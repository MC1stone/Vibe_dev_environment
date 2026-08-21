"""
Django management command to check port usage and conflicts
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
    Check port usage and detect conflicts in the NIR_Mistral Framework
    
    Usage:
        python manage.py check_ports
        python manage.py check_ports --resolve
        python manage.py check_ports --json
        python manage.py check_ports --agent django_agent
    """
    
    help = 'Check port usage and detect conflicts in the NIR_Mistral Framework'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--resolve',
            action='store_true',
            help='Automatically resolve detected conflicts'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output results in JSON format'
        )
        parser.add_argument(
            '--agent',
            type=str,
            help='Check port for a specific agent'
        )
        parser.add_argument(
            '--scan',
            action='store_true',
            help='Scan all ports and show usage'
        )
        parser.add_argument(
            '--range',
            type=str,
            default='8000-9000',
            help='Port range to scan (format: start-end)'
        )
    
    def handle(self, *args, **options):
        """Handle the command execution"""
        integration = PortAgentIntegration()
        
        # Initialize
        self.stdout.write("Initializing Port Management Agent...")
        init_result = integration.initialize()
        
        if options['json']:
            output = {'init': init_result}
        else:
            self.stdout.write(f"✓ Docker available: {init_result.get('docker_available')}")
            self.stdout.write(f"✓ System ports found: {init_result.get('system_ports_count')}")
            self.stdout.write(f"✓ Has conflicts: {init_result.get('has_conflicts')}")
        
        # Check specific agent
        if options['agent']:
            port = integration.get_agent_port(options['agent'])
            if options['json']:
                output['agent_port'] = {options['agent']: port}
            else:
                self.stdout.write(f"Agent {options['agent']} port: {port}")
        
        # Scan ports
        elif options['scan']:
            range_parts = options['range'].split('-')
            start = int(range_parts[0]) if len(range_parts) > 0 else 8000
            end = int(range_parts[1]) if len(range_parts) > 1 else 9000
            
            scan_result = integration.port_manager.scan_ports(start, end)
            used_ports = [p for p, available in scan_result.items() if not available]
            available_ports = [p for p, available in scan_result.items() if available]
            
            if options['json']:
                output['scan'] = {
                    'range': {'start': start, 'end': end},
                    'used_ports': used_ports,
                    'available_ports': available_ports,
                    'used_count': len(used_ports),
                    'available_count': len(available_ports)
                }
            else:
                self.stdout.write(f"Port scan results for {start}-{end}:")
                self.stdout.write(f"  Used ports: {len(used_ports)}")
                self.stdout.write(f"  Available ports: {len(available_ports)}")
                if len(used_ports) <= 20:
                    self.stdout.write(f"  Used: {used_ports}")
                else:
                    self.stdout.write(f"  Used: {used_ports[:20]}...")
        
        # Check conflicts
        else:
            conflict_result = integration.conflict_resolver.detect_conflicts()
            
            if options['json']:
                output['conflicts'] = conflict_result
            else:
                if conflict_result.get('has_conflicts'):
                    self.stdout.write(self.style.WARNING(f"⚠ Port conflicts detected: {conflict_result.get('conflict_count')}"))
                    for agent, conflicts in conflict_result.get('conflicts', {}).items():
                        self.stdout.write(f"  {agent}: {conflicts}")
                else:
                    self.stdout.write(self.style.SUCCESS("✓ No port conflicts detected"))
            
            # Resolve conflicts if requested
            if options['resolve'] and conflict_result.get('has_conflicts'):
                self.stdout.write("Resolving conflicts...")
                resolve_result = integration.conflict_resolver.resolve_conflicts(auto_assign=True)
                
                if options['json']:
                    output['resolution'] = resolve_result
                else:
                    if resolve_result.get('conflicts_resolved') > 0:
                        self.stdout.write(self.style.SUCCESS(f"✓ Resolved {resolve_result.get('conflicts_resolved')} conflicts"))
                        for agent_name, mapping in resolve_result.get('port_mappings', {}).items():
                            if mapping.get('status') == 'resolved':
                                self.stdout.write(f"  {agent_name}: {mapping.get('original_port')} → {mapping.get('new_port')}")
                    else:
                        self.stdout.write(self.style.ERROR("✗ Failed to resolve conflicts"))
        
        # Output JSON if requested
        if options['json']:
            self.stdout.write(json.dumps(output, indent=2))
        
        self.stdout.write(self.style.SUCCESS("✓ Port check completed"))