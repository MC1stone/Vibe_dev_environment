# 🚀 Starting Django Server with Port Management Agent

## 📋 Overview

This guide explains how to start the Django server with the **Port Management Agent** integration. The Port Management Agent provides automatic port conflict resolution, REST API endpoints, and management commands for port management.

## ✅ **What's Been Implemented**

### **1. Django App: `port_manager`**
- **Middleware**: `PortConflictMiddleware` and `PortConflictResolutionMiddleware`
- **API Views**: Comprehensive REST API endpoints at `/api/ports/`
- **Management Commands**: `check_ports` and `reserve_port` commands
- **URL Routing**: Full URL configuration integrated with main project

### **2. Django Settings Integration**
- Added `port_manager` to `INSTALLED_APPS`
- Added `PortConflictResolutionMiddleware` to `MIDDLEWARE`
- Added port manager URLs to main `urls.py`

### **3. Port Management Features**
- ✅ Thread-safe port reservation system
- ✅ Cross-platform port scanning (Windows/Linux/Mac)
- ✅ Docker-specific port management
- ✅ Framework port conflict detection and resolution
- ✅ Comprehensive error handling
- ✅ REST API endpoints
- ✅ Django management commands

## 🚀 **Starting the Server**

### **Option 1: Using the Start Script (Recommended)**

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
./start_server.sh
```

This will:
1. Kill any existing Django server processes
2. Activate the virtual environment
3. Start the server on port 8000
4. Initialize the Port Management Agent automatically

### **Option 2: Manual Start**

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
python manage.py runserver 0.0.0.0:8000
```

### **Option 3: Different Port**

If port 8000 is in use:

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
python manage.py runserver 0.0.0.0:8001
```

## 🔍 **Verifying Port Management Agent Initialization**

When the server starts, you should see:

```
✓ Port Management Agent initialized and ready
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
August 03, 2026 - 15:30:00
Django version 6.0.7, using settings 'nir_web.settings'
Starting development server at http://0.0.0.0:8000/
Quit the server with CONTROL-C.
```

The key line is: **`✓ Port Management Agent initialized and ready`**

## 🧪 **Testing the Integration**

### **1. Check Server Health**

```bash
curl http://localhost:8000/api/health/
```

### **2. Test Port Management API**

#### **Get Port Management Overview**
```bash
curl http://localhost:8000/api/ports/
```

Expected response:
```json
{
    "success": true,
    "docker_available": false,
    "system_ports_count": 35,
    "reserved_ports_count": 0,
    "docker_ports_count": 0,
    "has_conflicts": true,
    "conflict_count": 1,
    "message": "Port Management Agent is running"
}
```

#### **Get Detailed Port Status**
```bash
curl http://localhost:8000/api/ports/status/
```

#### **Check Specific Port Availability**
```bash
curl http://localhost:8000/api/ports/check/8080/
```

Expected response:
```json
{
    "port": 8080,
    "host": "127.0.0.1",
    "available": false,
    "conflicts": ["system:8080"]
}
```

#### **Scan Ports in a Range**
```bash
curl "http://localhost:8000/api/ports/scan/?start=9000&end=9100"
```

#### **Reserve a Port (POST)**
```bash
curl -X POST http://localhost:8000/api/ports/reserve/ \
  -H "Content-Type: application/json" \
  -d '{"service_name": "my_service", "start": 9000, "end": 9100}'
```

Expected response:
```json
{
    "success": true,
    "port": 9000,
    "host": "127.0.0.1",
    "service_name": "my_service",
    "message": "Port 9000 assigned and reserved"
}
```

### **3. Use Django Management Commands**

#### **Check Port Usage and Conflicts**
```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
python manage.py check_ports
```

#### **Auto-Resolve Conflicts**
```bash
python manage.py check_ports --resolve
```

#### **JSON Output**
```bash
python manage.py check_ports --json
```

#### **Scan Specific Port Range**
```bash
python manage.py check_ports --scan --range 8000-9000
```

#### **Reserve Port for Agent**
```bash
python manage.py reserve_port django_agent
```

#### **List All Reserved Ports**
```bash
python manage.py reserve_port --list
```

#### **Release a Reserved Port**
```bash
python manage.py reserve_port --release django_agent
```

## 🎯 **Using the Middleware**

The `PortConflictResolutionMiddleware` automatically:

1. **Initializes** the Port Management Agent when Django starts
2. **Detects** port conflicts in the framework configuration
3. **Resolves** conflicts by assigning new ports automatically
4. **Logs** all port changes for debugging

### **Example Output on Startup**
```
✓ Port Management: System initialized and conflicts resolved
  Updated django_agent port to 8048
  Updated weaviate_agent port to 8081
