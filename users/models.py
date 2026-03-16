import uuid
import logging
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import TimeStampedModel

logger = logging.getLogger(__name__)

class UserProfile(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cai_profile')
    
    is_onboarded = models.BooleanField(default=False)
    bio = models.TextField(max_length=500, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    """
    Ensures every User has a corresponding UserProfile.
    Uses get_or_create to ensure idempotency and prevent crashes during bulk operations.
    """
    try:
        if created:
            UserProfile.objects.get_or_create(user=instance)
            logger.info(f"SIGNAL: Created UserProfile for {instance.username}")
        else:
            # Safely update profile if it exists
            if hasattr(instance, 'cai_profile'):
                instance.cai_profile.save()
    except Exception as e:
        logger.error(f"SIGNAL ERROR: Failed to process profile for {instance.username}: {str(e)}")