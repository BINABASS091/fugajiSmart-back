from django.urls import path
from .views import ChatAPIView, ChatHistoryAPIView, ChatSessionDetailAPIView

urlpatterns = [
    path('chat/', ChatAPIView.as_view(), name='ai-chat'),
    path('chat/history/', ChatHistoryAPIView.as_view(), name='chat-history'),
    path('chat/sessions/<uuid:session_id>/', ChatSessionDetailAPIView.as_view(), name='chat-session-detail'),
]
