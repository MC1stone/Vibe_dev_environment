"""
Port Manager Django App Configuration
"""

from django.apps import AppConfig


class PortManagerConfig(AppConfig):
    """Configuration for Port Manager Django App"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'port_manager'
    verbose_name = 'Port Management Agent'
    
    def ready(self):
        """Called when the app is ready"""
        # Import and initialize the port management system
        from . import port_integration
        from .middleware import PortConflictMiddleware
        
        # Initialize the port integration if available
        if port_integration is not None:
            port_integration.initialize()
            print("✓ Port Management Agent initialized and ready")
        else:
            print("✓ Port Management Agent will be initialized on first use")