```

## 🤖 **CrewAI Integration**

### **Using Port Management with CrewAI Agents**

```python
from agents.port_agent.crewai_integration import (
    PortManagerCrewAIAgent,
    check_ports,
    resolve_conflicts,
    reserve_port,
    get_port_status
)

# Simple usage
result = check_ports()
print(f"Port check: {result['success']}")

# Reserve a port
result = reserve_port(service_name='my_crewai_service')
print(f"Reserved port: {result['port']}")

# Get comprehensive status
result = get_port_status()
print(f"Status: {result['success']}")
```

### **Using as a CrewAI Tool**

```python
from crewai import Agent, Task, Crew
from agents.port_agent import port_management_tool

# Create an agent with port management
port_manager_agent = Agent(
    role='DevOps Port Manager',
    goal='Manage ports and prevent conflicts',
    backstory='You are an expert in port management for the NIR_Mistral Framework',
    tools=[port_management_tool],
    verbose=True
)

# Create a task
task = Task(
    description='Find and reserve a port for my Django service in range 8000-9000',
    expected_output='The assigned port number',
    agent=port_manager_agent
)

# Execute
crew = Crew(agents=[port_manager_agent], tasks=[task])
result = crew.kickoff()
print(f"Assigned port: {result}")
```

## 📊 **API Endpoints Reference**

### **GET Endpoints**

| Endpoint | Description | Parameters |
|----------|-------------|------------|
| `/api/ports/` | Overview of port management status | None |
| `/api/ports/status/` | Detailed port status report | None |
| `/api/ports/conflicts/` | Get port conflicts | None |
| `/api/ports/scan/` | Scan ports in a range | `start`, `end`, `host` |
| `/api/ports/check/<port>/` | Check specific port availability | `host` |
| `/api/ports/agents/` | Get port info for all agents | None |

### **POST Endpoints**

| Endpoint | Description | Required Parameters |
|----------|-------------|-------------------|
| `/api/ports/reserve/` | Reserve a port | `service_name`, `port` or `start`/`end` |
| `/api/ports/release/` | Release a reserved port | `port` |
| `/api/ports/assign/` | Assign a free port | `start`, `end`, `service_name` |
| `/api/ports/resolve/` | Resolve port conflicts | `auto_assign` (optional) |

## 🛠️ **Troubleshooting**

### **Issue: Server fails to start**

**Possible Cause**: Missing `yaml` module

**Solution**: Install the missing dependency
```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
pip install pyyaml
```

### **Issue: Port already in use**

**Solution**: Use a different port
```bash
python manage.py runserver 0.0.0.0:8001
```

### **Issue: Port Management Agent not initializing**

**Solution**: Check the server logs for errors and ensure the `port_manager` app is in `INSTALLED_APPS`

### **Issue: API endpoints not working**

**Solution**: Verify the server is running and check the URL configuration
```bash
# Check if server is running
curl http://localhost:8000/api/health/

# Check URL configuration
python manage.py show_urls | grep ports
```

## 📝 **Configuration**

### **Django Settings**

Ensure these are in your `settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    'port_manager',
]

MIDDLEWARE = [
    # ... other middleware
    'port_manager.middleware.PortConflictResolutionMiddleware',
]
```

### **URL Configuration**

Ensure this is in your `urls.py`:

```python
urlpatterns = [
    # ... other URLs
    path('api/ports/', include('port_manager.urls')),
]
```

## 🎉 **Success Indicators**

When everything is working correctly, you should see:

1. **Server startup**: `✓ Port Management Agent initialized and ready`
2. **API response**: JSON responses from `/api/ports/` endpoints
3. **Management commands**: Successful output from `check_ports` and `reserve_port` commands
4. **Middleware**: Automatic port conflict resolution on server startup

## 📚 **Next Steps**

1. **Test the API endpoints** using `curl` or Postman
2. **Run management commands** to check and resolve port conflicts
3. **Integrate with your agents** using the CrewAI tools
4. **Monitor port usage** through the API or management commands
5. **Customize port ranges** in the configuration as needed

## 🔗 **Related Files**

- `django_project/port_manager/` - Port Management Django app
- `agents/port_agent/` - Core Port Management Agent
- `django_project/nir_web/settings.py` - Django settings with port_manager
- `django_project/nir_web/urls.py` - URL configuration with port_manager

## 🏁 **Conclusion**

The **Port Management Agent** is now fully integrated with your Django server! 🎉

**Key Benefits:**
- ✅ Automatic port conflict resolution
- ✅ REST API for port management
- ✅ Django management commands
- ✅ CrewAI integration
- ✅ Cross-platform support
- ✅ Thread-safe operations

**Start your server and enjoy conflict-free port management!**

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
./start_server.sh
```