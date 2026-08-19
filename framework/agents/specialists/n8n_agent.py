"""
n8n Agent - Specialist for n8n Workflow Automation

Responsibilities:
- Workflow design and development
- Node configuration
- Integration setup
- Automation scripting
- Error handling
- Performance optimization
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio


class N8NComponent(Enum):
    """n8n component types"""
    WORKFLOW = "workflow"
    NODE = "node"
    CONNECTION = "connection"
    CREDENTIAL = "credential"
    VARIABLE = "variable"
    EXPRESSION = "expression"


class N8NNodeType(Enum):
    """n8n node types"""
    TRIGGER = "trigger"
    ACTION = "action"
    PROCESSING = "processing"
    CONDITION = "condition"
    LOOP = "loop"
    SWITCH = "switch"
    MERGE = "merge"
    SPLIT = "split"
    WAIT = "wait"
    SET = "set"
    FUNCTION = "function"
    HTTP_REQUEST = "httpRequest"
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"


class N8NTriggerType(Enum):
    """n8n trigger types"""
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"
    MANUAL = "manual"
    EXTERNAL = "external"


@dataclass
class N8NNode:
    """Represents an n8n workflow node"""
    node_id: str
    name: str
    type: N8NNodeType
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0})
    parameters: Dict[str, Any] = field(default_factory=dict)
    credentials: Optional[str] = None
    continue_on_fail: bool = False
    disabled: bool = False


@dataclass
class N8NConnection:
    """Represents a connection between n8n nodes"""
    source_node: str
    source_port: int = 0
    target_node: str
    target_port: int = 0


@dataclass
class N8NWorkflow:
    """Represents an n8n workflow"""
    workflow_id: str
    name: str
    description: str = ""
    active: bool = True
    nodes: Dict[str, N8NNode] = field(default_factory=dict)
    connections: List[N8NConnection] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class N8NCredential:
    """Represents an n8n credential"""
    credential_id: str
    name: str
    type: str  # "apiKey", "oauth2", "basicAuth", etc.
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class N8NAgent:
    """
    n8n Specialist Agent
    
    This agent specializes in n8n workflow automation, node configuration, and integration setup.
    It can design and implement complex automation workflows.
    """
    
    agent_id: str = "n8n_agent_001"
    name: str = "n8n Specialist"
    description: str = "Expert in n8n workflow automation and integration"
    version: str = "1.0.0"
    
    # Agent capabilities
    supported_node_types: List[N8NNodeType] = field(default_factory=lambda: [
        N8NNodeType.TRIGGER,
        N8NNodeType.ACTION,
        N8NNodeType.PROCESSING,
        N8NNodeType.CONDITION,
        N8NNodeType.HTTP_REQUEST,
        N8NNodeType.WEBHOOK,
        N8NNodeType.SCHEDULE,
        N8NNodeType.FUNCTION,
        N8NNodeType.SET,
        N8NNodeType.WAIT,
    ])
    
    supported_trigger_types: List[N8NTriggerType] = field(default_factory=lambda: [
        N8NTriggerType.WEBHOOK,
        N8NTriggerType.SCHEDULE,
        N8NTriggerType.MANUAL,
    ])
    
    # Agent skills
    skills: Dict[str, str] = field(default_factory=dict)
    
    # Current project state
    current_project: Optional[str] = None
    current_workflow: Optional[str] = None
    
    # Workflows being developed
    workflows: Dict[str, N8NWorkflow] = field(default_factory=dict)
    
    # Credentials
    credentials: Dict[str, N8NCredential] = field(default_factory=dict)
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the agent with default skills"""
        self._initialize_skills()
    
    def _initialize_skills(self) -> None:
        """Initialize the agent's skill set"""
        self.skills = {
            "workflow_design": "Design complex workflows with proper error handling and branching",
            "node_configuration": "Configure n8n nodes with correct parameters and credentials",
            "integration_setup": "Set up integrations with external APIs and services",
            "automation_scripting": "Write JavaScript code for custom processing and logic",
            "error_handling": "Implement robust error handling and retry mechanisms",
            "performance_optimization": "Optimize workflow performance and resource usage",
            "data_transformation": "Transform and manipulate data between nodes",
            "conditional_logic": "Implement complex conditional logic and branching",
            "scheduling": "Configure workflow scheduling and triggers",
            "testing": "Test workflows and validate their functionality",
            "documentation": "Document workflows and their components",
            "deployment": "Deploy workflows to production environments"
        }
    
    async def create_workflow(self, workflow_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new n8n workflow
        
        Args:
            workflow_spec: Workflow specification
            
        Returns:
            Dictionary with workflow configuration
        """
        print(f"🚀 {self.name}: Creating workflow {workflow_spec.get('name', 'Unnamed')}")
        
        workflow_id = workflow_spec.get("workflow_id", f"workflow_{len(self.workflows) + 1}")
        workflow_name = workflow_spec.get("name", "Unnamed Workflow")
        description = workflow_spec.get("description", "")
        active = workflow_spec.get("active", True)
        
        # Create workflow
        workflow = N8NWorkflow(
            workflow_id=workflow_id,
            name=workflow_name,
            description=description,
            active=active,
            settings=workflow_spec.get("settings", {}),
            variables=workflow_spec.get("variables", {})
        )
        
        self.workflows[workflow_id] = workflow
        self.current_workflow = workflow_id
        
        # Generate workflow JSON
        workflow_json = self._generate_workflow_json(workflow)
        
        result = {
            "workflow_id": workflow_id,
            "name": workflow_name,
            "description": description,
            "active": active,
            "nodes": [],
            "connections": [],
            "json": workflow_json,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Workflow {workflow_name} created with ID {workflow_id}")
        return result
    
    def _generate_workflow_json(self, workflow: N8NWorkflow) -> str:
        """Generate n8n workflow JSON"""
        workflow_dict = {
            "name": workflow.name,
            "description": workflow.description,
            "active": workflow.active,
            "settings": workflow.settings,
            "variables": workflow.variables,
            "nodes": [],
            "connections": {}
        }
        
        # Add nodes
        for node_id, node in workflow.nodes.items():
            node_dict = {
                "parameters": node.parameters,
                "id": node.node_id,
                "name": node.name,
                "type": node.type.value,
                "typeVersion": 1,
                "position": node.position,
                "credentials": node.credentials,
                "continueOnFail": node.continue_on_fail,
                "disabled": node.disabled
            }
            workflow_dict["nodes"].append(node_dict)
        
        # Add connections
        for conn in workflow.connections:
            conn_key = f"{conn.source_node}::{conn.source_port}"
            if conn_key not in workflow_dict["connections"]:
                workflow_dict["connections"][conn_key] = []
            workflow_dict["connections"][conn_key].append({
                "node": conn.target_node,
                "type": "main",
                "index": conn.target_port
            })
        
        return json.dumps(workflow_dict, indent=2)
    
    async def add_node(self, workflow_id: str, node_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a node to a workflow
        
        Args:
            workflow_id: ID of the workflow
            node_spec: Node specification
            
        Returns:
            Dictionary with node configuration
        """
        print(f"🔧 {self.name}: Adding node to workflow {workflow_id}")
        
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        
        node_id = node_spec.get("node_id", f"node_{len(workflow.nodes) + 1}")
        node_name = node_spec.get("name", "Unnamed Node")
        node_type_str = node_spec.get("type", "function")
        
        # Validate node type
        try:
            node_type = N8NNodeType(node_type_str)
        except ValueError:
            node_type = N8NNodeType.FUNCTION
            print(f"⚠️  Node type {node_type_str} not supported, defaulting to Function")
        
        position = node_spec.get("position", {"x": 0, "y": 0})
        parameters = node_spec.get("parameters", {})
        credentials = node_spec.get("credentials")
        continue_on_fail = node_spec.get("continue_on_fail", False)
        disabled = node_spec.get("disabled", False)
        
        # Create node
        node = N8NNode(
            node_id=node_id,
            name=node_name,
            type=node_type,
            position=position,
            parameters=parameters,
            credentials=credentials,
            continue_on_fail=continue_on_fail,
            disabled=disabled
        )
        
        workflow.nodes[node_id] = node
        
        # Generate node code
        node_code = self._generate_node_code(node)
        
        result = {
            "workflow_id": workflow_id,
            "node_id": node_id,
            "name": node_name,
            "type": node_type.value,
            "position": position,
            "parameters": parameters,
            "code": node_code,
            "status": "added"
        }
        
        print(f"✅ {self.name}: Node {node_name} ({node_type.value}) added to workflow {workflow_id}")
        return result
    
    def _generate_node_code(self, node: N8NNode) -> str:
        """Generate node implementation code"""
        if node.type == N8NNodeType.HTTP_REQUEST:
            code = f'''
// HTTP Request Node: {node.name}
// Node ID: {node.node_id}

// Node parameters
const parameters = {json.dumps(node.parameters, indent=2)};

// Example HTTP Request node configuration
{{
    "parameters": {{
        "method": "GET",
        "url": "https://api.example.com/data",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "headers": {{
            "Content-Type": "application/json"
        }},
        "body": {{}},
        "options": {{
            "timeout": 30000,
            "followRedirect": true
        }}
    }},
    "id": "{node.node_id}",
    "name": "{node.name}",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.1,
    "position": {json.dumps(node.position)}
}}
'''
        elif node.type == N8NNodeType.WEBHOOK:
            code = f'''
// Webhook Node: {node.name}
// Node ID: {node.node_id}

// Node parameters
const parameters = {json.dumps(node.parameters, indent=2)};

// Example Webhook node configuration
{{
    "parameters": {{
        "httpMethod": "POST",
        "path": "{node.name.lower().replace(' ', '_')}",
        "responseMode": "responseNode",
        "options": {{
            "noResponseBody": false,
            "responseCode": 200,
            "responseData": ""
        }}
    }},
    "id": "{node.node_id}",
    "name": "{node.name}",
    "type": "n8n-nodes-base.webhook",
    "typeVersion": 2,
    "position": {json.dumps(node.position)},
    "webhookId": "{node.node_id}"
}}
'''
        elif node.type == N8NNodeType.SCHEDULE:
            code = f'''
// Schedule Trigger Node: {node.name}
// Node ID: {node.node_id}

// Node parameters
const parameters = {json.dumps(node.parameters, indent=2)};

// Example Schedule node configuration
{{
    "parameters": {{
        "triggerTimes": {{
            "item": [
                {{
                    "mode": "everyX",
                    "value": 1,
                    "unit": "hours"
                }}
            ]
        }},
        "timezone": "UTC"
    }},
    "id": "{node.node_id}",
    "name": "{node.name}",
    "type": "n8n-nodes-base.scheduleTrigger",
    "typeVersion": 1.1,
    "position": {json.dumps(node.position)}
}}
'''
        elif node.type == N8NNodeType.FUNCTION:
            code = f'''
// Function Node: {node.name}
// Node ID: {node.node_id}

// Node parameters
const parameters = {json.dumps(node.parameters, indent=2)};

// Example Function node configuration
{{
    "parameters": {{
        "functionCode": `
// Function code for {node.name}
// Input items are available as $input.all() or $input.item()
// Output items can be returned as individual items or arrays

// Example: Process input data
const inputData = $input.all();

// Transform data
const processedData = inputData.map(item => {{
    return {{
        ...item,
        processed: true,
        timestamp: new Date().toISOString(),
        // Add your custom logic here
        calculatedValue: item.value * 2
    }};
}});

// Return output
return processedData;
`
    }},
    "id": "{node.node_id}",
    "name": "{node.name}",
    "type": "n8n-nodes-base.function",
    "typeVersion": 1,
    "position": {json.dumps(node.position)}
}}
'''
        elif node.type == N8NNodeType.SET:
            code = f'''
// Set Node: {node.name}
// Node ID: {node.node_id}

// Node parameters
const parameters = {json.dumps(node.parameters, indent=2)};

// Example Set node configuration
{{
    "parameters": {{
        "values": {{
            "string": [
                {{
                    "name": "message",
                    "value": "Hello World"
                }}
            ],
            "number": [
                {{
                    "name": "count",
                    "value": 42
                }}
            ],
            "boolean": [
                {{
                    "name": "isActive",
                    "value": true
                }}
            ]
        }},
        "options": {{}}
    }},
    "id": "{node.node_id}",
    "name": "{node.name}",
    "type": "n8n-nodes-base.set",
    "typeVersion": 2,
    "position": {json.dumps(node.position)}
}}
'''
        elif node.type == N8NNodeType.CONDITION:
            code = f'''
// If/Condition Node: {node.name}
// Node ID: {node.node_id}

// Node parameters
const parameters = {json.dumps(node.parameters, indent=2)};

// Example Condition node configuration
{{
    "parameters": {{
        "conditions": {{
            "string": [],
            "number": [],
            "boolean": [
                {{
                    "value1": "={{ $json.isActive }}",
                    "operation": "equal",
                    "value2": true
                }}
            ]
        }},
        "combine": "ALL"
    }},
    "id": "{node.node_id}",
    "name": "{node.name}",
    "type": "n8n-nodes-base.if",
    "typeVersion": 1,
    "position": {json.dumps(node.position)}
}}
'''
        else:
            code = f'''
// Generic Node: {node.name}
// Node ID: {node.node_id}
// Type: {node.type.value}

// Node parameters
const parameters = {json.dumps(node.parameters, indent=2)};

// Node configuration
{{
    "parameters": {json.dumps(node.parameters, indent=4)},
    "id": "{node.node_id}",
    "name": "{node.name}",
    "type": "n8n-nodes-base.{node.type.value}",
    "typeVersion": 1,
    "position": {json.dumps(node.position)}
}}
'''
        
        return code
    
    async def add_connection(self, workflow_id: str, connection_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a connection between nodes in a workflow
        
        Args:
            workflow_id: ID of the workflow
            connection_spec: Connection specification
            
        Returns:
            Dictionary with connection configuration
        """
        print(f"🔗 {self.name}: Adding connection to workflow {workflow_id}")
        
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        
        source_node = connection_spec.get("source_node")
        source_port = connection_spec.get("source_port", 0)
        target_node = connection_spec.get("target_node")
        target_port = connection_spec.get("target_port", 0)
        
        # Validate nodes exist
        if source_node not in workflow.nodes:
            raise ValueError(f"Source node {source_node} not found in workflow")
        if target_node not in workflow.nodes:
            raise ValueError(f"Target node {target_node} not found in workflow")
        
        # Create connection
        connection = N8NConnection(
            source_node=source_node,
            source_port=source_port,
            target_node=target_node,
            target_port=target_port
        )
        
        workflow.connections.append(connection)
        
        result = {
            "workflow_id": workflow_id,
            "source_node": source_node,
            "source_port": source_port,
            "target_node": target_node,
            "target_port": target_port,
            "status": "added"
        }
        
        print(f"✅ {self.name}: Connection from {source_node} to {target_node} added")
        return result
    
    async def create_credential(self, credential_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a credential for external service integration
        
        Args:
            credential_spec: Credential specification
            
        Returns:
            Dictionary with credential configuration
        """
        print(f"🔐 {self.name}: Creating credential {credential_spec.get('name', 'Unnamed')}")
        
        credential_id = credential_spec.get("credential_id", f"cred_{len(self.credentials) + 1}")
        credential_name = credential_spec.get("name", "Unnamed Credential")
        credential_type = credential_spec.get("type", "apiKey")
        credential_data = credential_spec.get("data", {})
        
        # Create credential
        credential = N8NCredential(
            credential_id=credential_id,
            name=credential_name,
            type=credential_type,
            data=credential_data
        )
        
        self.credentials[credential_id] = credential
        
        # Generate credential configuration
        credential_config = self._generate_credential_config(credential)
        
        result = {
            "credential_id": credential_id,
            "name": credential_name,
            "type": credential_type,
            "config": credential_config,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Credential {credential_name} created with ID {credential_id}")
        return result
    
    def _generate_credential_config(self, credential: N8NCredential) -> Dict[str, Any]:
        """Generate credential configuration"""
        if credential.type == "apiKey":
            return {
                "name": credential.name,
                "type": "apiKey",
                "value": credential.data.get("api_key", ""),
                "host": credential.data.get("host", ""),
                "headers": credential.data.get("headers", {})
            }
        elif credential.type == "oauth2":
            return {
                "name": credential.name,
                "type": "oauth2",
                "clientId": credential.data.get("client_id", ""),
                "clientSecret": credential.data.get("client_secret", ""),
                "tokenUrl": credential.data.get("token_url", ""),
                "scope": credential.data.get("scope", "")
            }
        elif credential.type == "basicAuth":
            return {
                "name": credential.name,
                "type": "basicAuth",
                "username": credential.data.get("username", ""),
                "password": credential.data.get("password", "")
            }
        else:
            return {
                "name": credential.name,
                "type": credential.type,
                "data": credential.data
            }
    
    async def validate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Validate a workflow configuration
        
        Args:
            workflow_id: ID of the workflow to validate
            
        Returns:
            Dictionary with validation results
        """
        print(f"✅ {self.name}: Validating workflow {workflow_id}")
        
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        
        validation = {
            "workflow": workflow_id,
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Check workflow name
        if not workflow.name:
            validation["valid"] = False
            validation["errors"].append("Workflow name is required")
        
        # Check for nodes
        if not workflow.nodes:
            validation["warnings"].append("Workflow has no nodes")
        else:
            # Check each node
            for node_id, node in workflow.nodes.items():
                if not node.name:
                    validation["warnings"].append(f"Node {node_id} has no name")
                
                # Check for trigger nodes
                if node.type == N8NNodeType.TRIGGER:
                    validation["recommendations"].append(f"Trigger node {node.name} found")
        
        # Check connections
        if workflow.connections:
            for conn in workflow.connections:
                if conn.source_node not in workflow.nodes:
                    validation["errors"].append(f"Connection source node {conn.source_node} not found")
                if conn.target_node not in workflow.nodes:
                    validation["errors"].append(f"Connection target node {conn.target_node} not found")
        else:
            if len(workflow.nodes) > 1:
                validation["warnings"].append("Workflow has multiple nodes but no connections")
        
        # Check for trigger nodes
        trigger_nodes = [node for node in workflow.nodes.values() if node.type == N8NNodeType.TRIGGER]
        if not trigger_nodes and len(workflow.nodes) > 0:
            validation["recommendations"].append("Consider adding a trigger node to start the workflow")
        
        # Check for multiple trigger nodes
        if len(trigger_nodes) > 1:
            validation["warnings"].append(f"Workflow has {len(trigger_nodes)} trigger nodes (usually only one is needed)")
        
        print(f"✅ {self.name}: Workflow {workflow_id} validation completed")
        return validation
    
    async def generate_workflow_documentation(self, workflow_id: str) -> Dict[str, Any]:
        """
        Generate documentation for a workflow
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Dictionary with documentation
        """
        print(f"📚 {self.name}: Generating documentation for workflow {workflow_id}")
        
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        
        documentation = {
            "workflow": {
                "id": workflow.workflow_id,
                "name": workflow.name,
                "description": workflow.description,
                "active": workflow.active,
                "settings": workflow.settings,
                "variables": workflow.variables
            },
            "nodes": [],
            "connections": [],
            "credentials": [],
            "usage": {}
        }
        
        # Document nodes
        for node_id, node in workflow.nodes.items():
            node_doc = {
                "id": node.node_id,
                "name": node.name,
                "type": node.type.value,
                "position": node.position,
                "description": node.parameters.get("description", ""),
                "parameters": node.parameters,
                "credentials": node.credentials,
                "continue_on_fail": node.continue_on_fail,
                "disabled": node.disabled
            }
            documentation["nodes"].append(node_doc)
        
        # Document connections
        for conn in workflow.connections:
            conn_doc = {
                "source_node": conn.source_node,
                "source_port": conn.source_port,
                "target_node": conn.target_node,
                "target_port": conn.target_port
            }
            documentation["connections"].append(conn_doc)
        
        # Document credentials
        for cred_id, cred in self.credentials.items():
            if cred.credential_id in [node.credentials for node in workflow.nodes.values() if node.credentials]:
                cred_doc = {
                    "id": cred.credential_id,
                    "name": cred.name,
                    "type": cred.type
                }
                documentation["credentials"].append(cred_doc)
        
        # Generate usage examples
        workflow_json = self._generate_workflow_json(workflow)
        documentation["usage"] = {
            "import": f'''
# Import workflow into n8n

1. Open n8n editor
2. Click "Import" button
3. Select "From File" or "From URL"
4. Paste the following JSON:

```json
{workflow_json}
```

5. Click "Import" to create the workflow
''',
            "activation": f'''
# Activate the workflow

1. Open the workflow in n8n
2. Click the "Activate" toggle switch
3. The workflow will start running based on its triggers

# Note: Make sure all required credentials are configured before activating
''',
            "testing": f'''
# Test the workflow

1. Click "Execute Workflow" button
2. Or trigger the workflow manually
3. Check the execution logs for any errors
4. Verify the output matches expectations
'''
        }
        
        print(f"✅ {self.name}: Documentation generated for workflow {workflow_id}")
        return documentation
    
    async def export_workflow(self, workflow_id: str, format_type: str = "json") -> Dict[str, Any]:
        """
        Export a workflow in a specific format
        
        Args:
            workflow_id: ID of the workflow
            format_type: Export format ("json", "yaml", "url")
            
        Returns:
            Dictionary with exported workflow
        """
        print(f"📤 {self.name}: Exporting workflow {workflow_id} as {format_type}")
        
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        
        if format_type == "json":
            workflow_json = self._generate_workflow_json(workflow)
            
            result = {
                "workflow_id": workflow_id,
                "format": "json",
                "data": workflow_json,
                "status": "exported"
            }
        elif format_type == "yaml":
            workflow_json = self._generate_workflow_json(workflow)
            import yaml
            workflow_yaml = yaml.dump(json.loads(workflow_json), default_flow_style=False)
            
            result = {
                "workflow_id": workflow_id,
                "format": "yaml",
                "data": workflow_yaml,
                "status": "exported"
            }
        elif format_type == "url":
            # Generate a URL-encoded version
            workflow_json = self._generate_workflow_json(workflow)
            import urllib.parse
            encoded = urllib.parse.quote(workflow_json)
            
            result = {
                "workflow_id": workflow_id,
                "format": "url",
                "data": f"https://n8n.io/workflow/{encoded}",
                "status": "exported"
            }
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        print(f"✅ {self.name}: Workflow {workflow_id} exported as {format_type}")
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "current_project": self.current_project,
            "current_workflow": self.current_workflow,
            "workflows_count": len(self.workflows),
            "credentials_count": len(self.credentials),
            "performance_metrics": self.performance_metrics,
            "skills": list(self.skills.keys())
        }
    
    def reset(self) -> None:
        """Reset agent state"""
        self.current_project = None
        self.current_workflow = None
        self.workflows.clear()
        self.credentials.clear()
        self.performance_metrics.clear()
        print(f"🔄 {self.name}: Agent state reset")
