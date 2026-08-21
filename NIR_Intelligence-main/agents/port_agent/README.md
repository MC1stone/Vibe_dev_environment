# 🚀 Port Management Agent for NIR_Mistral Framework

## 📋 Overview

The **Port Management Agent** is a comprehensive solution for managing network ports in the NIR_Mistral Framework. It provides thread-safe port reservation, cross-platform port scanning, Docker-specific port management, and integration with existing framework agents to resolve port conflicts.

### **Key Features**

- ✅ **Thread-Safe Port Reservation System** - Prevents race conditions in multi-threaded environments
- ✅ **Cross-Platform Support** - Works on Windows, Linux, and macOS
- ✅ **Docker Integration** - Manages Docker container port mappings
- ✅ **Framework Integration** - Resolves port conflicts between NIR_Mistral agents
- ✅ **Comprehensive Error Handling** - Robust validation and error reporting
- ✅ **CrewAI Compatibility** - Can be used as a tool within CrewAI agents

## 📁 Structure

```
agents/port_agent/
├── __init__.py              # Main module exports
├── exceptions.py            # Custom exceptions
├── port_manager.py          # Core port management
├── docker_port_manager.py  # Docker-specific management
├── integration.py           # Framework integration
├── agent.py                 # CrewAI agent interface
├── test_port_agent.py       # Comprehensive test suite
└── README.md                # This file
```

## 🔧 Installation

The Port Management Agent is automatically included with the NIR_Mistral Framework. No additional installation is required.

### **Dependencies**

- Python 3.8+
- Standard library modules: `socket`, `subprocess`, `threading`, `re`, `json`, `yaml`
- Optional: `ss`, `netstat`, or `lsof` for port scanning (usually pre-installed)
- Optional: Docker for Docker-specific functionality

## 🚀 Quick Start

### **Basic Usage**

```python
# Import the port agent
from agents.port_agent import port_agent

# Assign a free port
port = port_agent.assign_port(8000, 9000, "127.0.0.1", "my_service")
print(f"Assigned port: {port['port']}")

# Check if a port is available
result = port_agent.check_port(8080)
print(f"Port 8080 available: {result['available']}")

# Release a port
port_agent.release_port(port['port'])
```

### **Framework Integration**

```python
from agents.port_agent import PortAgentIntegration

# Initialize
integration = PortAgentIntegration()

# Detect port conflicts
conflicts = integration.conflict_resolver.detect_conflicts()
print(f"Conflicts detected: {conflicts['has_conflicts']}")

# Resolve conflicts automatically
result = integration.resolve_framework_conflicts(auto_assign=True)
print(f"Resolved {result['conflicts_resolved']} conflicts")

# Get port for a specific agent
port = integration.get_agent_port('django_agent')
print(f"Django agent port: {port}")
```

### **Docker Integration**

```python
from agents.port_agent import port_agent

# Check Docker availability
docker_available = port_agent.is_docker_available()
print(f"Docker available: {docker_available}")

# Get running containers
containers = port_agent.get_running_containers()
for container in containers:
    print(f"Container: {container['name']}, Ports: {container['host_ports']}")

# Reserve a port for Docker
result = port_agent.reserve_docker_port(container_port=8000, start=8000, end=9000)
print(f"Reserved host port: {result['host_port']}")
```

## 🔌 CrewAI Integration

### **Using as a Tool**

```python
from crewai import Agent, Task, Crew
from agents.port_agent import port_management_tool

# Create an agent with port management capabilities
port_manager_agent = Agent(
    role='DevOps Port Manager',
    goal='Manage ports and prevent conflicts in the NIR_Mistral Framework',
    backstory='''
        You are an expert in network port management. Your job is to ensure that
        all services in the NIR_Mistral Framework have the ports they need without
        conflicts. You can scan for available ports, reserve ports for services,
        and manage Docker container port mappings.
    ''',
    tools=[port_management_tool],
    verbose=True
)

# Create a task to assign ports
task = Task(
    description='''
        1. Scan the system for used ports
        2. Find a free port in the range 8000-9000 for a new Django service
        3. Reserve that port for the service
        4. Return the assigned port number
    ''',
    expected_output='The assigned port number',
    agent=port_manager_agent
)

# Execute the task
crew = Crew(agents=[port_manager_agent], tasks=[task])
result = crew.kickoff()
print(f"Assigned port: {result}")
```

