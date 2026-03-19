import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.db import models, transaction
from django.contrib.postgres.fields import ArrayField
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from core.models import TimeStampedModel

class AIModel(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50) 
    api_identifier = models.CharField(max_length=100, unique=True)
    developer = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    tags = ArrayField(models.CharField(max_length=30), default=list, blank=True)

    class Meta:
        verbose_name = "AI Model"

    def __str__(self):
        return f"{self.name} ({self.developer})"

class ConsensusRun(TimeStampedModel):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey('questions.Question', related_name='runs', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    synthesis_summary = models.TextField(blank=True)
    minority_report = models.TextField(blank=True) 
    polarization_index = models.FloatField(default=0.0) 
    prompt_version = models.CharField(max_length=50, blank=True, default="v1.2")
    total_cost = models.DecimalField(max_digits=15, decimal_places=10, default=Decimal('0.0000000000'))

    def update_totals(self, commit=True):
        costs = self.responses.aggregate(total=models.Sum('cost'))['total'] or Decimal('0')
        self.total_cost = Decimal(costs).quantize(Decimal('1.0000000000'), rounding=ROUND_HALF_UP)
        if commit:
            ConsensusRun.objects.filter(id=self.id).update(total_cost=self.total_cost)

    def __str__(self):
        return f"Run: {self.question.slug} [{self.status}]"

@receiver(post_save, sender=ConsensusRun)
def auto_update_question_latest_run(sender, instance, created, **kwargs):
    from questions.models import Question
    # Only promote to latest_run if it completed successfully
    if instance.status == 'COMPLETED':
        latest_run = ConsensusRun.objects.filter(
            question=instance.question, 
            status='COMPLETED'
        ).order_by('-created_at').first()
        if latest_run:
            Question.objects.filter(id=instance.question.id).update(latest_run=latest_run)

class AIResponse(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(ConsensusRun, on_delete=models.CASCADE, related_name='responses')
    model = models.ForeignKey(AIModel, on_delete=models.CASCADE)
    
    normalized_score = models.FloatField(null=True, blank=True) 
    complex_forecast = models.JSONField(null=True, blank=True) 
    summary_sentence = models.TextField()
    is_refusal = models.BooleanField(default=False)
    refusal_reason = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=15, decimal_places=10, default=Decimal('0.0000000000'))
    is_manual_entry = models.BooleanField(default=False)

    class Meta:
        verbose_name = "AI Response"

    def save(self, *args, **kwargs):
        if self.cost:
            self.cost = Decimal(str(self.cost)).quantize(Decimal('1.0000000000'), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)

@receiver(post_save, sender=AIResponse)
@receiver(post_delete, sender=AIResponse)
def update_run_cost(sender, instance, **kwargs):
    instance.run.update_totals()

class OrchestrationLog(TimeStampedModel):
    task_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=(('SUCCESS', 'Success'), ('PARTIAL', 'Partial'), ('FAILURE', 'Failure')))
    items_processed = models.IntegerField(default=0)
    log_message = models.TextField()
    total_run_cost = models.DecimalField(max_digits=15, decimal_places=10, default=Decimal('0'))

    class Meta:
        ordering = ['-created_at']