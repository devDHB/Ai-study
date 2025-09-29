# qa_service/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import traceback

# RAG_CHAIN과 함께 RETRIEVER도 불러옵니다.
from .ai_logic import RAG_CHAIN, RETRIEVER

class AskAIView(APIView):
    def post(self, request):
        question = request.data.get('question')

        if not question:
            return Response(
                {"error": "Question is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 1. 먼저 Retriever를 사용해 관련 문서를 검색합니다.
            retrieved_docs = RETRIEVER.invoke(question)
            
            # 2. 검색된 문서의 내용을 sources 리스트로 만듭니다.
            sources = [doc.page_content for doc in retrieved_docs]

            # 3. RAG 체인을 사용해 답변을 생성합니다.
            answer = RAG_CHAIN.invoke(question)
            
            # 4. 답변과 출처를 함께 JSON으로 묶어서 반환합니다.
            return Response({
                "answer": answer,
                "sources": sources
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print("!!! CRITICAL ERROR CAUGHT !!!")
            traceback.print_exc()
            return Response(
                {"error": "An error occurred while processing the request."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )