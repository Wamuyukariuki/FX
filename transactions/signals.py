import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserPreference

logger = logging.getLogger(__name__)

# Signal to create UserPreferences when a new User is created
@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    if created:
        logger.info(f"Creating preferences for new user: {instance.username}")
        UserPreference.objects.create(user=instance)
    else:
        logger.info(f"User preferences already exist for: {instance.username}")

# Signal to save UserPreferences when the User is saved
@receiver(post_save, sender=User)
def save_user_preferences(sender, instance, **kwargs):
    try:
        instance.preferences.save()
        logger.info(f"Saving preferences for user: {instance.username}")
    except UserPreference.DoesNotExist:
        logger.warning(f"User preferences not found for: {instance.username}")
