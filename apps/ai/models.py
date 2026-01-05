import uuid
from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    """
    Represents a conversation session between a user and FugajiBot.
    Sessions help maintain context across multiple messages.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Session metadata
    language = models.CharField(max_length=5, default='sw', choices=[('sw', 'Swahili'), ('en', 'English')])
    total_messages = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
        ]
    
    def __str__(self):
        return f"Chat Session {self.id} - {self.user.email}"


class ChatMessage(models.Model):
    """
    Individual messages within a chat session.
    Stores both user queries and bot responses.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # AI metadata
    model_used = models.CharField(max_length=50, null=True, blank=True)  # e.g., 'gpt-4'
    tokens_used = models.IntegerField(null=True, blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    
    # Context snapshot (what farm data was available when this message was sent)
    context_snapshot = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class FecalImageAnalysis(models.Model):
    """
    AI-powered disease detection from fecal sample images.
    Future feature for computer vision disease prediction.
    """
    DISEASE_CHOICES = [
        ('HEALTHY', 'Healthy'),
        ('COCCIDIOSIS', 'Coccidiosis'),
        ('NEWCASTLE', 'Newcastle Disease'),
        ('SALMONELLA', 'Salmonellosis'),
        ('COLIBACILLOSIS', 'Colibacillosis'),
        ('UNKNOWN', 'Unknown/Uncertain'),
    ]
    
    RISK_LEVELS = [
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Medium Risk'),
        ('HIGH', 'High Risk'),
        ('CRITICAL', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    batch = models.ForeignKey('consolidated.Batch', on_delete=models.CASCADE, null=True, blank=True)
    
    # Image data
    image = models.ImageField(upload_to='fecal_samples/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # AI predictions
    predicted_disease = models.CharField(max_length=50, choices=DISEASE_CHOICES, null=True, blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS, null=True, blank=True)
    
    # Recommendations
    recommended_action = models.TextField(null=True, blank=True)
    veterinary_consultation_required = models.BooleanField(default=False)
    
    # Model metadata
    model_version = models.CharField(max_length=50, null=True, blank=True)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    
    # Verification (if vet confirms/corrects the diagnosis)
    verified_by_vet = models.BooleanField(default=False)
    actual_disease = models.CharField(max_length=50, null=True, blank=True)
    vet_notes = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name_plural = 'Fecal Image Analyses'
    
    def __str__(self):
        return f"Analysis {self.id} - {self.predicted_disease or 'Pending'}"
