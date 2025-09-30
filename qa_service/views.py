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

from .ai_logic import RAG_CHAIN, RETRIEVER, llm, prompt, format_docs, embeddings
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

class AskAIView(APIView):
    def post(self, request):
        question = request.data.get('question')
        session_id = request.data.get('session_id')

        if not question:
            return Response({"error": "Question is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if session_id and cache.get(session_id):
                print(f"업로드된 파일(ID: {session_id}) 기반으로 답변합니다...")
                index_bytes = cache.get(session_id)
                
                vectorstore = FAISS.deserialize_from_bytes(
                    serialized=index_bytes,  # 'serialized_index'가 아닌 'serialized'
                    embeddings=embeddings,
                    allow_dangerous_deserialization=True
                )
                
                temp_retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={'k': 5, 'fetch_k': 20})
                
                temp_rag_chain = (
                    {"context": temp_retriever | format_docs, "question": RunnablePassthrough()}
                    | prompt | llm | StrOutputParser()
                )
                answer = temp_rag_chain.invoke(question)
                sources = [doc.page_content for doc in temp_retriever.invoke(question)]
            else:
                print("기본 지식 기반으로 답변합니다...")
                answer = RAG_CHAIN.invoke(question)
                sources = [doc.page_content for doc in RETRIEVER.invoke(question)]
            
            return Response({"answer": answer, "sources": sources}, status=status.HTTP_200_OK)

        except Exception as e:
            traceback.print_exc()
            return Response({"error": "An error occurred while processing the request."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileUploadView(APIView):
    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

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
                return Response({"error": "Unsupported file type."}, status=status.HTTP_400_BAD_REQUEST)
            
            docs = loader.load()

            text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(docs)
            vectorstore = FAISS.from_documents(documents=splits, embedding=embeddings)
            index_bytes = vectorstore.serialize_to_bytes()
            
            session_id = uuid.uuid4().hex
            cache.set(session_id, index_bytes, timeout=600)
            
            print(f"파일 처리 완료. 캐시에 세션 ID '{session_id}'로 데이터 저장.")

            return Response({
                "message": f"'{file_obj.name}' 파일이 성공적으로 처리되었습니다.",
                "session_id": session_id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            traceback.print_exc()
            return Response({"error": "파일 처리 중 오류 발생"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)