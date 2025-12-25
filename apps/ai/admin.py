from django.contrib import admin
from .models import ChatSession, ChatMessage, FecalImageAnalysis


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'language', 'total_messages', 'created_at', 'is_active']
    list_filter = ['language', 'is_active', 'created_at']
    search_fields = ['user__email', 'id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'role', 'content_preview', 'created_at', 'tokens_used']
    list_filter = ['role', 'created_at']
    search_fields = ['content', 'session__id']
    readonly_fields = ['id', 'created_at']
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'


@admin.register(FecalImageAnalysis)
class FecalImageAnalysisAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'batch', 'predicted_disease', 'confidence_score', 'risk_level', 'uploaded_at']
    list_filter = ['predicted_disease', 'risk_level', 'verified_by_vet', 'uploaded_at']
    search_fields = ['user__email', 'batch__batch_number']
    readonly_fields = ['id', 'uploaded_at', 'processing_time_ms']
