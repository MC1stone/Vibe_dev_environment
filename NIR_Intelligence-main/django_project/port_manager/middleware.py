"""
Port Conflict Middleware for Django

This middleware automatically detects and resolves port conflicts
when Django starts up, ensuring that all services can run without
port collisions.
"""

import sys
import os
from pathlib import Path
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
import logging

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from agents.port_agent import PortAgentIntegration
except ImportError:
    PortAgentIntegration = None

# Configure logging
logger = logging.getLogger(__name__)


class PortConflictMiddleware(MiddlewareMixin):
    """
    Middleware that automatically detects and resolves port conflicts
    for the NIR_Mistral Framework.
    
    This middleware runs on Django startup and:
    1. Detects any port conflicts in the framework configuration
    2. Automatically resolves conflicts by assigning new ports
    3. Updates the configuration if needed
    4. Provides port management API endpoints
    """
    
    def __init__(self, get_response):
        """Initialize the middleware"""
        super().__init__(get_response)
        self.port_integration = PortAgentIntegration() if PortAgentIntegration else None
        self.conflicts_resolved = False
        self.initialized = False
    
    def __call__(self, request):
        """Process the request"""
        # Initialize on first request
        if not self.initialized and self.port_integration:
            self.initialize_port_management()
            self.initialized = True
        
        response = self.get_response(request)
        return response
    
    def initialize_port_management(self):
        """Initialize port management system"""
        try:
            # Initialize the port integration
            init_result = self.port_integration.initialize()
            logger.info("Port Management Agent initialized")
            
            # Detect conflicts
            conflict_result = self.port_integration.conflict_resolver.detect_conflicts()
            
            if conflict_result.get('has_conflicts'):
                logger.warning(f"Port conflicts detected: {conflict_result.get('conflict_count')}")
                
                # Auto-resolve conflicts
                resolve_result = self.port_integration.conflict_resolver.resolve_conflicts(auto_assign=True)
                
                if resolve_result.get('conflicts_resolved') > 0:
                    logger.info(f"Resolved {resolve_result.get('conflicts_resolved')} port conflicts")
                    self.conflicts_resolved = True
                    
                    # Log the new port mappings
                    for agent_name, mapping in resolve_result.get('port_mappings', {}).items():
                        if mapping.get('status') == 'resolved':
                            logger.info(f"Agent {agent_name}: port changed from {mapping.get('original_port')} to {mapping.get('new_port')}")
                else:
                    logger.warning("Failed to resolve all port conflicts")
            else:
                logger.info("No port conflicts detected")
                
            # Store the port mappings for later use
            self.port_mappings = self.port_integration.conflict_resolver.port_mappings
            
        except Exception as e:
            logger.error(f"Failed to initialize port management: {str(e)}")
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Process view - can be used to inject port information"""
        # Add port management to request context if needed
        request.port_manager = self.port_integration
        return None
    
    def get_agent_port(self, agent_name):
        """Get the port for a specific agent"""
        return self.port_integration.get_agent_port(agent_name)
    
    def reserve_port_for_service(self, service_name, port=None, host="127.0.0.1"):
        """Reserve a port for a service"""
        return self.port_integration.reserve_port_for_agent(service_name, port, host)
    
    def release_port_for_service(self, service_name, host="127.0.0.1"):
        """Release a port for a service"""
        return self.port_integration.release_agent_port(service_name, host)


class PortConflictResolutionMiddleware:
    """
    Alternative middleware that resolves port conflicts at startup time
    rather than on first request.
    """
    
    def __init__(self, get_response):
        """Initialize the middleware"""
        self.get_response = get_response
        self.port_integration = PortAgentIntegration() if PortAgentIntegration else None
        
        # Initialize immediately
        self.initialize_port_management()
    
    def __call__(self, request):
        """Process the request"""
        # Add port manager to request
        request.port_manager = self.port_integration
        return self.get_response(request)
    
    def initialize_port_management(self):
        """Initialize port management and resolve conflicts"""
        try:
            # Initialize
            init_result = self.port_integration.initialize()
            
            # Detect and resolve conflicts
            conflict_result = self.port_integration.conflict_resolver.detect_conflicts()
            
            if conflict_result.get('has_conflicts'):
                resolve_result = self.port_integration.conflict_resolver.resolve_conflicts(auto_assign=True)
                
                if resolve_result.get('conflicts_resolved') > 0:
                    print(f"✓ Port Management: Resolved {resolve_result.get('conflicts_resolved')} port conflicts")
                    
                    # Update Django settings if needed
                    self.update_django_settings(resolve_result)
                
            print("✓ Port Management: System initialized and conflicts resolved")
            
        except Exception as e:
            print(f"✗ Port Management: Failed to initialize - {str(e)}")
    
    def update_django_settings(self, resolve_result):
        """Update Django settings with resolved ports"""
        try:
            port_mappings = resolve_result.get('port_mappings', {})
            
            # Update settings for agents that had port changes
            for agent_name, mapping in port_mappings.items():
                if mapping.get('status') == 'resolved' and mapping.get('new_port'):
                    # This would be customized based on your Django settings structure
                    # For example, if you have AGENTS_CONFIG in settings:
                    if hasattr(settings, 'AGENTS_CONFIG'):
                        if agent_name in settings.AGENTS_CONFIG:
                            settings.AGENTS_CONFIG[agent_name]['port'] = mapping['new_port']
                    
                    print(f"  Updated {agent_name} port to {mapping['new_port']}")
                    
        except Exception as e:
            logger.error(f"Failed to update Django settings: {str(e)}")


def get_port_manager():
    """Get the global port manager instance"""
    return PortConflictMiddleware(None).port_integration