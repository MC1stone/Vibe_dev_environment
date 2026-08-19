#!/usr/bin/env python3
"""
Port Management Agent for NIR Intelligence Platform

This agent intelligently manages port allocations and resolves conflicts
for the Docker-based NIR Intelligence Platform.

Features:
- Scans system for ports in use
- Detects Docker container port mappings
- Suggests alternative ports
- Automatically updates docker-compose.yml
- Validates port configuration
"""

import os
import sys
import socket
import subprocess
import yaml
import re
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
import psutil
import netifaces


@dataclass
class PortInfo:
    """Information about a port"""
    port: int
    in_use: bool
    process_name: Optional[str] = None
    pid: Optional[int] = None
    protocol: str = "tcp"
    docker_container: Optional[str] = None


@dataclass
class ServicePort:
    """Service port configuration"""
    service_name: str
    container_port: int
    host_port: int
    required: bool = True


class PortManager:
    """Manages port allocations and conflicts"""
    
    # Default ports for NIR Intelligence Platform services
    DEFAULT_PORTS = {
        'django': 8000,
        'postgres': 5432,
        'qdrant': 6333,
        'qdrant_grpc': 6334,
        'ollama': 11434,
        'n8n': 5678,
        'mcp_server': 8001,
    }
    
    # Alternative ports for each service
    ALTERNATIVE_PORTS = {
        'django': [8000, 8001, 8002, 8080, 8888],
        'postgres': [5432, 5433, 5434, 15432],
        'qdrant': [6333, 6335, 6336, 16333],
        'qdrant_grpc': [6334, 6337, 6338, 16334],
        'ollama': [11434, 11435, 11436, 11437, 11438],
        'n8n': [5678, 5679, 5680, 5681],
        'mcp_server': [8001, 8002, 8003, 8004],
    }
    
    def __init__(self, compose_file: str = None):
        self.compose_file = compose_file or os.path.join(
            os.path.dirname(__file__), 
            '..', 'docker', 'docker-compose.yml'
        )
        self._ports_in_use: Dict[int, PortInfo] = {}
        self._docker_ports: Dict[str, List[Tuple[int, int]]] = {}
        
    def scan_system_ports(self, port_range: Tuple[int, int] = (1, 65535)) -> Dict[int, PortInfo]:
        """Scan system for ports in use"""
        ports_in_use = {}
        
        try:
            # Method 1: Use netstat/ss for faster scanning
            try:
                result = subprocess.run(
                    ['ss', '-tlnp'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    self._parse_ss_output(result.stdout, ports_in_use)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # Fallback to socket method
                self._scan_ports_with_socket(ports_in_use, port_range)
                
        except Exception as e:
            print(f"Warning: Could not scan ports: {e}")
        
        self._ports_in_use = ports_in_use
        return ports_in_use
    
    def _parse_ss_output(self, output: str, ports_in_use: Dict[int, PortInfo]):
        """Parse ss command output"""
        for line in output.split('\n'):
            if ':' in line and ('LISTEN' in line or 'ESTAB' in line):
                # Extract port and process info
                parts = line.split()
                for part in parts:
                    if ':' in part:
                        # Parse address:port
                        addr_port = part.split(':')
                        if len(addr_port) >= 2:
                            try:
                                port = int(addr_port[-1])
                                if port < 1 or port > 65535:
                                    continue
                                
                                # Find process info
                                pid = None
                                process_name = None
                                for p in parts:
                                    if 'pid=' in p:
                                        pid = int(p.split('pid=')[1].split(',')[0])
                                        break
                                
                                if pid:
                                    try:
                                        proc = psutil.Process(pid)
                                        process_name = proc.name()
                                    except:
                                        pass
                                
                                ports_in_use[port] = PortInfo(
                                    port=port,
                                    in_use=True,
                                    process_name=process_name,
                                    pid=pid
                                )
                            except ValueError:
                                continue
    
    def _scan_ports_with_socket(self, ports_in_use: Dict[int, PortInfo], 
                                  port_range: Tuple[int, int]):
        """Scan ports using socket connections"""
        start, end = port_range
        # Only scan common ports for performance
        common_ports = list(range(1, 1025)) + list(range(8000, 9000)) + \
                      list(range(10000, 12000)) + list(range(50000, 51000))
        
        for port in common_ports:
            if port < start or port > end:
                continue
            if self._is_port_in_use(port):
                ports_in_use[port] = PortInfo(port=port, in_use=True)
    
    def _is_port_in_use(self, port: int, timeout: float = 0.1) -> bool:
        """Check if a specific port is in use"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                result = s.connect_ex(('127.0.0.1', port))
                return result == 0
        except:
            return False
    
    def scan_docker_ports(self) -> Dict[str, List[Tuple[int, int]]]:
        """Scan Docker containers for port mappings"""
        docker_ports = {}
        
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}:{{.Ports}}'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if ':' in line:
                        name, ports_str = line.split(':', 1)
                        docker_ports[name] = self._parse_docker_ports(ports_str)
                        
        except Exception as e:
            print(f"Warning: Could not scan Docker ports: {e}")
        
        self._docker_ports = docker_ports
        return docker_ports
    
    def _parse_docker_ports(self, ports_str: str) -> List[Tuple[int, int]]:
        """Parse Docker port mappings"""
        mappings = []
        
        if not ports_str or ports_str == '(none)':
            return mappings
        
        # Parse port mappings like "0.0.0.0:8000->8000/tcp"
        for mapping in ports_str.split(','):
            mapping = mapping.strip()
            if '->' in mapping:
                host_part, container_part = mapping.split('->')
                
                # Extract host port
                host_port = None
                if ':' in host_part:
                    host_port_str = host_part.split(':')[-1]
                    try:
                        host_port = int(host_port_str)
                    except ValueError:
                        pass
                
                # Extract container port
                container_port = None
                if ':' in container_part:
                    container_port_str = container_part.split(':')[0]
                    try:
                        container_port = int(container_port_str)
                    except ValueError:
                        pass
                
                if host_port and container_port:
                    mappings.append((host_port, container_port))
        
        return mappings
    
    def get_conflicting_ports(self, services: List[ServicePort]) -> List[Tuple[str, int, int]]:
        """Get list of port conflicts"""
        conflicts = []
        
        for service in services:
            if service.host_port in self._ports_in_use:
                conflicts.append((
                    service.service_name,
                    service.host_port,
                    self._ports_in_use[service.host_port].process_name or 
                    self._ports_in_use[service.host_port].pid or 'unknown'
                ))
        
        return conflicts
    
    def find_alternative_port(self, service_name: str, 
                              preferred_port: int) -> Optional[int]:
        """Find an alternative port for a service"""
        if service_name not in self.ALTERNATIVE_PORTS:
            return None
        
        alternatives = self.ALTERNATIVE_PORTS[service_name]
        
        # Try preferred port first
        if preferred_port not in self._ports_in_use:
            return preferred_port
        
        # Try other alternatives
        for port in alternatives:
            if port != preferred_port and port not in self._ports_in_use:
                return port
        
        # Find any available port near the preferred one
        for offset in range(1, 100):
            candidate = preferred_port + offset
            if candidate > 65535:
                break
            if candidate not in self._ports_in_use:
                return candidate
        
        return None
    
    def load_compose_file(self) -> Optional[Dict]:
        """Load docker-compose.yml file"""
        try:
            with open(self.compose_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading compose file: {e}")
            return None
    
    def save_compose_file(self, data: Dict) -> bool:
        """Save docker-compose.yml file"""
        try:
            with open(self.compose_file, 'w') as f:
                yaml.dump(data, f, sort_keys=False, default_flow_style=False)
            return True
        except Exception as e:
            print(f"Error saving compose file: {e}")
            return False
    
    def extract_service_ports(self, compose_data: Dict) -> List[ServicePort]:
        """Extract service port configurations from compose file"""
        services = []
        
        if not compose_data or 'services' not in compose_data:
            return services
        
        for service_name, config in compose_data['services'].items():
            if 'ports' in config:
                for port_mapping in config['ports']:
                    # Parse port mapping
                    if isinstance(port_mapping, str):
                        # Format: "host_port:container_port"
                        if ':' in port_mapping:
                            host_port_str, container_port_str = port_mapping.split(':')
                            try:
                                host_port = int(host_port_str)
                                container_port = int(container_port_str)
                                services.append(ServicePort(
                                    service_name=service_name,
                                    container_port=container_port,
                                    host_port=host_port
                                ))
                            except ValueError:
                                continue
                    elif isinstance(port_mapping, dict):
                        # Complex port mapping
                        if 'published' in port_mapping and 'target' in port_mapping:
                            try:
                                host_port = int(port_mapping['published'])
                                container_port = int(port_mapping['target'])
                                services.append(ServicePort(
                                    service_name=service_name,
                                    container_port=container_port,
                                    host_port=host_port
                                ))
                            except (ValueError, TypeError):
                                continue
        
        return services
    
    def resolve_port_conflicts(self, compose_data: Dict = None) -> Dict[str, Dict]:
        """Resolve port conflicts in docker-compose.yml"""
        if compose_data is None:
            compose_data = self.load_compose_file()
            if compose_data is None:
                return {}
        
        # Scan current port usage
        self.scan_system_ports()
        self.scan_docker_ports()
        
        # Extract current service ports
        services = self.extract_service_ports(compose_data)
        
        # Find conflicts
        conflicts = self.get_conflicting_ports(services)
        
        if not conflicts:
            print("No port conflicts detected!")
            return {}
        
        print(f"Found {len(conflicts)} port conflict(s):")
        for service_name, port, process in conflicts:
            print(f"  - {service_name}: port {port} is in use by {process}")
        
        # Resolve conflicts
        changes = {}
        for service in services:
            if service.host_port in self._ports_in_use:
                alternative = self.find_alternative_port(
                    service.service_name, 
                    service.host_port
                )
                if alternative:
                    changes[service.service_name] = {
                        'old_port': service.host_port,
                        'new_port': alternative,
                        'container_port': service.container_port
                    }
                    # Update the compose data
                    if 'services' in compose_data and service.service_name in compose_data['services']:
                        for i, port_mapping in enumerate(compose_data['services'][service.service_name].get('ports', [])):
                            if isinstance(port_mapping, str) and str(service.host_port) in port_mapping:
                                new_mapping = f"{alternative}:{service.container_port}"
                                compose_data['services'][service.service_name]['ports'][i] = new_mapping
                            elif isinstance(port_mapping, dict):
                                if port_mapping.get('published') == service.host_port:
                                    port_mapping['published'] = alternative
        
        return changes
    
    def auto_fix_ports(self) -> bool:
        """Automatically detect and fix port conflicts"""
        compose_data = self.load_compose_file()
        if compose_data is None:
            return False
        
        changes = self.resolve_port_conflicts(compose_data)
        
        if changes:
            print("\nApplying port changes:")
            for service_name, change in changes.items():
                print(f"  - {service_name}: {change['old_port']} -> {change['new_port']}")
            
            # Save the updated compose file
            if self.save_compose_file(compose_data):
                print(f"\nUpdated {self.compose_file}")
                return True
        
        return False
    
    def validate_ports(self) -> Tuple[bool, List[str]]:
        """Validate that all configured ports are available"""
        compose_data = self.load_compose_file()
        if compose_data is None:
            return False, ["Could not load compose file"]
        
        self.scan_system_ports()
        self.scan_docker_ports()
        
        services = self.extract_service_ports(compose_data)
        errors = []
        
        for service in services:
            if service.host_port in self._ports_in_use:
                port_info = self._ports_in_use[service.host_port]
                errors.append(
                    f"Port {service.host_port} for {service.service_name} "
                    f"is in use by {port_info.process_name or port_info.pid or 'unknown'}"
                )
        
        return len(errors) == 0, errors
    
    def get_port_status(self) -> Dict[str, any]:
        """Get comprehensive port status"""
        self.scan_system_ports()
        self.scan_docker_ports()
        
        compose_data = self.load_compose_file()
        services = []
        if compose_data:
            services = self.extract_service_ports(compose_data)
        
        conflicts = self.get_conflicting_ports(services)
        
        return {
            'ports_in_use': len(self._ports_in_use),
            'docker_containers': len(self._docker_ports),
            'configured_services': len(services),
            'conflicts': [
                {'service': s, 'port': p, 'used_by': u} 
                for s, p, u in conflicts
            ],
            'suggestions': self.suggest_port_changes()
        }
    
    def suggest_port_changes(self) -> List[Dict]:
        """Suggest port changes to resolve conflicts"""
        compose_data = self.load_compose_file()
        if compose_data is None:
            return []
        
        self.scan_system_ports()
        services = self.extract_service_ports(compose_data)
        suggestions = []
        
        for service in services:
            if service.host_port in self._ports_in_use:
                alternative = self.find_alternative_port(
                    service.service_name,
                    service.host_port
                )
                if alternative:
                    suggestions.append({
                        'service': service.service_name,
                        'current_port': service.host_port,
                        'suggested_port': alternative,
                        'container_port': service.container_port
                    })
        
        return suggestions


class PortManagementAgent:
    """
    Port Management Agent for NIR Intelligence Platform
    
    This agent provides intelligent port management capabilities:
    - Detect port conflicts
    - Suggest alternative ports
    - Automatically fix docker-compose.yml
    - Validate port configuration
    """
    
    def __init__(self, compose_file: str = None):
        self.port_manager = PortManager(compose_file)
        self.name = "Port Management Agent"
        self.description = "Manages port allocations and resolves conflicts for Docker services"
        
    def scan(self) -> Dict[str, any]:
        """Scan system and Docker for port usage"""
        print(f"{self.name}: Scanning system ports...")
        self.port_manager.scan_system_ports()
        
        print(f"{self.name}: Scanning Docker containers...")
        self.port_manager.scan_docker_ports()
        
        return self.port_manager.get_port_status()
    
    def detect_conflicts(self) -> List[Tuple[str, int, str]]:
        """Detect port conflicts"""
        print(f"{self.name}: Detecting port conflicts...")
        compose_data = self.port_manager.load_compose_file()
        if compose_data is None:
            return []
        
        services = self.port_manager.extract_service_ports(compose_data)
        return self.port_manager.get_conflicting_ports(services)
    
    def resolve(self, auto_fix: bool = True) -> Dict[str, any]:
        """Resolve port conflicts"""
        print(f"{self.name}: Resolving port conflicts...")
        
        if auto_fix:
            success = self.port_manager.auto_fix_ports()
            if success:
                return {
                    'status': 'success',
                    'message': 'Port conflicts resolved automatically',
                    'action': 'docker-compose.yml updated'
                }
            else:
                return {
                    'status': 'no_changes',
                    'message': 'No port conflicts found'
                }
        else:
            changes = self.port_manager.resolve_port_conflicts()
            return {
                'status': 'manual_review',
                'changes': changes,
                'message': 'Review suggested changes above'
            }
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate port configuration"""
        print(f"{self.name}: Validating port configuration...")
        return self.port_manager.validate_ports()
    
    def get_suggestions(self) -> List[Dict]:
        """Get port change suggestions"""
        return self.port_manager.suggest_port_changes()
    
    def check_specific_port(self, port: int) -> Dict[str, any]:
        """Check if a specific port is available"""
        in_use = self.port_manager._is_port_in_use(port)
        
        info = {
            'port': port,
            'in_use': in_use,
            'available': not in_use
        }
        
        if in_use and port in self.port_manager._ports_in_use:
            port_info = self.port_manager._ports_in_use[port]
            info['process_name'] = port_info.process_name
            info['pid'] = port_info.pid
        
        return info


def main():
    """Command-line interface for Port Management Agent"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Port Management Agent for NIR Intelligence Platform'
    )
    parser.add_argument('--compose', '-c', 
                        help='Path to docker-compose.yml file')
    parser.add_argument('--scan', action='store_true',
                        help='Scan system and Docker ports')
    parser.add_argument('--detect', action='store_true',
                        help='Detect port conflicts')
    parser.add_argument('--resolve', action='store_true',
                        help='Resolve port conflicts automatically')
    parser.add_argument('--validate', action='store_true',
                        help='Validate port configuration')
    parser.add_argument('--suggest', action='store_true',
                        help='Suggest port changes')
    parser.add_argument('--check', type=int,
                        help='Check if a specific port is available')
    parser.add_argument('--fix', action='store_true',
                        help='Automatically fix port conflicts')
    
    args = parser.parse_args()
    
    # Determine compose file path
    compose_file = args.compose
    if not compose_file:
        # Try to find compose file
        possible_paths = [
            'docker/docker-compose.yml',
            'docker-compose.yml',
            '../docker/docker-compose.yml',
            os.path.join(os.path.dirname(__file__), '..', 'docker', 'docker-compose.yml')
        ]
        for path in possible_paths:
            if os.path.exists(path):
                compose_file = path
                break
    
    if not compose_file:
        print("Error: Could not find docker-compose.yml file")
        sys.exit(1)
    
    agent = PortManagementAgent(compose_file)
    
    if args.scan:
        status = agent.scan()
        print("\nPort Status:")
        print(f"  Ports in use: {status['ports_in_use']}")
        print(f"  Docker containers: {status['docker_containers']}")
        print(f"  Configured services: {status['configured_services']}")
        if status['conflicts']:
            print(f"\n  Conflicts found: {len(status['conflicts'])}")
            for conflict in status['conflicts']:
                print(f"    - {conflict['service']}: port {conflict['port']} used by {conflict['used_by']}")
        else:
            print("\n  No conflicts found!")
        
        if status['suggestions']:
            print(f"\n  Suggestions: {len(status['suggestions'])}")
            for suggestion in status['suggestions']:
                print(f"    - {suggestion['service']}: {suggestion['current_port']} -> {suggestion['suggested_port']}")
    
    elif args.detect:
        conflicts = agent.detect_conflicts()
        if conflicts:
            print(f"\nFound {len(conflicts)} port conflict(s):")
            for service, port, process in conflicts:
                print(f"  - {service}: port {port} is in use by {process}")
        else:
            print("\nNo port conflicts detected!")
    
    elif args.resolve or args.fix:
        result = agent.resolve(auto_fix=True)
        print(f"\n{result.get('message', 'Unknown result')}")
        if result.get('action'):
            print(f"Action: {result['action']}")
    
    elif args.validate:
        valid, errors = agent.validate()
        if valid:
            print("\n✓ All ports are available!")
        else:
            print(f"\n✗ Found {len(errors)} port conflict(s):")
            for error in errors:
                print(f"  - {error}")
    
    elif args.suggest:
        suggestions = agent.get_suggestions()
        if suggestions:
            print(f"\nSuggested port changes ({len(suggestions)}):")
            for suggestion in suggestions:
                print(f"  - {suggestion['service']}: {suggestion['current_port']} -> {suggestion['suggested_port']}")
        else:
            print("\nNo port changes suggested!")
    
    elif args.check:
        info = agent.check_specific_port(args.check)
        if info['available']:
            print(f"\n✓ Port {info['port']} is available!")
        else:
            print(f"\n✗ Port {info['port']} is in use")
            if info.get('process_name'):
                print(f"  Process: {info['process_name']} (PID: {info.get('pid', 'unknown')})")
    
    else:
        # Default: scan and detect
        print("Port Management Agent - NIR Intelligence Platform")
        print("=" * 50)
        
        status = agent.scan()
        print(f"\nPorts in use: {status['ports_in_use']}")
        print(f"Docker containers: {status['docker_containers']}")
        print(f"Configured services: {status['configured_services']}")
        
        if status['conflicts']:
            print(f"\n⚠️  {len(status['conflicts'])} port conflict(s) detected:")
            for conflict in status['conflicts']:
                print(f"  - {conflict['service']}: port {conflict['port']} used by {conflict['used_by']}")
            
            print("\nRun with --resolve to automatically fix conflicts")
            print("Run with --suggest to see suggested changes")
        else:
            print("\n✓ No port conflicts detected!")


if __name__ == '__main__':
    try:
        import psutil
        import yaml
    except ImportError as e:
        print(f"Error: Missing required package: {e}")
        print("Install with: pip install psutil pyyaml")
        sys.exit(1)
    
    main()
