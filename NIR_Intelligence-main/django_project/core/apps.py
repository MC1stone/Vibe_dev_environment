"""
Core app configuration
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for Core app"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core'
    
    def ready(self):
        """Called when the app is ready"""
        # Import and register signals
        import core.signals