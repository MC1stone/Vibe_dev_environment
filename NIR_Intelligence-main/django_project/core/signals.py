"""
Core signals for NIR_Mistral Framework

This module contains signal handlers for the core application.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=User)
def handle_user_created(sender, instance, created, **kwargs):
    """Handle user creation events"""
    if created:
        # New user created - perform any initialization
        pass


@receiver(post_save, sender=User)
def handle_user_updated(sender, instance, created, **kwargs):
    """Handle user update events"""
    if not created:
        # User updated - perform any update actions
        pass


@receiver(post_delete, sender=User)
def handle_user_deleted(sender, instance, **kwargs):
    """Handle user deletion events"""
    # User deleted - perform any cleanup
    pass