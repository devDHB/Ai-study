# qa_service/urls.py (새 파일)

from django.urls import path
from .views import AskAIView

urlpatterns = [
    path('ask/', AskAIView.as_view(), name='ask-ai'),
]