# Agent Framework - Usage Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Basic Usage](#basic-usage)
5. [Agent Management](#agent-management)
6. [Project Execution](#project-execution)
7. [Advanced Features](#advanced-features)
8. [Examples](#examples)
9. [Troubleshooting](#troubleshooting)
10. [API Reference](#api-reference)

## Getting Started

The Agent Framework is a comprehensive multi-agent system for collaborative software development. This guide will walk you through setting up and using the framework.

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Basic understanding of software development concepts

### Quick Start

```python
from framework.main import MultiAgentFramework
import asyncio

async def main():
    # Create framework instance
    framework = MultiAgentFramework()
    
    # Initialize team with default configuration
    await framework.initialize_team()
    
    # Create a project
    project_spec = {
        "name": "My First Project",
        "description": "A simple project to test the framework",
        "requirements": {
            "backend": {"api": True, "database": True},
            "frontend": {"ui_design": True, "components": True}
        }
    }
    
    project = await framework.create_project(project_spec)
    print(f"Project created: {project['project_id']}")
    
    # Execute the project
    result = await framework.execute_project(project['project_id'])
    print(f"Project status: {result['status']}")
    
    # Get team status
    status = await framework.get_team_status()
    print(f"Team has {status['agents']['total']} agents")
    
    # Shutdown framework
    await framework.shutdown()

asyncio.run(main())
```

## Installation

### Install from Source

```bash
# Clone the repository
git clone https://github.com/MC1stone/Vibe_dev_environment.git
cd Vibe_dev_environment/framework

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install framework in development mode
pip install -e .
```

### Install Dependencies

The framework requires the following dependencies:

```bash
pip install pyyaml dataclasses typing-extensions numpy pandas scikit-learn faiss-cpu
```

For additional features:

```bash
# For PostgreSQL support
pip install psycopg2-binary sqlalchemy

# For n8n integration
pip install requests

# For MCP integration
pip install mcp

# For CrewAI integration
pip install crewai
```

## Configuration

### Team Configuration

The framework uses YAML files for configuration. Here's an example `team_configs.yaml`:

```yaml
# Team metadata
team:
  name: "Software Development Team"
  description: "Multi-agent team for comprehensive software development"
  version: "1.0.0"

# Orchestrator configuration
orchestrator:
  max_concurrent_projects: 5
  max_agents_per_project: 10
  task_timeout: 3600  # 1 hour
  project_timeout: 86400  # 24 hours
  retry_attempts: 3
  load_balancing: "workload_based"

# Agent configurations
agents:
  - agent_id: "backend_agent_001"
    agent_type: "specialist"
    name: "Backend Specialist"
    description: "Expert in backend development"
    capabilities: ["backend", "api", "database"]
    skills: ["api_design", "authentication", "database_integration"]
    module: "framework.agents.specialists.backend_agent.BackendAgent"
    
  - agent_id: "frontend_agent_001"
    agent_type: "specialist"
    name: "Frontend Specialist"
    description: "Expert in frontend development"
    capabilities: ["frontend", "ui", "javascript"]
    skills: ["ui_design", "responsive_design", "state_management"]
    module: "framework.agents.specialists.frontend_agent.FrontendAgent"

# Project templates
project_templates:
  full_stack_application:
    name: "Full Stack Application"
    description: "Complete application with backend and frontend"
    requirements:
      backend:
        api: true
        database: true
        implementation: true
      frontend:
        ui_design: true
        components: true
        pages: true
```

### Loading Configuration

```python
from framework.main import MultiAgentFramework

# Create framework with custom configuration
framework = MultiAgentFramework(config_path="path/to/team_configs.yaml")

# Or initialize with configuration later
framework = MultiAgentFramework()
framework.load_config("path/to/team_configs.yaml")
```

## Basic Usage

### Creating a Framework Instance

```python
from framework.main import MultiAgentFramework

# Create framework with default configuration
framework = MultiAgentFramework()

# Create framework with custom configuration
framework = MultiAgentFramework(config_path="configs/team_configs.yaml")
```

### Initializing the Team

```python
import asyncio

async def initialize():
    framework = MultiAgentFramework()
    
    # Initialize with default configuration
    result = await framework.initialize_team()
    print(f"Team initialized: {result['status']}")
    
    # Or initialize with custom configuration
    custom_config = {
        "agents": [
            {
                "agent_id": "test_agent",
                "name": "Test Agent",
                "capabilities": ["testing"],
                "skills": ["test_execution"],
                "module": "framework.agents.quality.testing_agent.TestingAgent"
            }
        ]
    }
    result = await framework.initialize_team(custom_config)

asyncio.run(initialize())
```

### Creating a Project

```python
import asyncio

async def create_project():
    framework = MultiAgentFramework()
    await framework.initialize_team()
    
    # Simple project
    project_spec = {
        "name": "Simple Project",
        "description": "A basic project to test the framework"
    }
    
    # Full project with requirements
    project_spec = {
        "name": "Full Stack Application",
        "description": "Complete application with backend and frontend",
        "requirements": {
            "backend": {
                "api": True,
                "database": True,
                "implementation": True,
                "testing": True
            },
            "frontend": {
                "ui_design": True,
                "components": True,
                "pages": True,
                "testing": True
            },
            "data_analysis": {
                "data_loading": True,
                "eda": True
            },
            "tools": ["postgresql", "faiss"]
        }
    }
    
    project = await framework.create_project(project_spec)
    print(f"Project created: {project['project_id']}")
    return project['project_id']

asyncio.run(create_project())
```

### Executing a Project

```python
import asyncio

async def execute_project():
    framework = MultiAgentFramework()
    await framework.initialize_team()
    
    # Create a project
    project_spec = {
        "name": "Test Project",
        "description": "Testing the framework",
        "requirements": {
            "backend": {"api": True},
            "frontend": {"ui_design": True}
        }
    }
    
    project = await framework.create_project(project_spec)
    project_id = project['project_id']
    
    # Execute the project
    execution_spec = {
        "priority": "high",
        "timeout": 3600,
        "documentation": True,
        "quality_assurance": True
    }
    
    result = await framework.execute_project(project_id, execution_spec)
    print(f"Project status: {result['status']}")
    print(f"Results: {result['results']}")
    
    return result

asyncio.run(execute_project())
```

### Monitoring a Project

```python
import asyncio

async def monitor_project():
    framework = MultiAgentFramework()
    await framework.initialize_team()
    
    # Create and execute a project
    project_spec = {
        "name": "Monitored Project",
        "description": "Project to monitor",
        "requirements": {"backend": {"api": True}}
    }
    
    project = await framework.create_project(project_spec)
    project_id = project['project_id']
    
    # Execute project in background
    execution_task = asyncio.create_task(
        framework.execute_project(project_id)
    )
    
    # Monitor project while it's executing
    for i in range(5):  # Monitor 5 times
        status = await framework.monitor_project(project_id)
        print(f"Progress: {status['progress']:.1f}%")
        print(f"Completed tasks: {status['completed_tasks']}/{status['total_tasks']}")
        await asyncio.sleep(2)  # Wait 2 seconds
    
    # Wait for execution to complete
    result = await execution_task
    print(f"Final status: {result['status']}")

asyncio.run(monitor_project())
```

### Getting Team Status

```python
import asyncio

async def get_status():
    framework = MultiAgentFramework()
    await framework.initialize_team()
    
    # Get overall team status
    status = await framework.get_team_status()
    
    print(f"Team status: {status['status']}")
    print(f"Total agents: {status['agents']['total']}")
    print(f"Available agents: {status['agents']['available']}")
    print(f"Busy agents: {status['agents']['busy']}")
    print(f"Total projects: {status['projects']['total']}")
    print(f"Total tasks: {status['tasks']['total']}")
    
    # List all agents
    print("\nAgents:")
    for agent_id, agent_info in status['agents']['details'].items():
        print(f"  - {agent_info['name']} ({agent_id}): {agent_info['status']}")

asyncio.run(get_status())
```

## Agent Management

### Accessing Specific Agents

```python
import asyncio

async def access_agents():
    framework = MultiAgentFramework()
    await framework.initialize_team()
    
    # List all registered agents
    agent_ids = framework.list_agents()
    print(f"Registered agents: {agent_ids}")
    
    # Get a specific agent
    backend_agent = framework.get_agent("backend_agent_001")
    if backend_agent:
        print(f"Backend agent: {backend_agent.name}")
        print(f"Description: {backend_agent.description}")
        
        # Use the agent directly
        api_spec = {
            "name": "Test API",
            "description": "A test API",
            "endpoints": [
                {"path": "/users", "method": "GET", "description": "Get all users"},
                {"path": "/users", "method": "POST", "description": "Create a user"}
            ]
        }
        
        api_design = await backend_agent.design_api(api_spec)
        print(f"API designed: {api_design['name']}")

asyncio.run(access_agents())
```

### Using Specialist Agents Directly

```python
import asyncio
from framework.agents.specialists.backend_agent import BackendAgent
from framework.agents.specialists.frontend_agent import FrontendAgent
from framework.agents.specialists.data_analysis_agent import DataAnalysisAgent

async def use_specialists():
    # Create specialist agents directly
    backend_agent = BackendAgent()
    frontend_agent = FrontendAgent()
    data_agent = DataAnalysisAgent()
    
    # Use Backend Agent
    api_spec = {
        "name": "User API",
        "description": "API for user management",
        "endpoints": [
            {"path": "/users", "method": "GET", "description": "List users"},
            {"path": "/users/{id}", "method": "GET", "description": "Get user by ID"}
        ]
    }
    
    api_design = await backend_agent.design_api(api_spec)
    print(f"API designed: {api_design['name']}")
    
    # Use Frontend Agent
    ui_spec = {
        "name": "User Dashboard",
        "description": "Dashboard for user management",
        "components": [
            {"name": "UserList", "type": "component", "description": "List of users"},
            {"name": "UserForm", "type": "component", "description": "Form for user creation"}
        ],
        "pages": [
            {"name": "UsersPage", "path": "/users", "components": ["UserList", "UserForm"]}
        ]
    }
    
    ui_design = await frontend_agent.design_ui(ui_spec)
    print(f"UI designed: {ui_design['name']}")
    
    # Use Data Analysis Agent
    dataset_spec = {
        "name": "user_data",
        "source": "file",
        "format": "csv",
        "columns": [
            {"name": "id", "type": "integer"},
            {"name": "name", "type": "string"},
            {"name": "age", "type": "integer"}
        ]
    }
    
    dataset = await data_agent.load_dataset(dataset_spec)
    print(f"Dataset loaded: {dataset['dataset_name']}")

asyncio.run(use_specialists())
```

## Project Execution

### Using the Convenience Function

```python
import asyncio
from framework.main import run_project

async def simple_execution():
    # Simple project specification
    project_spec = {
        "name": "Quick Test",
        "description": "A quick test of the framework",
        "requirements": {
            "backend": {"api": True},
            "frontend": {"ui_design": True}
        }
    }
    
    # Run project with default configuration
    result = await run_project(project_spec)
    print(f"Project completed with status: {result['status']}")

asyncio.run(simple_execution())
```

### Custom Project Execution

```python
import asyncio
from framework.main import MultiAgentFramework

async def custom_execution():
    framework = MultiAgentFramework()
    await framework.initialize_team()
    
    # Create a complex project
    project_spec = {
        "project_id": "complex_project_001",
        "name": "Complex Application",
        "description": "A complex application with multiple components",
        "requirements": {
            "backend": {
                "api": True,
                "database": True,
                "implementation": True,
                "testing": True,
                "authentication": True
            },
            "frontend": {
                "ui_design": True,
                "components": True,
                "pages": True,
                "testing": True,
                "responsive_design": True
            },
            "data_analysis": {
                "data_loading": True,
                "eda": True,
                "feature_engineering": True
            },
            "tools": ["postgresql", "faiss", "n8n"]
        }
    }
    
    # Create project
    project = await framework.create_project(project_spec)
    project_id = project['project_id']
    
    # Custom execution specification
    execution_spec = {
        "priority": "high",
        "timeout": 7200,  # 2 hours
        "max_retries": 3,
        "documentation": True,
        "quality_assurance": True,
        "testing": True,
        "parallel_execution": True
    }
    
    # Execute project
    result = await framework.execute_project(project_id, execution_spec)
    
    print(f"Project: {result['name']}")
    print(f"Status: {result['status']}")
    print(f"Tasks executed: {result['tasks_executed']}")
    print(f"Agents involved: {result['agents_involved']}")
    print(f"Results: {result['results']}")
    
    # Check for errors
    if result['errors']:
        print(f"Errors: {result['errors']}")
    
    return result

asyncio.run(custom_execution())
```

## Advanced Features

### Custom Agent Registration

```python
import asyncio
from framework.main import MultiAgentFramework
from framework.agents.specialists.backend_agent import BackendAgent

async def register_custom_agent():
    framework = MultiAgentFramework()
    await framework.initialize_team()
    
    # Create a custom agent configuration
    custom_agent_config = {
        "agent_id": "custom_backend_agent",
        "agent_type": "specialist",
        "name": "Custom Backend Agent",
        "description": "A custom backend agent with specific capabilities",
        "capabilities": ["backend", "api", "custom"],
        "skills": ["api_design", "custom_implementation"],
        "module": "framework.agents.specialists.backend_agent.BackendAgent"
    }
    
    # Register the agent
    result = await framework.orchestrator.register_agent(custom_agent_config)
    print(f"Agent registered: {result['agent_id']}")
    
    # Now the agent is available for task assignment
    project_spec = {
        "name": "Custom Project",
        "requirements": {"backend": {"api": True}}
    }
    
    project = await framework.create_project(project_spec)
    result = await framework.execute_project(project['project_id'])
    print(f"Project executed: {result['status']}")

asyncio.run(register_custom_agent())
```

### Workflow Management

```python
import asyncio
from framework.orchestration.workflow_manager import WorkflowManager

async def manage_workflows():
    # Create workflow manager
    workflow_manager = WorkflowManager()
    await workflow_manager.initialize()
    
    # Define a workflow
    workflow_spec = {
        "workflow_id": "data_processing_workflow",
        "name": "Data Processing Workflow",
        "description": "Workflow for processing and analyzing data",
        "workflow_type": "sequential",
        "tasks": [
            {
                "task_id": "load_data",
                "name": "Load Data",
                "description": "Load data from source",
                "task_type": "data_analysis",
                "priority": 10
            },
            {
                "task_id": "clean_data",
                "name": "Clean Data",
                "description": "Clean and preprocess data",
                "task_type": "data_analysis",
                "priority": 9,
                "dependencies": ["load_data"]
            },
            {
                "task_id": "analyze_data",
                "name": "Analyze Data",
                "description": "Perform data analysis",
                "task_type": "data_analysis",
                "priority": 8,
                "dependencies": ["clean_data"]
            },
            {
                "task_id": "visualize_results",
                "name": "Visualize Results",
                "description": "Create visualizations",
                "task_type": "data_analysis",
                "priority": 7,
                "dependencies": ["analyze_data"]
            }
        ],
        "dependencies": {
            "clean_data": ["load_data"],
            "analyze_data": ["clean_data"],
            "visualize_results": ["analyze_data"]
        }
    }
    
    # Create workflow
    workflow = await workflow_manager.create_workflow(workflow_spec)
    print(f"Workflow created: {workflow['workflow_id']}")
    
    # Execute workflow
    execution_result = await workflow_manager.execute_workflow(workflow['workflow_id'])
    print(f"Workflow status: {execution_result['status']}")
    
    # Monitor workflow
    status = await workflow_manager.get_workflow_status(workflow['workflow_id'])
    print(f"Workflow progress: {status['progress']}")

asyncio.run(manage_workflows())
```

### Task Distribution

```python
import asyncio
from framework.orchestration.task_distributor import TaskDistributor

async def distribute_tasks():
    # Create task distributor
    task_distributor = TaskDistributor()
    
    # Initialize with agents
    agents = {
        "backend_agent": {"capabilities": ["backend"], "workload": 0.0},
        "frontend_agent": {"capabilities": ["frontend"], "workload": 0.0},
        "data_agent": {"capabilities": ["data_analysis"], "workload": 0.0}
    }
    
    await task_distributor.initialize(agents)
    
    # Create tasks
    tasks = [
        {
            "task_id": "task_1",
            "name": "Backend API",
            "task_type": "backend",
            "priority": 8
        },
        {
            "task_id": "task_2",
            "name": "Frontend UI",
            "task_type": "frontend",
            "priority": 7
        },
        {
            "task_id": "task_3",
            "name": "Data Analysis",
            "task_type": "data_analysis",
            "priority": 6
        }
    ]
    
    # Distribute tasks
    distribution = await task_distributor.distribute_tasks(tasks)
    print(f"Tasks distributed: {distribution['assigned']}")
    print(f"Unassigned: {distribution['unassigned']}")
    
    # Check workload balance
    for agent_id, workload_info in distribution['workload_balance'].items():
        print(f"{agent_id}: {workload_info['workload']:.1%} workload")

asyncio.run(distribute_tasks())
```

### Communication Between Agents

```python
import asyncio
from framework.orchestration.communication_bus import CommunicationBus

async def agent_communication():
    # Create communication bus
    bus = CommunicationBus()
    await bus.initialize()
    
    # Register agents
    await bus.register_agent("agent_1", ["backend", "api"])
    await bus.register_agent("agent_2", ["frontend", "ui"])
    
    # Send a message
    message_spec = {
        "sender": "agent_1",
        "receiver": "agent_2",
        "message": "API design completed",
        "data": {
            "api_spec": {
                "name": "User API",
                "endpoints": ["/users", "/users/{id}"]
            }
        }
    }
    
    result = await bus.send_message(message_spec)
    print(f"Message sent: {result['message_id']}")
    
    # Broadcast an event
    event_spec = {
        "sender": "agent_1",
        "event_type": "api_completed",
        "data": {"api_name": "User API"}
    }
    
    result = await bus.broadcast_event(event_spec)
    print(f"Event broadcast: {result['event_id']}")
    
    # Get message history
    history = await bus.get_message_history()
    print(f"Message history: {len(history)} messages")

asyncio.run(agent_communication())
```

## Examples

### Example 1: Simple Project Execution

```python
import asyncio
from framework.main import run_project

async def example_simple_project():
    # Define a simple project
    project_spec = {
        "name": "Simple Web Application",
        "description": "A basic web application with backend and frontend",
        "requirements": {
            "backend": {
                "api": True,
                "database": False,
                "implementation": True
            },
            "frontend": {
                "ui_design": True,
                "components": True
            }
        }
    }
    
    # Execute the project
    result = await run_project(project_spec)
    
    print("Simple Project Execution Results:")
    print(f"  Status: {result['status']}")
    print(f"  Tasks executed: {result['tasks_executed']}")
    print(f"  Agents involved: {result['agents_involved']}")
    print(f"  Progress: {result['results']['progress']}")

asyncio.run(example_simple_project())
```

### Example 2: Data Analysis Project

```python
import asyncio
from framework.main import run_project

async def example_data_project():
    # Define a data analysis project
    project_spec = {
        "name": "Data Analysis Project",
        "description": "Analyze customer data to find insights",
        "requirements": {
            "data_analysis": {
                "data_loading": True,
                "eda": True,
                "feature_engineering": True,
                "model_training": False
            },
            "tools": ["faiss", "postgresql"]
        }
    }
    
    # Execute the project
    result = await run_project(project_spec)
    
    print("Data Analysis Project Results:")
    print(f"  Status: {result['status']}")
    print(f"  Tasks: {result['tasks_executed']}")
    print(f"  Results: {result['results']}")

asyncio.run(example_data_project())
```

### Example 3: Full Stack Application

```python
import asyncio
from framework.main import run_project

async def example_full_stack():
    # Define a full stack application
    project_spec = {
        "name": "Full Stack Application",
        "description": "Complete application with all components",
        "requirements": {
            "backend": {
                "api": True,
                "database": True,
                "implementation": True,
                "testing": True,
                "authentication": True
            },
            "frontend": {
                "ui_design": True,
                "components": True,
                "pages": True,
                "testing": True,
                "responsive_design": True
            },
            "data_analysis": {
                "data_loading": True,
                "eda": True
            },
            "tools": ["postgresql", "faiss", "n8n"]
        }
    }
    
    # Execute the project
    result = await run_project(project_spec)
    
    print("Full Stack Application Results:")
    print(f"  Status: {result['status']}")
    print(f"  Total tasks: {result['tasks_executed']}")
    print(f"  Agents: {len(result['agents_involved'])} involved")
    print(f"  Summary: {result['results']['summary']}")

asyncio.run(example_full_stack())
```

### Example 4: Using Specialist Agents Directly

```python
import asyncio
from framework.agents.specialists.backend_agent import BackendAgent
from framework.agents.specialists.frontend_agent import FrontendAgent
from framework.agents.specialists.data_analysis_agent import DataAnalysisAgent

async def example_specialist_agents():
    # Create specialist agents
    backend_agent = BackendAgent()
    frontend_agent = FrontendAgent()
    data_agent = DataAnalysisAgent()
    
    # Backend Agent: Design an API
    api_spec = {
        "name": "E-commerce API",
        "description": "API for an e-commerce platform",
        "technology": "python_fastapi",
        "endpoints": [
            {
                "path": "/products",
                "method": "GET",
                "description": "Get all products",
                "parameters": {"category": "string", "limit": "integer"}
            },
            {
                "path": "/products/{id}",
                "method": "GET",
                "description": "Get product by ID"
            },
            {
                "path": "/products",
                "method": "POST",
                "description": "Create a new product",
                "authentication": True
            }
        ]
    }
    
    api_design = await backend_agent.design_api(api_spec)
    print(f"API designed: {api_design['name']}")
    print(f"  Technology: {api_design['technology']}")
    print(f"  Endpoints: {len(api_design['endpoints'])}")
    
    # Frontend Agent: Design UI
    ui_spec = {
        "name": "E-commerce UI",
        "description": "User interface for e-commerce platform",
        "technology": "react",
        "framework": "spa",
        "components": [
            {
                "name": "ProductList",
                "type": "component",
                "description": "List of products with filtering",
                "props": {"products": "array", "onSelect": "function"}
            },
            {
                "name": "ProductDetail",
                "type": "component",
                "description": "Detailed view of a product",
                "props": {"product": "object"}
            },
            {
                "name": "ShoppingCart",
                "type": "component",
                "description": "Shopping cart with items",
                "props": {"items": "array", "onCheckout": "function"}
            }
        ],
        "pages": [
            {
                "name": "HomePage",
                "path": "/",
                "components": ["ProductList"],
                "description": "Home page with product listing"
            },
            {
                "name": "ProductPage",
                "path": "/products/{id}",
                "components": ["ProductDetail", "ShoppingCart"],
                "description": "Product detail page"
            }
        ]
    }
    
    ui_design = await frontend_agent.design_ui(ui_spec)
    print(f"\nUI designed: {ui_design['name']}")
    print(f"  Components: {len(ui_design['components'])}")
    print(f"  Pages: {len(ui_design['pages'])}")
    
    # Data Analysis Agent: Load dataset
    dataset_spec = {
        "name": "sales_data",
        "description": "Historical sales data",
        "source": "file",
        "format": "csv",
        "columns": [
            {"name": "date", "type": "date"},
            {"name": "product_id", "type": "string"},
            {"name": "quantity", "type": "integer"},
            {"name": "price", "type": "float"},
            {"name": "customer_id", "type": "string"}
        ]
    }
    
    dataset = await data_agent.load_dataset(dataset_spec)
    print(f"\nDataset loaded: {dataset['dataset_name']}")
    print(f"  Shape: {dataset['shape']}")
    print(f"  Columns: {list(dataset['dtypes'].keys())}")

asyncio.run(example_specialist_agents())
```

## Troubleshooting

### Common Issues

#### 1. Agent Registration Failed

**Symptom**: Agent fails to register with the orchestrator.

**Possible Causes**:
- Module path is incorrect
- Agent class not found in module
- Circular import issues

**Solutions**:
- Verify the module path in the configuration
- Check that the agent class exists and is importable
- Ensure there are no circular imports

```python
# Test agent import
from framework.agents.specialists.backend_agent import BackendAgent
agent = BackendAgent()
print(f"Agent created: {agent.name}")
```

#### 2. Project Execution Hangs

**Symptom**: Project execution starts but never completes.

**Possible Causes**:
- Task timeout is too long
- Agent is stuck or unresponsive
- Circular dependencies between tasks

**Solutions**:
- Reduce task timeout in configuration
- Check agent health and status
- Review task dependencies for circular references

```python
# Check team status
status = await framework.get_team_status()
print(f"Team status: {status['status']}")
print(f"Agents: {status['agents']}")
```

#### 3. No Agents Available for Tasks

**Symptom**: Tasks remain unassigned because no agents are available.

**Possible Causes**:
- No agents registered with required capabilities
- All agents are busy
- Task type doesn't match any agent capabilities

**Solutions**:
- Register agents with the required capabilities
- Check agent workload and availability
- Verify task type matches agent capabilities

```python
# Check available agents
status = await framework.get_team_status()
for agent_id, agent_info in status['agents']['details'].items():
    print(f"{agent_info['name']}: {agent_info['status']}, workload: {agent_info['workload']}")
```

#### 4. Configuration Loading Failed

**Symptom**: Configuration file fails to load.

**Possible Causes**:
- File not found
- Invalid YAML syntax
- Incorrect file path

**Solutions**:
- Verify file exists at the specified path
- Check YAML syntax with a validator
- Use absolute paths for configuration files

```python
# Test configuration loading
import yaml
try:
    with open("configs/team_configs.yaml", 'r') as f:
        config = yaml.safe_load(f)
    print("Configuration loaded successfully")
except Exception as e:
    print(f"Error loading configuration: {e}")
```

### Debugging

#### Enable Debug Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or configure in the team configuration
team_config = {
    "orchestrator": {
        "logging": {
            "level": "debug",
            "console": True
        }
    }
}
```

#### Inspect Team State

```python
# Get detailed team status
status = await framework.get_team_status()
print(json.dumps(status, indent=2))
```

#### Monitor Project Progress

```python
# Monitor project during execution
for i in range(10):
    status = await framework.monitor_project(project_id)
    print(f"Progress: {status['progress']:.1f}%")
    print(f"Status: {status['status']}")
    await asyncio.sleep(1)
```

### Error Handling

#### Retry Failed Tasks

```python
# Configure retry in execution specification
execution_spec = {
    "retry_attempts": 3,
    "auto_retry": True,
    "retry_delay": 5  # seconds between retries
}

result = await framework.execute_project(project_id, execution_spec)
```

#### Manual Task Assignment

```python
# Manually assign a task to a specific agent
task_spec = {
    "task_id": "manual_task",
    "name": "Manual Task",
    "description": "Task to be assigned manually",
    "assigned_to": "backend_agent_001",  # Specific agent ID
    "priority": 10
}

# Add task to project requirements
project_spec = {
    "name": "Manual Project",
    "requirements": {
        "custom_tasks": [task_spec]
    }
}
```

## API Reference

### MultiAgentFramework Class

#### Methods

- `__init__(config_path: Optional[str] = None)`: Initialize the framework
- `load_config(config_path: str) -> Dict[str, Any]`: Load configuration from file
- `initialize_team(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`: Initialize the team
- `create_project(project_spec: Dict[str, Any]) -> Dict[str, Any]`: Create a new project
- `execute_project(project_id: str, execution_spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`: Execute a project
- `monitor_project(project_id: str) -> Dict[str, Any]`: Monitor project status
- `get_team_status() -> Dict[str, Any]`: Get current team status
- `shutdown() -> Dict[str, Any]`: Shutdown the framework
- `get_agent(agent_id: str) -> Optional[Any]`: Get a specific agent
- `list_agents() -> List[str]`: List all agent IDs
- `list_projects() -> List[str]`: List all project IDs

### Convenience Functions

- `create_framework(config_path: Optional[str] = None) -> MultiAgentFramework`: Create a framework instance
- `run_project(project_spec: Dict[str, Any], config_path: Optional[str] = None) -> Dict[str, Any]`: Create framework, run project, and shutdown

### Agent Classes

All agent classes follow a similar pattern:

#### Methods

- `__init__()`: Initialize the agent
- `get_status() -> Dict[str, Any]`: Get current agent status
- `reset()`: Reset agent state

#### Specialist Agent Methods

Each specialist agent has domain-specific methods. For example:

**BackendAgent**:
- `design_api(api_spec: Dict[str, Any]) -> Dict[str, Any]`
- `implement_endpoint(endpoint_spec: Dict[str, Any]) -> Dict[str, Any]`
- `design_database_schema(schema_spec: Dict[str, Any]) -> Dict[str, Any]`
- `optimize_performance(analysis: Dict[str, Any]) -> Dict[str, Any]`
- `generate_documentation(api_spec: Dict[str, Any]) -> Dict[str, Any]`

**FrontendAgent**:
- `design_ui(requirements: Dict[str, Any]) -> Dict[str, Any]`
- `implement_component(component_spec: Dict[str, Any]) -> Dict[str, Any]`
- `design_page(page_spec: Dict[str, Any]) -> Dict[str, Any]`
- `optimize_performance(analysis: Dict[str, Any]) -> Dict[str, Any]`
- `ensure_accessibility(audit: Dict[str, Any]) -> Dict[str, Any]`

**DataAnalysisAgent**:
- `load_dataset(dataset_spec: Dict[str, Any]) -> Dict[str, Any]`
- `perform_eda(dataset_name: str, analysis_spec: Dict[str, Any]) -> Dict[str, Any]`
- `clean_data(dataset_name: str, cleaning_spec: Dict[str, Any]) -> Dict[str, Any]`
- `perform_feature_engineering(dataset_name: str, feature_spec: Dict[str, Any]) -> Dict[str, Any]`
- `train_ml_model(dataset_name: str, model_spec: Dict[str, Any]) -> Dict[str, Any]`

### Orchestration Classes

#### TeamOrchestrator

- `initialize_team(team_config: Dict[str, Any]) -> Dict[str, Any]`
- `register_agent(agent_config: Dict[str, Any]) -> Dict[str, Any]`
- `unregister_agent(agent_id: str) -> Dict[str, Any]`
- `create_project(project_spec: Dict[str, Any]) -> Dict[str, Any]`
- `execute_project(project_id: str, execution_spec: Dict[str, Any]) -> Dict[str, Any]`
- `monitor_project(project_id: str) -> Dict[str, Any]`
- `get_team_status() -> Dict[str, Any]`
- `shutdown() -> Dict[str, Any]`

#### TaskDistributor

- `initialize(agents: Dict[str, Any]) -> Dict[str, Any]`
- `distribute_tasks(tasks: List[Dict[str, Any]]) -> Dict[str, Any]`
- `balance_workload() -> Dict[str, Any]`
- `get_status() -> Dict[str, Any]`

#### CommunicationBus

- `initialize() -> Dict[str, Any]`
- `register_agent(agent_id: str, capabilities: List[str]) -> Dict[str, Any]`
- `send_message(message_spec: Dict[str, Any]) -> Dict[str, Any]`
- `broadcast_event(event_spec: Dict[str, Any]) -> Dict[str, Any]`
- `get_message_history() -> List[Dict[str, Any]]`
- `shutdown() -> Dict[str, Any]`

#### WorkflowManager

- `initialize() -> Dict[str, Any]`
- `create_workflow(workflow_spec: Dict[str, Any]) -> Dict[str, Any]`
- `execute_workflow(workflow_id: str) -> Dict[str, Any]`
- `get_workflow_status(workflow_id: str) -> Dict[str, Any]`
- `shutdown() -> Dict[str, Any]`

## Configuration Reference

### Team Configuration

```yaml
team:
  name: "Team Name"
  description: "Team description"
  version: "1.0.0"
```

### Orchestrator Configuration

```yaml
orchestrator:
  max_concurrent_projects: 5
  max_agents_per_project: 10
  task_timeout: 3600
  project_timeout: 86400
  retry_attempts: 3
  auto_retry: true
  load_balancing: "workload_based"
  
  logging:
    level: "info"
    file: "orchestrator.log"
    console: true
```

### Agent Configuration

```yaml
agents:
  - agent_id: "agent_001"
    agent_type: "specialist"
    name: "Agent Name"
    description: "Agent description"
    capabilities: ["capability1", "capability2"]
    skills: ["skill1", "skill2"]
    module: "framework.agents.specialists.backend_agent.BackendAgent"
```

### Project Templates

```yaml
project_templates:
  template_name:
    name: "Template Name"
    description: "Template description"
    requirements:
      backend:
        api: true
        database: true
      frontend:
        ui_design: true
      tools: ["tool1", "tool2"]
```

## Best Practices

### Project Design

1. **Modular Tasks**: Break projects into small, focused tasks
2. **Clear Dependencies**: Clearly define task dependencies
3. **Appropriate Priorities**: Set priorities based on business value
4. **Realistic Estimates**: Provide realistic time estimates for tasks
5. **Comprehensive Requirements**: Define clear, specific requirements

### Agent Management

1. **Specialized Agents**: Use specialized agents for specific domains
2. **Capability Matching**: Ensure tasks match agent capabilities
3. **Workload Balancing**: Monitor and balance agent workload
4. **Health Monitoring**: Regularly check agent health and status
5. **Error Handling**: Implement robust error handling in agents

### Performance Optimization

1. **Parallel Execution**: Execute independent tasks in parallel
2. **Caching**: Cache frequent operations and results
3. **Batch Processing**: Process data in batches where possible
4. **Resource Allocation**: Allocate appropriate resources to tasks
5. **Monitoring**: Continuously monitor performance metrics

### Quality Assurance

1. **Quality Standards**: Define and enforce quality standards
2. **Automated Testing**: Implement automated testing for all code
3. **Code Reviews**: Conduct thorough code reviews
4. **Continuous Monitoring**: Continuously monitor quality metrics
5. **Continuous Improvement**: Regularly review and improve processes

## Support

For issues, questions, or contributions:

- **GitHub Repository**: [MC1stone/Vibe_dev_environment](https://github.com/MC1stone/Vibe_dev_environment)
- **Documentation**: [Framework Documentation](https://github.com/MC1stone/Vibe_dev_environment/tree/main/framework/docs)
- **Issues**: [GitHub Issues](https://github.com/MC1stone/Vibe_dev_environment/issues)

## License

This framework is provided under the MIT License. See the LICENSE file for details.
