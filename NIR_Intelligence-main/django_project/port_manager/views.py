"""
Port Management API Views for Django

This module provides REST API endpoints for port management,
allowing external services to check port availability, reserve ports,
and resolve conflicts.
"""

import sys
import json
from pathlib import Path
from django.http import JsonResponse
from django.views import View
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# Import path configuration
from path_config import setup_project_paths
setup_project_paths()

try:
    from agents.port_agent import PortAgentIntegration
    # Global port integration instance
    port_integration = PortAgentIntegration()
except ImportError as e:
    print(f"Warning: PortAgentIntegration not available: {e}")
    port_integration = None


def check_port_integration():
    """Check if port_integration is available and return appropriate response"""
    if port_integration is None:
        return JsonResponse({
            'success': False,
            'error': 'Port Management Agent not fully initialized',
            'message': 'Agents module not available, using basic port management'
        }, status=503)


class PortManagementAPI(View):
    """Main API endpoint for port management"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """Dispatch the request to the appropriate method"""
        return super().dispatch(request, *args, **kwargs)
    
    @method_decorator(csrf_exempt)
    def get(self, request, action=None):
        """Handle GET requests"""
        if action == 'status':
            return self.get_status(request)
        elif action == 'conflicts':
            return self.get_conflicts(request)
        elif action == 'scan':
            return self.scan_ports(request)
        elif action == 'check':
            return self.check_port(request)
        elif action == 'agents':
            return self.get_agents(request)
        else:
            return self.get_overview(request)
    
    @method_decorator(csrf_exempt)
    def post(self, request, action=None):
        """Handle POST requests"""
        if action == 'reserve':
            return self.reserve_port(request)
        elif action == 'release':
            return self.release_port(request)
        elif action == 'assign':
            return self.assign_port(request)
        elif action == 'resolve':
            return self.resolve_conflicts(request)
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
    
    def get_overview(self, request):
        """Get port management overview"""
        try:
            if port_integration is None:
                return JsonResponse({
                    'success': True,
                    'docker_available': False,
                    'system_ports_count': 0,
                    'reserved_ports_count': 0,
                    'docker_ports_count': 0,
                    'has_conflicts': False,
                    'conflict_count': 0,
                    'message': 'Port Management Agent is running (limited functionality)'
                })
            
            # Initialize
            init_result = port_integration.initialize()
            
            # Get conflict status
            conflict_result = port_integration.conflict_resolver.detect_conflicts()
            
            # Get system ports
            system_ports = list(port_integration.port_manager._scanner.get_system_used_ports())
            
            # Get reserved ports
            reserved_ports = list(port_integration.port_manager.get_reserved_ports().keys())
            
            # Get Docker ports if available
            docker_ports = []
            if hasattr(port_integration, 'docker_port_manager') and port_integration.docker_port_manager.is_docker_available():
                docker_ports = list(port_integration.docker_port_manager.get_used_docker_ports())
            
            return JsonResponse({
                'success': True,
                'docker_available': init_result.get('docker_available') if init_result else False,
                'system_ports_count': len(system_ports),
                'reserved_ports_count': len(reserved_ports),
                'docker_ports_count': len(docker_ports),
                'has_conflicts': conflict_result.get('has_conflicts') if conflict_result else False,
                'conflict_count': conflict_result.get('conflict_count') if conflict_result else 0,
                'message': 'Port Management Agent is running'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    def get_status(self, request):
        """Get detailed port status"""
        try:
            if port_integration is None:
                return JsonResponse({
                    'success': True,
                    'message': 'Port Management Agent running with basic functionality',
                    'basic_mode': True
                })
            
            status_report = port_integration.get_port_status_report()
            return JsonResponse(status_report)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    @method_decorator(csrf_exempt)
    def get_conflicts(self, request):
        """Get port conflicts"""
        try:
            if port_integration is None:
                return JsonResponse({
                    'success': True,
                    'has_conflicts': False,
                    'conflict_count': 0,
                    'conflicts': [],
                    'message': 'Basic mode - no conflict detection available'
                })
            
            conflict_result = port_integration.conflict_resolver.detect_conflicts()
            return JsonResponse(conflict_result)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    @method_decorator(csrf_exempt)
    def scan_ports(self, request):
        """Scan ports in a range"""
        try:
            if port_integration is None:
                from agents.port_agent.port_manager import PortManager
                basic_port_manager = PortManager()
                start = int(request.GET.get('start', 8000))
                end = int(request.GET.get('end', 9000))
                host = request.GET.get('host', '127.0.0.1')
                scan_result = basic_port_manager.scan_ports(start, end, host)
            else:
                start = int(request.GET.get('start', 8000))
                end = int(request.GET.get('end', 9000))
                host = request.GET.get('host', '127.0.0.1')
                scan_result = port_integration.port_manager.scan_ports(start, end, host)
            
            # Convert to more readable format
            used_ports = [p for p, available in scan_result.items() if not available]
            available_ports = [p for p, available in scan_result.items() if available]
            
            return JsonResponse({
                'success': True,
                'range': {'start': start, 'end': end},
                'host': host,
                'used_ports': used_ports,
                'available_ports': available_ports,
                'used_count': len(used_ports),
                'available_count': len(available_ports)
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    @method_decorator(csrf_exempt)
    def check_port(self, request):
        """Check if a specific port is available"""
        try:
            port = int(request.GET.get('port'))
            host = request.GET.get('host', '127.0.0.1')
            
            if not port:
                return JsonResponse({'success': False, 'error': 'Port parameter is required'}, status=400)
            
            if port_integration is None:
                from agents.port_agent.port_manager import PortManager
                basic_port_manager = PortManager()
                available = basic_port_manager.check_port_available(port, host)
            else:
                available = port_integration.port_manager.check_port_available(port, host)
            conflicts = port_integration.port_manager.get_port_conflicts(port, host)
            
            return JsonResponse({
                'success': True,
                'port': port,
                'host': host,
                'available': available,
                'conflicts': conflicts
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    @method_decorator(csrf_exempt)
    def get_agents(self, request):
        """Get port information for all agents"""
        try:
            if port_integration is None:
                return JsonResponse({
                    'success': True,
                    'agents': {},
                    'message': 'Basic mode - agent information not available'
                })
            
            status_report = port_integration.get_port_status_report()
            agents_info = status_report.get('agents', {})
            
            return JsonResponse({
                'success': True,
                'agents': agents_info,
                'count': len(agents_info)
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    @method_decorator(csrf_exempt)
    def reserve_port(self, request):
        """Reserve a port for a service"""
        try:
            data = json.loads(request.body)
            port = data.get('port')
            service_name = data.get('service_name')
            host = data.get('host', '127.0.0.1')
            
            if not service_name:
                return JsonResponse({'success': False, 'error': 'service_name is required'}, status=400)
            
            if port_integration is None:
                from agents.port_agent.port_manager import PortManager
                basic_port_manager = PortManager()
                if port:
                    # Reserve specific port
                    success = basic_port_manager.reserve_port(port, host, service_name)
                else:
                    # Find and reserve a port
                    start = data.get('start', 8000)
                    end = data.get('end', 9000)
                    port = basic_port_manager.find_and_reserve_port(start, end, host, service_name)
                    success = port is not None
            else:
                if port:
                    # Reserve specific port
                    success = port_integration.port_manager.reserve_port(port, host, service_name)
                    return JsonResponse({
                        'success': success,
                        'port': port,
                        'host': host,
                        'service_name': service_name,
                        'message': f'Port {port} reserved for {service_name}' if success else 'Failed to reserve port'
                    })
                else:
                    # Find and reserve a port
                    start = data.get('start', 8000)
                    end = data.get('end', 9000)
                    port = port_integration.port_manager.find_and_reserve_port(start, end, host, service_name)
                    return JsonResponse({
                        'success': True,
                        'port': port,
                        'host': host,
                        'service_name': service_name,
                        'message': f'Port {port} assigned and reserved for {service_name}'
                    })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    @method_decorator(csrf_exempt)
    def release_port(self, request):
        """Release a reserved port"""
        try:
            data = json.loads(request.body)
            port = data.get('port')
            host = data.get('host', '127.0.0.1')
            
            if not port:
                return JsonResponse({'success': False, 'error': 'port is required'}, status=400)
            
            if port_integration is None:
                from agents.port_agent.port_manager import PortManager
                basic_port_manager = PortManager()
                success = basic_port_manager.release_port(port, host)
            else:
                success = port_integration.port_manager.release_port(port, host)
            return JsonResponse({
                'success': success,
                'port': port,
                'host': host,
                'message': f'Port {port} released' if success else 'Port was not reserved'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    @method_decorator(csrf_exempt)
    def assign_port(self, request):
        """Assign a free port in a range"""
        try:
            data = json.loads(request.body)
            start = data.get('start', 8000)
            end = data.get('end', 9000)
            host = data.get('host', '127.0.0.1')
            service_name = data.get('service_name', 'unknown')
            
            if port_integration is None:
                from agents.port_agent.port_manager import PortManager
                basic_port_manager = PortManager()
                port = basic_port_manager.find_and_reserve_port(start, end, host, service_name)
            else:
                port = port_integration.port_manager.find_and_reserve_port(start, end, host, service_name)
            return JsonResponse({
                'success': True,
                'port': port,
                'host': host,
                'service_name': service_name,
                'message': f'Port {port} assigned and reserved'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    @method_decorator(csrf_exempt)
    def resolve_conflicts(self, request):
        """Resolve port conflicts"""
        try:
            data = json.loads(request.body) if request.body else {}
            auto_assign = data.get('auto_assign', True)
            
            if port_integration is None:
                return JsonResponse({
                    'success': True,
                    'message': 'Basic mode - conflict resolution not available',
                    'resolved': False
                })
            
            resolve_result = port_integration.conflict_resolver.resolve_conflicts(auto_assign)
            return JsonResponse(resolve_result)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


# Decorator-based views for simpler endpoints
@require_http_methods(["GET"])
@csrf_exempt
def port_status(request):
    """Get port status (simplified endpoint)"""
    try:
        if port_integration is None:
            return JsonResponse({
                'success': True,
                'message': 'Port Management Agent running with basic functionality',
                'basic_mode': True
            })
        
        status_report = port_integration.get_port_status_report()
        return JsonResponse(status_report)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
@csrf_exempt
def check_port_availability(request, port):
    """Check if a specific port is available"""
    try:
        host = request.GET.get('host', '127.0.0.1')
        
        if port_integration is None:
            # Basic port checking without agents
            from agents.port_agent.port_manager import PortManager
            basic_port_manager = PortManager()
            available = basic_port_manager.check_port_available(int(port), host)
            conflicts = basic_port_manager.get_port_conflicts(int(port), host)
        else:
            available = port_integration.port_manager.check_port_available(int(port), host)
            conflicts = port_integration.port_manager.get_port_conflicts(int(port), host)
        
        return JsonResponse({
            'port': int(port),
            'host': host,
            'available': available,
            'conflicts': conflicts
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
@csrf_exempt
def reserve_port_endpoint(request):
    """Reserve a port"""
    try:
        data = json.loads(request.body)
        port = data.get('port')
        service_name = data.get('service_name', 'unknown')
        host = data.get('host', '127.0.0.1')
        
        if port_integration is None:
            from agents.port_agent.port_manager import PortManager
            basic_port_manager = PortManager()
            if port:
                success = basic_port_manager.reserve_port(port, host, service_name)
                return JsonResponse({
                    'success': success,
                    'port': port,
                    'service_name': service_name
                })
            else:
                start = data.get('start', 8000)
                end = data.get('end', 9000)
                port = basic_port_manager.find_and_reserve_port(start, end, host, service_name)
                success = port is not None
                return JsonResponse({
                    'success': success,
                    'port': port,
                    'service_name': service_name
                })
        else:
            if port:
                success = port_integration.port_manager.reserve_port(port, host, service_name)
                return JsonResponse({
                    'success': success,
                    'port': port,
                    'service_name': service_name
                })
            else:
                start = data.get('start', 8000)
                end = data.get('end', 9000)
                port = port_integration.port_manager.find_and_reserve_port(start, end, host, service_name)
                return JsonResponse({
                    'success': True,
                    'port': port,
                    'service_name': service_name
                })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)