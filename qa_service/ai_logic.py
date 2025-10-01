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

# --- 1. 主要な構成要素を関数外に定義します ---
# これらの変数は他のファイルからimportして使用できます。

# 埋め込みモデル (エンベディング)
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

# LLM (大規模言語モデル)
llm = ChatOpenAI(
    model="sonar",
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai"
)

# プロンプト
prompt = ChatPromptTemplate.from_template(
    """以下のコンテキストのみに基づいて質問に答えてください。
コンテキストから答えが見つからない場合、「申し訳ありませんが、与えられたドキュメントの内容についてのみお答えできます」とだけ答えてください。
推測で答えないでください。

コンテキスト:
{context}

質問: {question}"""
)

# 検索されたドキュメントを1つの文字列に結合する関数
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# --- 2. 構成要素の組み立て用関数 ---

FAISS_INDEX_PATH = "./faiss_index"

def create_rag_components():
    """
    RAGチェーンを構成する要素 (retriever, chain) を生成する関数
    """
    if os.path.exists(FAISS_INDEX_PATH):
        print("保存されているFAISSインデックスを読み込みます...")
        vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    else:
        print("新しくFAISSインデックスを作成します...")
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
        print(f"'{FAISS_INDEX_PATH}'にFAISSインデックスを保存しました。")

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

    print("RAGの構成要素の生成が完了しました。")
    return retriever, rag_chain

# サーバー起動時にRAGの構成要素を一度だけ生成し、変数に保存
RETRIEVER, RAG_CHAIN = create_rag_components()
