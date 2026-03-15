import uuid
import logging
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.models import TimeStampedModel

logger = logging.getLogger(__name__)

class Question(TimeStampedModel):
    STATUS_CHOICES = (
        ('PROPOSED', 'Proposed (Voting Only, No AI)'), 
        ('ACTIVE', 'Active (Has AI Data)'), 
        ('ARCHIVED', 'Archived (Locked)')
    )
    
    QUESTION_TYPES = (
        ('SUBJECTIVE_SLIDER', 'Subjective Slider (0-100)'),
        ('PREDICTIVE_BINARY', 'Binary Prediction (0-100% Probability)'),
        ('PREDICTIVE_CHOICE', 'Categorical Prediction (Probability Distribution)')
    )

    RESOLUTION_STATES = (
        ('N_A', 'Not Applicable (Subjective)'),
        ('PENDING', 'Pending Resolution'),
        ('RESOLVED', 'Resolved'),
        ('CANCELLED', 'Cancelled / Invalid')
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.CharField(max_length=255)
    context = models.TextField(blank=True)
    slug = models.SlugField(unique=True, max_length=255)
    
    question_type = models.CharField(max_length=30, choices=QUESTION_TYPES, default='SUBJECTIVE_SLIDER')
    choices = ArrayField(models.CharField(max_length=100), blank=True, default=list, help_text="Required for PREDICTIVE_CHOICE")
    
    resolution_state = models.CharField(max_length=20, choices=RESOLUTION_STATES, default='N_A')
    resolution_date = models.DateTimeField(null=True, blank=True, help_text="When the prediction objectively resolves.")
    resolved_truth = models.JSONField(null=True, blank=True, help_text="Stores the factual outcome once resolved.")
    
    requires_web_search = models.BooleanField(default=False)
    status = models.CharField(choices=STATUS_CHOICES, default='PROPOSED', db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_auto_poll = models.BooleanField(default=False, db_index=True)
    
    favorites = models.ManyToManyField(User, related_name='favorited_questions', blank=True)
    tags = ArrayField(models.CharField(max_length=30), blank=True, default=list)
    
    latest_run = models.ForeignKey(
        'ai_engine.ConsensusRun', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='latest_for_question'
    )

    def __str__(self):
        return self.text

class BaseVote(TimeStampedModel):
    # Used for SUBJECTIVE_SLIDER and PREDICTIVE_BINARY (0-100)
    score = models.FloatField(null=True, blank=True) 
    
    # Used for PREDICTIVE_CHOICE e.g., [{"choice": "France", "confidence": 85.0}, {"choice": "Germany", "confidence": 15.0}]
    complex_forecast = models.JSONField(null=True, blank=True) 
    
    class Meta:
        abstract = True
        constraints =[
            models.CheckConstraint(
                condition=models.Q(score__isnull=True) | (models.Q(score__gte=0.0) & models.Q(score__lte=100.0)),
                name='%(app_label)s_%(class)s_valid_score'
            )
        ]
        
    def clean(self):
        q_type = self.question.question_type
        
        # Prevent voting if question is already resolved or past deadline
        if self.question.resolution_date and timezone.now() > self.question.resolution_date:
             raise ValidationError('Voting is closed. The resolution deadline has passed.')

        if q_type in ['SUBJECTIVE_SLIDER', 'PREDICTIVE_BINARY']:
            if self.score is None:
                raise ValidationError({'score': f'Score/Probability is required for {q_type}.'})
            if self.complex_forecast is not None:
                raise ValidationError({'complex_forecast': f'Must be null for {q_type}.'})
                
        elif q_type == 'PREDICTIVE_CHOICE':
            if not isinstance(self.complex_forecast, list):
                raise ValidationError({'complex_forecast': 'Must be a list of forecast objects.'})
            if self.score is not None:
                raise ValidationError({'score': 'Score must be null for PREDICTIVE_CHOICE.'})
            
            # Validate JSON structure and math
            total_confidence = 0.0
            for item in self.complex_forecast:
                if 'choice' not in item or 'confidence' not in item:
                    raise ValidationError({'complex_forecast': 'Each item must have "choice" and "confidence".'})
                if item['choice'] not in self.question.choices:
                    raise ValidationError({'complex_forecast': f"Invalid choice: {item['choice']}"})
                total_confidence += float(item['confidence'])
            
            if not (99.0 <= total_confidence <= 101.0): # Account for minor float rounding
                raise ValidationError({'complex_forecast': f'Confidence scores must sum to ~100.0. Current sum: {total_confidence}'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class HumanVote(BaseVote):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='verified_votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta(BaseVote.Meta):
        unique_together = ('question', 'user')

class AnonymousVote(BaseVote):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='public_votes')
    session_key = models.CharField(max_length=40, db_index=True)
    ip_address = models.GenericIPAddressField(db_index=True, null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta(BaseVote.Meta):
        constraints = BaseVote.Meta.constraints + [
            models.UniqueConstraint(fields=['question', 'session_key'], name='unique_anonymous_vote')
        ]