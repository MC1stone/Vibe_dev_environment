"""
MCP Agent - Specialist for Model Context Protocol (MCP)

Responsibilities:
- MCP server development and configuration
- Tool integration via MCP
- Context management
- Resource handling
- MCP client development
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio


class MCPComponent(Enum):
    """MCP components"""
    SERVER = "server"
    CLIENT = "client"
    TOOL = "tool"
    RESOURCE = "resource"
    CONTEXT = "context"


class MCPTransport(Enum):
    """MCP transport protocols"""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"
    IN_PROCESS = "in_process"


@dataclass
class MCPTool:
    """Represents an MCP tool"""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    optional: List[str] = field(default_factory=list)


@dataclass
class MCPResource:
    """Represents an MCP resource"""
    name: str
    description: str
    uri: str
    mime_type: str
    read_only: bool = True


@dataclass
class MCPServer:
    """Represents an MCP server configuration"""
    name: str
    description: str
    version: str = "1.0.0"
    transport: MCPTransport = MCPTransport.STDIO
    tools: List[MCPTool] = field(default_factory=list)
    resources: List[MCPResource] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)


@dataclass
class MCPAgent:
    """
    MCP Specialist Agent
    
    This agent specializes in Model Context Protocol development and integration.
    It can create MCP servers, tools, and resources for various applications.
    """
    
    agent_id: str = "mcp_agent_001"
    name: str = "MCP Specialist"
    description: str = "Expert in Model Context Protocol development and integration"
    version: str = "1.0.0"
    
    # Agent capabilities
    supported_transports: List[MCPTransport] = field(default_factory=lambda: [
        MCPTransport.STDIO,
        MCPTransport.HTTP,
        MCPTransport.WEBSOCKET,
    ])
    
    # Agent skills
    skills: Dict[str, str] = field(default_factory=dict)
    
    # Current project state
    current_project: Optional[str] = None
    current_server: Optional[str] = None
    
    # MCP servers being developed
    servers: Dict[str, MCPServer] = field(default_factory=dict)
    
    # MCP tools
    tools: Dict[str, MCPTool] = field(default_factory=dict)
    
    # MCP resources
    resources: Dict[str, MCPResource] = field(default_factory=dict)
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the agent with default skills"""
        self._initialize_skills()
    
    def _initialize_skills(self) -> None:
        """Initialize the agent's skill set"""
        self.skills = {
            "server_development": "Develop MCP servers with various transport protocols",
            "tool_creation": "Create MCP tools with proper schemas and validation",
            "resource_management": "Manage MCP resources and context sharing",
            "client_development": "Develop MCP clients for tool consumption",
            "protocol_implementation": "Implement MCP protocol specifications",
            "error_handling": "Handle MCP errors and edge cases",
            "security": "Implement MCP security best practices",
            "testing": "Test MCP servers and tools",
            "documentation": "Document MCP implementations",
            "integration": "Integrate MCP with other systems and frameworks"
        }
    
    async def create_mcp_server(self, server_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an MCP server
        
        Args:
            server_spec: MCP server specification
            
        Returns:
            Dictionary with server configuration
        """
        print(f"🚀 {self.name}: Creating MCP server {server_spec.get('name', 'Unnamed')}")
        
        server_name = server_spec.get("name", "unnamed_server")
        description = server_spec.get("description", "")
        version = server_spec.get("version", "1.0.0")
        transport_str = server_spec.get("transport", "stdio")
        
        # Validate transport
        try:
            transport = MCPTransport(transport_str)
        except ValueError:
            transport = MCPTransport.STDIO
            print(f"⚠️  Transport {transport_str} not supported, defaulting to STDIO")
        
        # Create server
        server = MCPServer(
            name=server_name,
            description=description,
            version=version,
            transport=transport,
            capabilities=server_spec.get("capabilities", ["tools", "resources"])
        )
        
        self.servers[server_name] = server
        self.current_server = server_name
        
        # Create server configuration
        config = {
            "name": server_name,
            "description": description,
            "version": version,
            "transport": transport.value,
            "capabilities": server.capabilities,
            "tools": [],
            "resources": [],
            "status": "created"
        }
        
        print(f"✅ {self.name}: MCP server {server_name} created with {transport.value} transport")
        return config
    
    async def add_mcp_tool(self, server_name: str, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a tool to an MCP server
        
        Args:
            server_name: Name of the server
            tool_spec: Tool specification
            
        Returns:
            Dictionary with tool configuration
        """
        print(f"🔧 {self.name}: Adding tool to MCP server {server_name}")
        
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")
        
        server = self.servers[server_name]
        
        tool_name = tool_spec.get("name", "unnamed_tool")
        description = tool_spec.get("description", "")
        input_schema = tool_spec.get("input_schema", {})
        output_schema = tool_spec.get("output_schema", {})
        required = tool_spec.get("required", [])
        optional = tool_spec.get("optional", [])
        
        # Create tool
        tool = MCPTool(
            name=tool_name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            required=required,
            optional=optional
        )
        
        self.tools[tool_name] = tool
        server.tools.append(tool)
        
        # Generate tool code
        tool_code = self._generate_mcp_tool_code(tool)
        
        result = {
            "server": server_name,
            "tool_name": tool_name,
            "description": description,
            "input_schema": input_schema,
            "output_schema": output_schema,
            "required": required,
            "optional": optional,
            "code": tool_code,
            "status": "added"
        }
        
        print(f"✅ {self.name}: Tool {tool_name} added to server {server_name}")
        return result
    
    def _generate_mcp_tool_code(self, tool: MCPTool) -> str:
        """Generate MCP tool implementation code"""
        code = f'''
import json
from typing import Dict, Any, Optional
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

# Define the tool
{tool.name}_tool = Tool(
    name="{tool.name}",
    description="{tool.description}",
    inputSchema={json.dumps(tool.input_schema, indent=4)},
)

# Tool handler
async def handle_{tool.name}(args: Dict[str, Any]) -> List[TextContent | ImageContent | EmbeddedResource]:
    """
    Handle {tool.name} tool execution
    
    Args:
        args: Tool arguments
        
    Returns:
        List of content items (text, images, or resources)
    """
    try:
        # Validate required arguments
        for required_arg in {tool.required}:
            if required_arg not in args:
                raise ValueError(f"Missing required argument: {{required_arg}}")
        
        # Process arguments
        # TODO: Implement tool logic
        result = {{
            "status": "success",
            "message": "Tool executed successfully",
            "data": args
        }}
        
        # Return result as text content
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({{"error": str(e)}}))]

# Create server
server = Server("{self.current_server or 'mcp_server'}")

# Register tool
@server.register_tool({tool.name}_tool)
async def {tool.name}_wrapper(args: Dict[str, Any]) -> List[TextContent | ImageContent | EmbeddedResource]:
    return await handle_{tool.name}(args)

# Server initialization
async def initialize_server():
    options = InitializationOptions(
        server_name="{self.current_server or 'mcp_server'}",
        server_version="1.0.0",
        capabilities=["tools"],
    )
    
    await server.initialize(options)
    print(f"Server {{server.name}} initialized with {{len(server.tools)}} tools")

if __name__ == "__main__":
    import asyncio
    asyncio.run(initialize_server())
'''
        return code
    
    async def add_mcp_resource(self, server_name: str, resource_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a resource to an MCP server
        
        Args:
            server_name: Name of the server
            resource_spec: Resource specification
            
        Returns:
            Dictionary with resource configuration
        """
        print(f"📚 {self.name}: Adding resource to MCP server {server_name}")
        
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")
        
        server = self.servers[server_name]
        
        resource_name = resource_spec.get("name", "unnamed_resource")
        description = resource_spec.get("description", "")
        uri = resource_spec.get("uri", f"resource://{resource_name}")
        mime_type = resource_spec.get("mime_type", "text/plain")
        read_only = resource_spec.get("read_only", True)
        
        # Create resource
        resource = MCPResource(
            name=resource_name,
            description=description,
            uri=uri,
            mime_type=mime_type,
            read_only=read_only
        )
        
        self.resources[resource_name] = resource
        server.resources.append(resource)
        
        # Generate resource code
        resource_code = self._generate_mcp_resource_code(resource)
        
        result = {
            "server": server_name,
            "resource_name": resource_name,
            "description": description,
            "uri": uri,
            "mime_type": mime_type,
            "read_only": read_only,
            "code": resource_code,
            "status": "added"
        }
        
        print(f"✅ {self.name}: Resource {resource_name} added to server {server_name}")
        return result
    
    def _generate_mcp_resource_code(self, resource: MCPResource) -> str:
        """Generate MCP resource implementation code"""
        code = f'''
import json
from typing import Dict, Any, Optional, List
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource, ResourceTemplate

# Define the resource template
{resource.name}_template = ResourceTemplate(
    name="{resource.name}",
    description="{resource.description}",
    uri="{resource.uri}",
    mimeType="{resource.mime_type}",
    readOnly={str(resource.read_only).lower()},
)

# Resource handler
async def handle_{resource.name}_read() -> str:
    """
    Handle resource read operation
    
    Returns:
        Resource content as string
    """
    # TODO: Implement resource read logic
    return "Resource content goes here"

async def handle_{resource.name}_list() -> List[ResourceTemplate]:
    """
    Handle resource listing
    
    Returns:
        List of resource templates
    """
    return [{resource.name}_template]

# Create server
server = Server("{self.current_server or 'mcp_server'}")

# Register resource
@server.register_resource("{resource.uri}")
async def {resource.name}_wrapper() -> ResourceTemplate:
    return {resource.name}_template

# Server initialization
async def initialize_server():
    options = InitializationOptions(
        server_name="{self.current_server or 'mcp_server'}",
        server_version="1.0.0",
        capabilities=["resources"],
    )
    
    await server.initialize(options)
    print(f"Server {{server.name}} initialized with {{len(server.resources)}} resources")

if __name__ == "__main__":
    import asyncio
    asyncio.run(initialize_server())
'''
        return code
    
    async def create_mcp_client(self, client_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an MCP client
        
        Args:
            client_spec: MCP client specification
            
        Returns:
            Dictionary with client configuration
        """
        print(f"💻 {self.name}: Creating MCP client {client_spec.get('name', 'Unnamed')}")
        
        client_name = client_spec.get("name", "unnamed_client")
        description = client_spec.get("description", "")
        server_urls = client_spec.get("server_urls", [])
        
        # Generate client code
        client_code = self._generate_mcp_client_code(client_name, server_urls)
        
        result = {
            "client_name": client_name,
            "description": description,
            "server_urls": server_urls,
            "code": client_code,
            "status": "created"
        }
        
        print(f"✅ {self.name}: MCP client {client_name} created")
        return result
    
    def _generate_mcp_client_code(self, client_name: str, server_urls: List[str]) -> str:
        """Generate MCP client implementation code"""
        code = f'''
import asyncio
import json
from typing import Dict, Any, List, Optional
from mcp.client import Client
from mcp.types import TextContent, ImageContent, CallToolRequest

class {client_name}Client:
    """
    MCP client for {client_name}
    
    This client connects to MCP servers and provides access to their tools and resources.
    """
    
    def __init__(self, server_urls: List[str] = None):
        self.server_urls = server_urls or {server_urls}
        self.clients: Dict[str, Client] = {{}}
        
    async def connect(self) -> None:
        """Connect to all MCP servers"""
        print(f"Connecting to {{len(self.server_urls)}} MCP servers...")
        
        for url in self.server_urls:
            try:
                client = Client(url)
                await client.connect()
                self.clients[url] = client
                print(f"Connected to server at {{url}}")
                
                # List available tools
                tools = await client.list_tools()
                print(f"Available tools: {{[tool.name for tool in tools]}}")
                
            except Exception as e:
                print(f"Failed to connect to {{url}}: {{e}}")
        
    async def list_tools(self, server_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available tools from a server
        
        Args:
            server_url: Specific server URL (optional)
            
        Returns:
            List of available tools
        """
        if server_url:
            if server_url not in self.clients:
                raise ValueError(f"Not connected to server: {{server_url}}")
            client = self.clients[server_url]
            tools = await client.list_tools()
            return [{{ "name": tool.name, "description": tool.description }} for tool in tools]
        else:
            all_tools = []
            for url, client in self.clients.items():
                tools = await client.list_tools()
                all_tools.extend([{{ "name": tool.name, "description": tool.description, "server": url }} for tool in tools])
            return all_tools
    
    async def call_tool(self, server_url: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on a specific server
        
        Args:
            server_url: Server URL
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool response
        """
        if server_url not in self.clients:
            raise ValueError(f"Not connected to server: {{server_url}}")
        
        client = self.clients[server_url]
        
        # Create request
        request = CallToolRequest(
            name=tool_name,
            arguments=arguments
        )
        
        # Call tool
        response = await client.call_tool(request)
        
        # Process response
        result = {{
            "tool": tool_name,
            "server": server_url,
            "success": True,
            "content": []
        }}
        
        for content in response.content:
            if hasattr(content, 'text'):
                result["content"].append({{"type": "text", "text": content.text}})
            elif hasattr(content, 'image'):
                result["content"].append({{"type": "image", "data": content.image.data}})
        
        return result
    
    async def list_resources(self, server_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available resources from a server
        
        Args:
            server_url: Specific server URL (optional)
            
        Returns:
            List of available resources
        """
        if server_url:
            if server_url not in self.clients:
                raise ValueError(f"Not connected to server: {{server_url}}")
            client = self.clients[server_url]
            resources = await client.list_resources()
            return [{{ "name": resource.name, "uri": resource.uri, "mime_type": resource.mimeType }} for resource in resources]
        else:
            all_resources = []
            for url, client in self.clients.items():
                resources = await client.list_resources()
                all_resources.extend([{{ "name": resource.name, "uri": resource.uri, "mime_type": resource.mimeType, "server": url }} for resource in resources])
            return all_resources
    
    async def read_resource(self, server_url: str, resource_uri: str) -> Dict[str, Any]:
        """
        Read a resource from a server
        
        Args:
            server_url: Server URL
            resource_uri: Resource URI
            
        Returns:
            Resource content
        """
        if server_url not in self.clients:
            raise ValueError(f"Not connected to server: {{server_url}}")
        
        client = self.clients[server_url]
        content = await client.read_resource(resource_uri)
        
        return {{
            "resource": resource_uri,
            "server": server_url,
            "content": content.text if hasattr(content, 'text') else str(content),
            "mime_type": content.mimeType if hasattr(content, 'mimeType') else "text/plain"
        }}
    
    async def close(self) -> None:
        """Close all connections"""
        for url, client in self.clients.items():
            await client.close()
            print(f"Disconnected from server at {{url}}")
        self.clients.clear()

# Usage example
async def main():
    client = {client_name}Client({server_urls})
    
    try:
        await client.connect()
        
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {{tools}}")
        
        # Call a tool (example)
        if tools:
            tool = tools[0]
            result = await client.call_tool(
                server_url={server_urls[0] if server_urls else ""},
                tool_name=tool["name"],
                arguments={{}}
            )
            print(f"Tool result: {{result}}")
        
        # List resources
        resources = await client.list_resources()
        print(f"Available resources: {{resources}}")
        
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
'''
        return code
    
    async def validate_mcp_server(self, server_name: str) -> Dict[str, Any]:
        """
        Validate an MCP server configuration
        
        Args:
            server_name: Name of the server to validate
            
        Returns:
            Dictionary with validation results
        """
        print(f"✅ {self.name}: Validating MCP server {server_name}")
        
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")
        
        server = self.servers[server_name]
        
        validation = {
            "server": server_name,
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Check server name
        if not server.name:
            validation["valid"] = False
            validation["errors"].append("Server name is required")
        
        # Check tools
        if not server.tools:
            validation["warnings"].append("No tools defined for the server")
        else:
            for tool in server.tools:
                if not tool.name:
                    validation["errors"].append(f"Tool without name found")
                if not tool.description:
                    validation["warnings"].append(f"Tool {tool.name} has no description")
        
        # Check resources
        if not server.resources:
            validation["warnings"].append("No resources defined for the server")
        
        # Check transport
        if server.transport not in self.supported_transports:
            validation["warnings"].append(f"Transport {server.transport.value} may not be fully supported")
        
        # Recommendations
        if not server.tools and not server.resources:
            validation["recommendations"].append("Consider adding tools or resources to make the server useful")
        
        print(f"✅ {self.name}: Server {server_name} validation completed")
        return validation
    
    async def generate_mcp_documentation(self, server_name: str) -> Dict[str, Any]:
        """
        Generate documentation for an MCP server
        
        Args:
            server_name: Name of the server
            
        Returns:
            Dictionary with documentation
        """
        print(f"📚 {self.name}: Generating documentation for MCP server {server_name}")
        
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")
        
        server = self.servers[server_name]
        
        documentation = {
            "server": {
                "name": server.name,
                "description": server.description,
                "version": server.version,
                "transport": server.transport.value,
                "capabilities": server.capabilities
            },
            "tools": [],
            "resources": [],
            "usage_examples": {}
        }
        
        # Document tools
        for tool in server.tools:
            tool_doc = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "output_schema": tool.output_schema,
                "required_parameters": tool.required,
                "optional_parameters": tool.optional
            }
            documentation["tools"].append(tool_doc)
        
        # Document resources
        for resource in server.resources:
            resource_doc = {
                "name": resource.name,
                "description": resource.description,
                "uri": resource.uri,
                "mime_type": resource.mime_type,
                "read_only": resource.read_only
            }
            documentation["resources"].append(resource_doc)
        
        # Generate usage examples
        if server.tools:
            first_tool = server.tools[0]
            documentation["usage_examples"]["tool_call"] = f'''
# Example: Calling the {first_tool.name} tool

```python
from mcp.client import Client
import asyncio

async def call_tool():
    client = Client("{{server_url}}")
    await client.connect()
    
    result = await client.call_tool(
        name="{first_tool.name}",
        arguments={{
            "param1": "value1",
            "param2": "value2"
        }}
    )
    
    print(result)
    await client.close()

asyncio.run(call_tool())
```
'''
        
        if server.resources:
            first_resource = server.resources[0]
            documentation["usage_examples"]["resource_access"] = f'''
# Example: Accessing the {first_resource.name} resource

```python
from mcp.client import Client
import asyncio

async def read_resource():
    client = Client("{{server_url}}")
    await client.connect()
    
    content = await client.read_resource("{first_resource.uri}")
    print(content.text)
    
    await client.close()

asyncio.run(read_resource())
```
'''
        
        print(f"✅ {self.name}: Documentation generated for server {server_name}")
        return documentation
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "current_project": self.current_project,
            "current_server": self.current_server,
            "servers_count": len(self.servers),
            "tools_count": len(self.tools),
            "resources_count": len(self.resources),
            "performance_metrics": self.performance_metrics,
            "skills": list(self.skills.keys())
        }
    
    def reset(self) -> None:
        """Reset agent state"""
        self.current_project = None
        self.current_server = None
        self.servers.clear()
        self.tools.clear()
        self.resources.clear()
        self.performance_metrics.clear()
        print(f"🔄 {self.name}: Agent state reset")