### **Tool Actions**

The `port_management_tool` supports these actions:

#### **General Port Actions**
- `scan` - Scan a range of ports
- `check` - Check if a port is available
- `assign` - Assign and reserve a free port
- `reserve` - Reserve a specific port
- `release` - Release a reserved port
- `find` - Find a free port without reserving
- `status` - Get status of reserved ports
- `conflicts` - Get port conflict information
- `info` - Get detailed port information

#### **Docker Actions**
- `docker_containers` - Get running Docker containers
- `docker_mappings` - Get Docker port mappings
- `docker_reserve` - Reserve Docker port
- `docker_release` - Release Docker port

#### **Framework Actions**
- `detect_conflicts` - Detect framework port conflicts
- `resolve_conflicts` - Resolve framework port conflicts
- `agent_port` - Get port for agent
- `reserve_agent_port` - Reserve port for agent
- `release_agent_port` - Release agent port
- `status_report` - Get comprehensive port status report
- `cleanup` - Clean up all reserved ports
- `initialize` - Initialize port management system

## 🎯 Use Cases

### **1. Preventing Port Conflicts**

```python
from agents.port_agent import port_agent

# Before starting a service, check if the port is available
if port_agent.check_port(8000)['available']:
    # Port is available, start the service
    start_django_server(port=8000)
else:
    # Port is in use, find a new one
    new_port = port_agent.assign_port(8000, 8100, "127.0.0.1", "django")
    start_django_server(port=new_port['port'])
```

### **2. Dynamic Port Assignment**

```python
from agents.port_agent import port_agent

# Assign ports dynamically for multiple services
services = ["django", "weaviate", "postgresql", "mcp_server"]
ports = {}

for service in services:
    port = port_agent.assign_port(8000, 9000, "127.0.0.1", service)
    ports[service] = port['port']
    print(f"{service}: {port['port']}")
```

### **3. Docker Container Management**

```python
from agents.port_agent import port_agent

# Start a container with automatic port assignment
result = port_agent.start_container_with_port(
    image="my-django-app",
    container_name="nir_django",
    container_port=8000,
    host="127.0.0.1"
)
print(f"Container started with mapping: {result['mapping']}")

# Later, stop the container and release the port
port_agent.stop_container("nir_django")
```

### **4. Framework Port Conflict Resolution**

```python
from agents.port_agent import PortAgentIntegration

# Initialize
integration = PortAgentIntegration()

# Detect and resolve conflicts
conflict_result = integration.detect_conflicts()
if conflict_result['has_conflicts']:
    print(f"Found {conflict_result['conflict_count']} conflicts")
    
    # Resolve conflicts
    resolution = integration.resolve_framework_conflicts(auto_assign=True)
    print(f"Resolved {resolution['conflicts_resolved']} conflicts")
    
    # Get updated port mappings
    for agent, mapping in resolution['port_mappings'].items():
        if mapping['status'] == 'resolved':
            print(f"{agent}: {mapping['original_port']} -> {mapping['new_port']}")
```

## 📊 API Reference

### **PortManager Class**

The core class for port management.

#### **Methods**

- `validate_port(port, host=None)` - Validate port number
- `validate_host(host)` - Validate host address
- `check_port_available(port, host=None)` - Check if port is available
- `reserve_port(port, host=None, service_name=None)` - Reserve a specific port
- `release_port(port, host=None)` - Release a reserved port
- `find_and_reserve_port(start, end, host, service_name, max_attempts, random_search)` - Find and reserve a free port
- `find_free_port(start, end, host)` - Find a free port without reserving
- `get_reserved_ports()` - Get all reserved ports
- `get_port_info(port)` - Get information about a specific port
- `release_all_ports()` - Release all reserved ports
- `scan_ports(start, end, host)` - Scan a range of ports
- `get_port_conflicts(port, host)` - Get port conflict information

### **DockerPortManager Class**

Docker-specific port management.

