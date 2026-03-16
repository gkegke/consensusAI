import uuid
from decimal import Decimal
from django.db import models
from django.contrib.postgres.fields import ArrayField
from core.models import TimeStampedModel

class AIModel(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50) 
    api_identifier = models.CharField(max_length=100, unique=True)
    developer = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    tags = ArrayField(models.CharField(max_length=30), default=list, blank=True)

    def __str__(self):
        return f"{self.name} ({self.developer})"

class ConsensusRun(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey('questions.Question', related_name='runs', on_delete=models.CASCADE)
    
    synthesis_summary = models.TextField(blank=True)
    minority_report = models.TextField(blank=True) 
    polarization_index = models.FloatField(default=0.0) 

    verified_sentiment_avg = models.FloatField(null=True, blank=True)
    public_sentiment_avg = models.FloatField(null=True, blank=True)
    
    aggregated_forecast = models.JSONField(blank=True, null=True)
    
    prompt_version = models.CharField(max_length=50, blank=True, default="v1.0")
    total_cost = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal('0.000000'))

    def __str__(self):
        return f"Run: {self.question.slug} @ {self.created_at.date()}"

class AIResponse(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(ConsensusRun, on_delete=models.CASCADE, related_name='responses')
    model = models.ForeignKey(AIModel, on_delete=models.CASCADE)
    
    raw_json = models.JSONField(blank=True, null=True) 
    
    normalized_score = models.FloatField(null=True, blank=True) 
    selected_choice = models.CharField(max_length=100, null=True, blank=True)
    complex_forecast = models.JSONField(null=True, blank=True) 
    
    summary_sentence = models.TextField()
    is_refusal = models.BooleanField(default=False)
    refusal_reason = models.TextField(blank=True)

    cost = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal('0.000000'))

    class Meta:
        constraints =[
            models.CheckConstraint(
                check=models.Q(normalized_score__isnull=True) | (models.Q(normalized_score__gte=0.0) & models.Q(normalized_score__lte=100.0)),
                name='ai_engine_airesponse_valid_ai_score'
            )
        ]

    def __str__(self):
        return f"{self.model.name} response for {self.run.question.slug}"