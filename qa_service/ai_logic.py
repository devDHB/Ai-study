# qa_service/ai_logic.py

import os
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# --- 1. 핵심 부품들을 함수 바깥으로 이동 ---
# 이제 이 변수들은 다른 파일에서 import 해서 사용할 수 있습니다.

# 임베딩 모델 (사서)
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

# LLM (답변가)
llm = ChatOpenAI(
    model="sonar",
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai"
)

# 프롬프트
prompt = ChatPromptTemplate.from_template(
    """Answer the question based only on the following context.
If the answer cannot be found in the context, just say "죄송합니다, 주어진 문서의 내용에 대해서만 답변할 수 있습니다."
Do not try to make up an answer.

Context:
{context}

Question: {question}"""
)

# 검색된 문서를 하나의 문자열로 합치는 함수
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# --- 2. 함수는 이제 이 부품들을 조립하는 역할만 수행 ---

FAISS_INDEX_PATH = "./faiss_index"

def create_rag_components():
    """
    RAG 체인을 구성하는 요소들(retriever, chain)을 생성하는 함수
    """
    if os.path.exists(FAISS_INDEX_PATH):
        print("저장된 FAISS 인덱스를 불러옵니다...")
        vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    else:
        print("새로운 FAISS 인덱스를 생성합니다...")
        docs = []
        knowledge_base_path = "./knowledge_base"
        for dirpath, dirnames, filenames in os.walk(knowledge_base_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if filename.endswith('.pdf'):
                    loader = PyPDFLoader(file_path)
                    docs.extend(loader.load())
                elif filename.endswith('.txt'):
                    loader = TextLoader(file_path, encoding="utf-8")
                    docs.extend(loader.load())
        
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        vectorstore = FAISS.from_documents(documents=splits, embedding=embeddings)
        vectorstore.save_local(FAISS_INDEX_PATH)
        print(f"'{FAISS_INDEX_PATH}'에 FAISS 인덱스를 저장했습니다.")

    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={'k': 5, 'fetch_k': 20}
    )
    
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    print("RAG 구성요소 생성이 완료되었습니다.")
    return retriever, rag_chain

# 서버 시작 시 RAG 구성요소들을 한 번만 생성하여 변수에 저장
RETRIEVER, RAG_CHAIN = create_rag_components()