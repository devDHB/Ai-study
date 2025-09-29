import os
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# 저장될 FAISS 인덱스 파일 경로
FAISS_INDEX_PATH = "./faiss_index"

def create_rag_components():
    """
    RAG 체인을 구성하는 요소들(retriever, chain)을 생성하는 함수
    - 이미 생성된 인덱스 파일이 있으면, 파일을 로드하여 시간을 절약합니다.
    """
    
    # 다국어(한국어, 영어, 일본어 등) 지원 임베딩 모델로 교체
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    if os.path.exists(FAISS_INDEX_PATH):
        # 인덱스 파일이 이미 존재하면...
        print("저장된 FAISS 인덱스를 불러옵니다...")
        vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    else:
        # 인덱스 파일이 없으면...
        print("새로운 FAISS 인덱스를 생성합니다...")
        # 1. 문서 로드 (data.txt)
        loader = TextLoader("./data.txt", encoding="utf-8")
        docs = loader.load()

        # 2. 텍스트 분할
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)

        # 3. 벡터 스토어 생성 및 파일로 저장
        vectorstore = FAISS.from_documents(documents=splits, embedding=embeddings)
        vectorstore.save_local(FAISS_INDEX_PATH)
        print(f"'{FAISS_INDEX_PATH}'에 FAISS 인덱스를 저장했습니다.")

    # 4. 검색기(Retriever) 생성
    retriever = vectorstore.as_retriever()
    
    # 5. LLM(답변가)은 Perplexity를 사용
    llm = ChatOpenAI(
        model="sonar",
        api_key=os.getenv("PERPLEXITY_API_KEY"),
        base_url="https://api.perplexity.ai"
    )
    
    # 6. 프롬프트 설정
    # qa_service/ai_logic.py

    prompt = ChatPromptTemplate.from_template(
        """Answer the question based only on the following context.
        If the answer cannot be found in the context, just say "죄송합니다, 주어진 문서의 내용에 대해서만 답변할 수 있습니다."
        Do not try to make up an answer.

        Context:
        {context}

        Question: {question}"""
            )

    # 7. RAG 체인 조립
    def format_docs(docs):
        # 검색된 문서들을 하나의 문자열로 합칩니다.
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    print("RAG 구성요소 생성이 완료되었습니다.")
    # 체인과 검색기를 모두 반환
    return retriever, rag_chain

# 서버 시작 시 RAG 구성요소들을 한 번만 생성하여 변수에 저장
RETRIEVER, RAG_CHAIN = create_rag_components()