#### **Methods**

- `is_docker_available()` - Check if Docker is available
- `get_docker_version()` - Get Docker version
- `get_running_containers()` - Get running Docker containers
- `get_container_info(container_name)` - Get container information
- `get_container_port_mappings()` - Get all Docker port mappings
- `get_used_docker_ports()` - Get all host ports used by Docker
- `find_available_host_port(container_port, start, end, host)` - Find available host port
- `reserve_docker_port(container_port, host_port, start, end, host, service_name)` - Reserve Docker port
- `release_docker_port(host_port, host)` - Release Docker port
- `check_docker_port_conflicts(host_port, host)` - Check Docker port conflicts
- `get_docker_port_status(host_port, host)` - Get Docker port status
- `start_container_with_port(image, container_name, container_port, host_port, host, **kwargs)` - Start container with port
- `stop_container(container_name)` - Stop container and release ports
- `get_port_mapping_suggestions(services, start_port, end_port)` - Get port mapping suggestions

### **PortManagementAgent Class**

High-level agent interface.

#### **Methods**

- `execute(action, **kwargs)` - Execute a port management action

### **PortAgentIntegration Class**

Framework integration.

#### **Methods**

- `initialize()` - Initialize the port management system
- `resolve_framework_conflicts(auto_assign)` - Resolve framework port conflicts
- `get_agent_port(agent_name)` - Get port for a specific agent
- `reserve_port_for_agent(agent_name, port, host)` - Reserve port for agent
- `release_agent_port(agent_name, host)` - Release agent port
- `execute_port_action(action, **kwargs)` - Execute port action
- `get_port_status_report()` - Get comprehensive port status report
- `cleanup()` - Clean up all reserved ports

## 🔍 Configuration

The Port Management Agent can be configured using `config/port_agent_config.yaml`:

```yaml
port_agent:
  enabled: true
  default_host: "127.0.0.1"
  
  port_scanning:
    enabled: true
    cache_timeout: 30.0
    
  port_reservation:
    enabled: true
    max_attempts: 100
    random_search: true
    
  port_ranges:
    django: {start: 8000, end: 8050}
    weaviate: {start: 8080, end: 8090}
    database: {start: 5432, end: 5450}
    monitoring: {start: 9000, end: 9100}
    general: {start: 10000, end: 11000}

docker:
  enabled: true
  check_available: true
  timeout: 10

framework_integration:
  enabled: true
  auto_resolve_conflicts: true
  update_config: true
```

## 🛠️ Customization

### **Adding Custom Port Ranges**

```python
from agents.port_agent import PortManager

# Create custom port manager
port_manager = PortManager()

# Define custom port ranges
custom_ranges = {
    'custom_service': {'start': 20000, 'end': 21000}
}

# Use the port manager with custom ranges
port = port_manager.find_and_reserve_port(
    custom_ranges['custom_service']['start'],
    custom_ranges['custom_service']['end'],
    "127.0.0.1",
    "custom_service"
)
```

### **Creating Custom Agents**

```python
from agents.port_agent import PortManagementAgentCrewAI

class MyPortAgent(PortManagementAgentCrewAI):
    def custom_method(self):
        # Add custom functionality
        result = self.assign_port(8000, 9000, "127.0.0.1", "my_custom_service")
        return result
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral
python agents/port_agent/test_port_agent.py
```

This will test:
- Basic port operations
- Port availability checking
- Port reservation system
- Find and reserve functionality
- Thread safety
- Cross-platform port scanning
- Docker port management
- Framework integration
- CrewAI integration
- Error handling

## 📝 Examples

### **Example 1: Simple Port Assignment**

```python
from agents.port_agent import port_agent

# Assign a port for a Django service
port = port_agent.assign_port(8000, 8050, "127.0.0.1", "django_service")
print(f"Django service assigned to port: {port['port']}")

# Later, release the port
port_agent.release_port(port['port'])
```

### **Example 2: Framework Conflict Resolution**

