# qa_service/views.py

import base64
import os
import traceback
import io
import uuid
from django.core.cache import cache

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# ai_logicからRAGのコアコンポーネントをインポート
from .ai_logic import RAG_CHAIN, RETRIEVER, llm, prompt, format_docs, embeddings

# ファイルアップロードと一時的なRAGチェーン作成に必要なライブラリをインポート
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

class AskAIView(APIView):
    # POSTリクエスト（質問の送信）を処理するメソッド
    def post(self, request):
        question = request.data.get('question')
        session_id = request.data.get('session_id')

        # 質問が空の場合はエラーを返す
        if not question:
            return Response({"error": "質問が必要です。"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # session_idがあり、かつそのIDに対応するデータがキャッシュに存在する場合
            if session_id and cache.get(session_id):
                print(f"アップロードされたファイル(ID: {session_id})に基づいて回答します...")
                index_bytes = cache.get(session_id)
                
                # バイナリデータからFAISSベクトルデータベースを復元
                vectorstore = FAISS.deserialize_from_bytes(
                    embeddings=embeddings,
                    serialized=index_bytes, # 正しい引数名 'serialized' を使用
                    allow_dangerous_deserialization=True
                )
                
                # 復元したベクトルデータベースから一時的な検索器（Retriever）を作成
                temp_retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={'k': 5, 'fetch_k': 20})
                
                # アップロードされたファイル専用の一時的なRAGチェーンを即席で作成
                temp_rag_chain = (
                    {"context": temp_retriever | format_docs, "question": RunnablePassthrough()}
                    | prompt | llm | StrOutputParser()
                )
                answer = temp_rag_chain.invoke(question)
                sources = [doc.page_content for doc in temp_retriever.invoke(question)]
            else:
                # アップロードされたファイルがない場合は、基本知識で回答
                print("基本知識に基づいて回答します...")
                answer = RAG_CHAIN.invoke(question)
                sources = [doc.page_content for doc in RETRIEVER.invoke(question)]
            
            # 生成された回答と参考資料をJSON形式でフロントエンドに返す
            return Response({"answer": answer, "sources": sources}, status=status.HTTP_200_OK)

        except Exception as e:
            traceback.print_exc()
            return Response({"error": "リクエストの処理中にエラーが発生しました。"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileUploadView(APIView):
    # POSTリクエスト（ファイルのアップロード）を処理するメソッド
    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "ファイルがアップロードされていません。"}, status=status.HTTP_400_BAD_REQUEST)

        temp_file_name = f"{uuid.uuid4()}_{file_obj.name}"
        temp_file_path = os.path.join('temp_uploads', temp_file_name)
        
        with open(temp_file_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        try:
            if file_obj.name.endswith('.pdf'):
                loader = PyPDFLoader(temp_file_path)
            elif file_obj.name.endswith('.txt'):
                loader = TextLoader(temp_file_path, encoding='utf-8')
            else:
                return Response({"error": "サポートされていないファイル形式です。"}, status=status.HTTP_400_BAD_REQUEST)
            
            docs = loader.load()

            text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(docs)
            vectorstore = FAISS.from_documents(documents=splits, embedding=embeddings)
            index_bytes = vectorstore.serialize_to_bytes()
            
            session_id = uuid.uuid4().hex
            cache.set(session_id, index_bytes, timeout=600)
            
            print(f"ファイル処理完了。キャッシュにセッションID '{session_id}'でデータを保存しました。")

            return Response({
                "message": f"'{file_obj.name}' ファイルの処理が正常に完了しました。",
                "session_id": session_id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            traceback.print_exc()
            return Response({"error": "ファイル処理中にエラーが発生しました。"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)