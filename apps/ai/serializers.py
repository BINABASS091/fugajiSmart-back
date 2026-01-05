from rest_framework import serializers
from .models import ChatSession, ChatMessage, FecalImageAnalysis


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'created_at', 'tokens_used', 'response_time_ms']
        read_only_fields = ['id', 'created_at', 'tokens_used', 'response_time_ms']


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatSession
        fields = ['id', 'language', 'created_at', 'updated_at', 'total_messages', 'messages']
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_messages']


class ChatRequestSerializer(serializers.Serializer):
    """Serializer for incoming chat requests"""
    message = serializers.CharField(required=True, max_length=2000)
    session_id = serializers.UUIDField(required=False, allow_null=True)
    language = serializers.ChoiceField(choices=['sw', 'en'], default='sw')


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat responses"""
    response = serializers.CharField()
    session_id = serializers.UUIDField()
    suggestions = serializers.ListField(child=serializers.CharField(), required=False)
    context_used = serializers.DictField(required=False)


class FecalImageAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = FecalImageAnalysis
        fields = [
            'id', 'batch', 'image', 'uploaded_at',
            'predicted_disease', 'confidence_score', 'risk_level',
            'recommended_action', 'veterinary_consultation_required',
            'model_version', 'processing_time_ms'
        ]
        read_only_fields = [
            'id', 'uploaded_at', 'predicted_disease', 'confidence_score',
            'risk_level', 'recommended_action', 'veterinary_consultation_required',
            'model_version', 'processing_time_ms'
        ]
