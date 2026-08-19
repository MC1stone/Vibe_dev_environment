#!/usr/bin/env python3
"""
Quick script to fix Ollama port conflict
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.port_management_agent import PortManagementAgent

def main():
    # Path to docker-compose.yml
    compose_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'docker', 'docker-compose.yml'
    )
    
    if not os.path.exists(compose_file):
        print(f"Error: docker-compose.yml not found at {compose_file}")
        sys.exit(1)
    
    print("Port Management Agent - Fixing Ollama Port Conflict")
    print("=" * 60)
    
    agent = PortManagementAgent(compose_file)
    
    # Scan for conflicts
    print("\n1. Scanning system ports...")
    agent.scan()
    
    # Detect conflicts
    print("\n2. Detecting port conflicts...")
    conflicts = agent.detect_conflicts()
    
    if conflicts:
        print(f"\n   Found {len(conflicts)} conflict(s):")
        for service, port, process in conflicts:
            print(f"   - {service}: port {port} is in use by {process}")
    else:
        print("\n   No conflicts found!")
        return
    
    # Resolve automatically
    print("\n3. Resolving conflicts automatically...")
    result = agent.resolve(auto_fix=True)
    
    print(f"\n   {result.get('message', 'Unknown result')}")
    if result.get('action'):
        print(f"   Action: {result['action']}")
    
    # Validate
    print("\n4. Validating new configuration...")
    valid, errors = agent.validate()
    
    if valid:
        print("   ✓ All ports are now available!")
        print("\n5. You can now run:")
        print("   cd docker")
        print("   docker compose down")
        print("   docker compose up -d")
    else:
        print(f"   ✗ Still have {len(errors)} conflict(s):")
        for error in errors:
            print(f"     - {error}")

if __name__ == '__main__':
    main()
