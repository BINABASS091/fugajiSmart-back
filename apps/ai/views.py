from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import ChatSession, ChatMessage
from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    ChatSessionSerializer,
    ChatMessageSerializer
)
from .services import FugajiBotService


class ChatAPIView(APIView):
    """
    FugajiBot Chat API
    Handles conversational AI interactions for farmers.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        request=ChatRequestSerializer,
        responses={
            200: ChatResponseSerializer,
            400: OpenApiResponse(description="Bad Request"),
            500: OpenApiResponse(description="Internal Server Error")
        },
        summary="Send message to FugajiBot",
        description="Send a message to the AI assistant and receive a contextual response based on farm data."
    )
    def post(self, request):
        """
        Send a message to FugajiBot and get AI-generated response.
        """
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user_message = serializer.validated_data['message']
        session_id = serializer.validated_data.get('session_id')
        language = serializer.validated_data.get('language', 'sw')
        
        try:
            # Get or create chat session
            if session_id:
                try:
                    session = ChatSession.objects.get(id=session_id, user=request.user)
                except ChatSession.DoesNotExist:
                    session = ChatSession.objects.create(user=request.user, language=language)
            else:
                session = ChatSession.objects.create(user=request.user, language=language)
            
            # Save user message
            user_msg = ChatMessage.objects.create(
                session=session,
                role='user',
                content=user_message
            )
            
            # Get conversation history
            history_messages = ChatMessage.objects.filter(
                session=session
            ).order_by('created_at').values('role', 'content')
            
            conversation_history = [
                {"role": msg['role'], "content": msg['content']}
                for msg in history_messages
            ]
            
            # Generate AI response
            bot_service = FugajiBotService()
            ai_result = bot_service.generate_response(
                user_message=user_message,
                conversation_history=conversation_history[:-1],  # Exclude the message we just added
                user=request.user,
                language=language
            )
            
            # Save bot response
            bot_msg = ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=ai_result['response'],
                model_used=ai_result['model_used'],
                tokens_used=ai_result['tokens_used'],
                response_time_ms=ai_result['response_time_ms'],
                context_snapshot=ai_result.get('context_used')
            )
            
            # Update session
            session.total_messages += 2  # user + bot
            session.save()
            
            # Prepare response
            response_data = {
                'response': ai_result['response'],
                'session_id': str(session.id),
                'suggestions': ai_result.get('suggestions', []),
                'context_used': ai_result.get('context_used', {})
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(f"Error in ChatAPIView: {e}")
            return Response(
                {'error': 'Failed to process chat message'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChatHistoryAPIView(APIView):
    """
    Get chat history for the current user.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        responses={200: ChatSessionSerializer(many=True)},
        summary="Get chat history",
        description="Retrieve all chat sessions and messages for the authenticated user."
    )
    def get(self, request):
        """
        Get all chat sessions for the current user.
        """
        sessions = ChatSession.objects.filter(
            user=request.user
        ).prefetch_related('messages')[:10]  # Last 10 sessions
        
        serializer = ChatSessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChatSessionDetailAPIView(APIView):
    """
    Get or delete a specific chat session.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        responses={200: ChatSessionSerializer},
        summary="Get chat session details",
        description="Retrieve a specific chat session with all messages."
    )
    def get(self, request, session_id):
        """
        Get a specific chat session.
        """
        try:
            session = ChatSession.objects.prefetch_related('messages').get(
                id=session_id,
                user=request.user
            )
            serializer = ChatSessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Chat session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        responses={204: None},
        summary="Delete chat session",
        description="Delete a specific chat session and all its messages."
    )
    def delete(self, request, session_id):
        """
        Delete a chat session.
        """
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            session.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Chat session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
