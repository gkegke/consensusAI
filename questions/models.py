import uuid
import logging
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from core.models import TimeStampedModel

logger = logging.getLogger(__name__)

class Question(TimeStampedModel):
    STATUS_CHOICES = (
        ('PROPOSED', 'Proposed (Voting Only, No AI)'), 
        ('ACTIVE', 'Active (Has AI Data)'), 
        ('ARCHIVED', 'Archived (Locked)')
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.CharField(max_length=255)
    context = models.TextField(blank=True)
    slug = models.SlugField(unique=True, max_length=255)
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
    score = models.FloatField() # 0-100
    
    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=models.Q(score__gte=0.0) & models.Q(score__lte=100.0),
                name='%(app_label)s_%(class)s_valid_score'
            )
        ]

class HumanVote(BaseVote):
    """High-Trust: Linked to a registered user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='verified_votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta(BaseVote.Meta):
        unique_together = ('question', 'user')

class AnonymousVote(BaseVote):
    """Low-Trust: Frictionless voting tied to sessions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='public_votes')
    
    session_key = models.CharField(max_length=40, db_index=True)
    ip_address = models.GenericIPAddressField(db_index=True, null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta(BaseVote.Meta):
        constraints = BaseVote.Meta.constraints + [
            models.UniqueConstraint(fields=['question', 'session_key'], name='unique_anonymous_vote')
        ]