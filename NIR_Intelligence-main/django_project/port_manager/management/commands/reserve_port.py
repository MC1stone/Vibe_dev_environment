"""
Django management command to reserve ports for services
"""

import sys
import json
from pathlib import Path
from django.core.management.base import BaseCommand

# Import path configuration
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from path_config import setup_project_paths
setup_project_paths()

from agents.port_agent import PortAgentIntegration


class Command(BaseCommand):
    """
    Reserve a port for a service or agent
    
    Usage:
        python manage.py reserve_port django_agent
        python manage.py reserve_port --port 8080 --service my_service
        python manage.py reserve_port --range 9000-9100 --service new_service
        python manage.py reserve_port --list
    """
    
    help = 'Reserve a port for a service or agent'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'agent_name',
            type=str,
            nargs='?',
            help='Name of the agent to reserve port for'
        )
        parser.add_argument(
            '--port',
            type=int,
            help='Specific port number to reserve'
        )
        parser.add_argument(
            '--service',
            type=str,
            help='Service name for the port reservation'
        )
        parser.add_argument(
            '--range',
            type=str,
            help='Port range to search (format: start-end)'
        )
        parser.add_argument(
            '--host',
            type=str,
            default='127.0.0.1',
            help='Host address for the port'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all reserved ports'
        )
        parser.add_argument(
            '--release',
            action='store_true',
            help='Release a reserved port'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output in JSON format'
        )
    
    def handle(self, *args, **options):
        """Handle the command execution"""
        integration = PortAgentIntegration()
        
        # List reserved ports
        if options['list']:
            status_result = integration.get_port_status_report()
            reserved_ports = status_result.get('reserved_ports', [])
            
            if options['json']:
                output = {'reserved_ports': reserved_ports, 'count': len(reserved_ports)}
                self.stdout.write(json.dumps(output, indent=2))
            else:
                if reserved_ports:
                    self.stdout.write(f"Reserved ports ({len(reserved_ports)}):")
                    for port_info in reserved_ports:
                        self.stdout.write(f"  Port {port_info.get('port')}: {port_info.get('service_name')} on {port_info.get('host')}")
                else:
                    self.stdout.write("No ports are currently reserved")
        
        # Release a port
        elif options['release'] and options['agent_name']:
            result = integration.release_agent_port(options['agent_name'], options['host'])
            
            if options['json']:
                self.stdout.write(json.dumps(result, indent=2))
            else:
                if result.get('success'):
                    self.stdout.write(self.style.SUCCESS(f"✓ Released port for {options['agent_name']}: {result.get('port')}"))
                else:
                    self.stdout.write(self.style.ERROR(f"✗ Failed to release port: {result.get('message')}"))
        
        # Reserve a port
        else:
            if options['agent_name']:
                # Reserve port for agent
                result = integration.reserve_port_for_agent(
                    options['agent_name'], 
                    options['port'], 
                    options['host']
                )
            elif options['service']:
                # Reserve port for service
                if options['port']:
                    # Reserve specific port
                    result = integration.port_manager.reserve_port(
                        options['port'], 
                        options['host'], 
                        options['service']
                    )
                    result = {'success': result, 'port': options['port'], 'service_name': options['service']}
                else:
                    # Find and reserve a port in range
                    if options['range']:
                        range_parts = options['range'].split('-')
                        start = int(range_parts[0]) if len(range_parts) > 0 else 8000
                        end = int(range_parts[1]) if len(range_parts) > 1 else 9000
                    else:
                        start, end = 8000, 9000
                    
                    port = integration.port_manager.find_and_reserve_port(
                        start, end, options['host'], options['service']
                    )
                    result = {'success': True, 'port': port, 'service_name': options['service']}
            else:
                self.stdout.write(self.style.ERROR("✗ Please specify either --agent_name or --service"))
                return
            
            if options['json']:
                self.stdout.write(json.dumps(result, indent=2))
            else:
                if result.get('success'):
                    self.stdout.write(self.style.SUCCESS(f"✓ Reserved port {result.get('port')} for {result.get('service_name', options.get('agent_name', 'unknown'))}"))
                else:
                    self.stdout.write(self.style.ERROR(f"✗ Failed to reserve port: {result.get('message', 'Unknown error')}"))
        
        self.stdout.write(self.style.SUCCESS("✓ Port reservation completed"))