```python
from agents.port_agent import PortAgentIntegration

# Initialize
integration = PortAgentIntegration()

# Detect conflicts
conflicts = integration.detect_conflicts()
if conflicts['has_conflicts']:
    print("Port conflicts detected:")
    for agent, conflict_list in conflicts['conflicts'].items():
        print(f"  {agent}: {conflict_list}")
    
    # Resolve conflicts
    resolution = integration.resolve_framework_conflicts()
    print(f"\nResolved {resolution['conflicts_resolved']} conflicts")
    
    # Show new port assignments
    for agent, mapping in resolution['port_mappings'].items():
        if mapping['status'] == 'resolved':
            print(f"  {agent}: {mapping['original_port']} -> {mapping['new_port']}")
```

### **Example 3: Docker Container with Dynamic Port**

```python
from agents.port_agent import port_agent

# Reserve a port for a Docker container
result = port_agent.reserve_docker_port(
    container_port=8000,
    start=8000,
    end=9000,
    host="127.0.0.1",
    service_name="my_container"
)

print(f"Container port 8000 mapped to host port: {result['host_port']}")

# Start the container (pseudo-code)
# docker run -p 127.0.0.1:{result['host_port']}:8000 my_image

# Later, release the port
port_agent.release_docker_port(result['host_port'])
```

### **Example 4: Port Status Report**

```python
from agents.port_agent import port_agent

# Get comprehensive port status report
report = port_agent.get_port_status_report()

print("Port Status Report:")
print(f"  System ports in use: {len(report['system_ports'])}")
print(f"  Reserved ports: {report['reserved_ports']}")
print(f"  Docker available: {report['docker_available']}")

if report['docker_available']:
    print(f"  Docker ports in use: {report['docker_ports']}")

print("\nAgent Port Status:")
for agent, status in report['agents'].items():
    print(f"  {agent}:")
    print(f"    Configured: {status['configured_port']}")
    print(f"    Current: {status['current_port']}")
    print(f"    Available: {status['is_available']}")
    if status['has_conflicts']:
        print(f"    Conflicts: {status['conflicts']}")
```

## 🔒 Security

### **Port Validation**

- Only ports in range 1-65535 are allowed
- Host addresses are validated
- Reserved system ports (22, 80, 443, etc.) are avoided by default

### **Thread Safety**

- All port operations use threading locks
- Prevents race conditions in multi-threaded environments
- Safe for use in concurrent applications

### **Error Handling**

- Comprehensive exception handling
- Graceful degradation when features are unavailable
- Detailed error messages for debugging

## 📊 Performance

- **Port Scanning**: Cached for 30 seconds to avoid frequent system calls
- **Port Checking**: Uses socket binding for reliable availability checking
- **Port Assignment**: Random search to avoid clustering
- **Thread Safety**: Minimal overhead with efficient locking

## 🤝 Contributing

1. **Report Issues**: Open issues for bugs or feature requests
2. **Submit Pull Requests**: Contribute improvements and fixes
3. **Add Tests**: Add comprehensive tests for new functionality
4. **Update Documentation**: Keep documentation up to date

## 📄 License

This Port Management Agent is part of the NIR_Mistral Framework and is licensed under the same terms as the main project.

## 🏁 Conclusion

The **Port Management Agent** provides a comprehensive solution for managing network ports in the NIR_Mistral Framework. It addresses the common issue of port conflicts and provides dynamic port assignment capabilities that work across different platforms and with Docker containers.

### **Key Benefits**

- **✅ Eliminates Port Conflicts** - No more "port already in use" errors
- **✅ Cross-Platform Support** - Works on Windows, Linux, and macOS
- **✅ Docker Integration** - Manages Docker container ports seamlessly
- **✅ Framework Integration** - Resolves conflicts between framework agents
- **✅ Thread-Safe** - Safe for use in multi-threaded applications
- **✅ Easy to Use** - Simple API for common port management tasks

### **Next Steps**

1. **Integrate with Existing Agents** - Update framework agents to use the Port Management Agent
2. **Add to Startup Process** - Include port conflict resolution in framework startup
3. **Create CLI Tools** - Add command-line tools for port management
4. **Add Monitoring** - Monitor port usage and provide alerts for conflicts

The Port Management Agent is now ready for use in the NIR_Mistral Framework! 🎉