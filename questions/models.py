import uuid
import logging
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify
from core.models import TimeStampedModel

logger = logging.getLogger(__name__)

class Question(TimeStampedModel):
    STATUS_CHOICES = (
        ('IN_REVIEW', 'In Review (Admin Approval Pending)'),
        ('REJECTED', 'Rejected (Needs Edits)'),
        ('PROPOSED', 'Proposed (Voting & Upvoting, No AI)'), 
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
    text = models.CharField(max_length=255, help_text="The core question or prediction.")
    
    context = models.TextField(blank=False, help_text="Provide background info to help voters and AI models understand the scope.")
    
    slug = models.SlugField(unique=True, max_length=255, blank=True)
    question_type = models.CharField(max_length=30, choices=QUESTION_TYPES, default='SUBJECTIVE_SLIDER')
    choices = ArrayField(models.CharField(max_length=100), blank=True, default=list)
    
    resolution_state = models.CharField(max_length=20, choices=RESOLUTION_STATES, default='N_A')
    resolution_date = models.DateTimeField(null=True, blank=True)
    resolved_truth = models.JSONField(null=True, blank=True)
    
    requires_web_search = models.BooleanField(default=False)
    status = models.CharField(choices=STATUS_CHOICES, default='IN_REVIEW', db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_auto_poll = models.BooleanField(default=False, db_index=True)

    # --- Orchestration Control Fields ---
    orchestration_queued = models.BooleanField(default=False, db_index=True, help_text="If True, the orchestrator will process this next.")
    ai_priority = models.IntegerField(default=0, db_index=True, help_text="Higher numbers are processed first.")
    
    allow_skip_vote = models.BooleanField(default=False)
    
    favorites = models.ManyToManyField(User, related_name='favorited_questions', blank=True)
    tags = ArrayField(models.CharField(max_length=30), blank=True, default=list)

    # Selection by tag group to reduce admin friction
    model_group_tags = ArrayField(
        models.CharField(max_length=30), 
        blank=True, 
        default=list, 
        help_text="Automatically query all active models with these tags (e.g., 'free', 'frontier')."
    )
    
    submitted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='submitted_questions')
    upvoters = models.ManyToManyField(User, related_name='upvoted_questions', blank=True)
    admin_feedback = models.TextField(blank=True)
    target_models = models.ManyToManyField('ai_engine.AIModel', blank=True)

    latest_run = models.ForeignKey(
        'ai_engine.ConsensusRun', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='latest_for_question'
    )

    __original_status = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_status = self.status

    @property
    def can_be_edited(self):
        return self.status in ['IN_REVIEW', 'REJECTED', 'PROPOSED']

    @property
    def can_be_voted_on(self):
        if self.status == 'ARCHIVED':
            return False
        if self.resolution_date and timezone.now() > self.resolution_date:
            return False
        return True

    def update_latest_run(self):
        """Automatically sets the latest_run based on the most recent ConsensusRun."""
        latest = self.runs.order_by('-created_at').first()
        if latest:
            self.latest_run = latest
            # Use update_fields to avoid triggering full save() and slug logic
            Question.objects.filter(id=self.id).update(latest_run=latest)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.text)[:240]
            self.slug = f"{base}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text

class BaseVote(TimeStampedModel):
    score = models.FloatField(null=True, blank=True) 
    complex_forecast = models.JSONField(null=True, blank=True) 
    reasoning = models.TextField(blank=True)
    
    class Meta:
        abstract = True
        constraints =[
            models.CheckConstraint(
                check=models.Q(score__isnull=True) | (models.Q(score__gte=0.0) & models.Q(score__lte=100.0)),
                name='%(app_label)s_%(class)s_valid_score'
            )
        ]
        
    def clean(self):
        if not self.question.can_be_voted_on:
             raise ValidationError('Voting is closed for this question.')

        q_type = self.question.question_type
        if q_type in ['SUBJECTIVE_SLIDER', 'PREDICTIVE_BINARY']:
            if self.score is None:
                raise ValidationError({'score': 'A score value is required.'})
                
        elif q_type == 'PREDICTIVE_CHOICE':
            if not isinstance(self.complex_forecast, list):
                raise ValidationError({'complex_forecast': 'Forecast must be a list.'})
            
            total_confidence = sum(float(item.get('confidence', 0)) for item in self.complex_forecast)
            if not (99.9 <= total_confidence <= 100.1):
                raise ValidationError({'complex_forecast': f'Total must sum to 100%. Currently: {total_confidence}%'})

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