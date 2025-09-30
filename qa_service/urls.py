# qa_service/urls.py

from django.urls import path
from .views import AskAIView, FileUploadView

urlpatterns = [
    path('ask/', AskAIView.as_view(), name='ask-ai'),
    path('upload/', FileUploadView.as_view(), name='file-upload'),
]