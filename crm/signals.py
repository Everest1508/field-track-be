from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, SystemNotification
from .services import send_system_notification_fcm


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create UserProfile when User is created"""
    if created:
        UserProfile.objects.get_or_create(user=instance, defaults={'role': 'sales_executive'})


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(post_save, sender=SystemNotification)
def send_system_notification_push(sender, instance, created, **kwargs):
    """Send FCM push notification when SystemNotification is created"""
    if created:
        # Send FCM notification asynchronously (using threading to avoid blocking)
        import threading
        thread = threading.Thread(target=send_system_notification_fcm, args=(instance,))
        thread.daemon = True
        thread.start()

