"""
MCP Server for NIR Intelligence Platform

This server orchestrates communication between all agents and resources,
managing tool access, permissions, and federated learning data sharing.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class MCPServer:
    """
    Model Context Protocol (MCP) Server for NIR Intelligence Platform.
    
    Orchestrates communication between:
    - CrewAI agents
    - Vector databases (Qdrant, Faiss)
    - PostgreSQL database
    - n8n workflows
    - Quarto reporting
    - Django frontend
    """
    
    def __init__(self, 
                 crewai_url: str = "http://localhost:8002",
                 qdrant_url: str = "http://localhost:6333",
                 faiss_url: str = "http://localhost:5001",
                 postgres_url: str = "postgresql://postgres:postgres@localhost:5432/nir_db",
                 ollama_url: str = "http://localhost:11434",
                 n8n_url: str = "http://localhost:5678"):
        """
        Initialize MCP Server with service URLs.
        
        Args:
            crewai_url: URL for CrewAI orchestration
            qdrant_url: URL for Qdrant vector database
            faiss_url: URL for Faiss vector index
            postgres_url: URL for PostgreSQL database
            ollama_url: URL for Ollama (Mistral model)
            n8n_url: URL for n8n workflow automation
        """
        self.crewai_url = crewai_url
        self.qdrant_url = qdrant_url
        self.faiss_url = faiss_url
        self.postgres_url = postgres_url
        self.ollama_url = ollama_url
        self.n8n_url = n8n_url
        
        # Agent registry
        self.agents: Dict[str, Any] = {}
        
        # Resource registry
        self.resources: Dict[str, Dict] = {
            "qdrant": {"url": qdrant_url, "type": "vector_db"},
            "faiss": {"url": faiss_url, "type": "vector_index"},
            "postgres": {"url": postgres_url, "type": "relational_db"},
            "ollama": {"url": ollama_url, "type": "llm"},
            "n8n": {"url": n8n_url, "type": "workflow"},
        }
        
        # Tool registry
        self.tools: Dict[str, Dict] = {}
        
        # WebSocket connections
        self.websocket_connections: List[WebSocket] = []
        
        # Initialize FastAPI app
        self.app = FastAPI(title="NIR MCP Server")
        self._setup_middleware()
        self._setup_routes()
        
        logger.info("MCP Server initialized")
    
    def _setup_middleware(self):
        """Set up CORS middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Set up API routes."""
        # Health check
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": "mcp_server"}
        
        # Agent management
        @self.app.post("/agents/register")
        async def register_agent(agent_data: Dict):
            agent_id = agent_data.get("id")
            if not agent_id:
                raise HTTPException(status_code=400, detail="Agent ID required")
            
            self.agents[agent_id] = agent_data
            logger.info(f"Registered agent: {agent_id}")
            
            # Notify all connected clients
            await self._broadcast({
                "type": "agent_registered",
                "data": agent_data
            })
            
            return {"status": "registered", "agent_id": agent_id}
        
        @self.app.get("/agents")
        async def list_agents():
            return {"agents": list(self.agents.keys())}
        
        @self.app.get("/agents/{agent_id}")
        async def get_agent(agent_id: str):
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found")
            return self.agents[agent_id]
        
        # Resource management
        @self.app.get("/resources")
        async def list_resources():
            return {"resources": self.resources}
        
        @self.app.get("/resources/{resource_name}")
        async def get_resource(resource_name: str):
            if resource_name not in self.resources:
                raise HTTPException(status_code=404, detail="Resource not found")
            return self.resources[resource_name]
        
        # Tool management
        @self.app.post("/tools/register")
        async def register_tool(tool_data: Dict):
            tool_name = tool_data.get("name")
            if not tool_name:
                raise HTTPException(status_code=400, detail="Tool name required")
            
            self.tools[tool_name] = tool_data
            logger.info(f"Registered tool: {tool_name}")
            
            return {"status": "registered", "tool_name": tool_name}
        
        @self.app.get("/tools")
        async def list_tools():
            return {"tools": list(self.tools.keys())}
        
        @self.app.post("/tools/{tool_name}/execute")
        async def execute_tool(tool_name: str, parameters: Dict):
            if tool_name not in self.tools:
                raise HTTPException(status_code=404, detail="Tool not found")
            
            # Execute tool logic here
            logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
            
            # For now, return mock response
            return {
                "status": "executed",
                "tool": tool_name,
                "parameters": parameters,
                "result": f"Result from {tool_name}"
            }
        
        # Task execution
        @self.app.post("/tasks/execute")
        async def execute_task(task_data: Dict):
            """Execute a task using the appropriate agent."""
            agent_id = task_data.get("agent_id")
            task = task_data.get("task")
            
            if not agent_id or not task:
                raise HTTPException(status_code=400, detail="Agent ID and task required")
            
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            # Forward task to CrewAI for execution
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.crewai_url}/tasks",
                        json={"agent_id": agent_id, "task": task}
                    )
                    return response.json()
            except Exception as e:
                logger.error(f"Error executing task: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # WebSocket for real-time communication
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    logger.info(f"Received WebSocket message: {message}")
                    
                    # Handle different message types
                    if message.get("type") == "agent_message":
                        # Forward to appropriate agent
                        await self._handle_agent_message(message)
                    elif message.get("type") == "resource_request":
                        # Handle resource request
                        await self._handle_resource_request(message, websocket)
                    
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
                logger.info("WebSocket disconnected")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.websocket_connections.remove(websocket)
        
        # Analysis endpoints
        @self.app.post("/analysis/spectral")
        async def spectral_analysis(analysis_data: Dict):
            """Perform spectral analysis using CrewAI agents."""
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.crewai_url}/analysis/spectral",
                        json=analysis_data
                    )
                    return response.json()
            except Exception as e:
                logger.error(f"Error in spectral analysis: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/analysis/metadata")
        async def metadata_analysis(analysis_data: Dict):
            """Perform metadata quality analysis."""
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.crewai_url}/analysis/metadata",
                        json=analysis_data
                    )
                    return response.json()
            except Exception as e:
                logger.error(f"Error in metadata analysis: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/analysis/calibration")
        async def calibration_analysis(analysis_data: Dict):
            """Perform calibration analysis."""
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.crewai_url}/analysis/calibration",
                        json=analysis_data
                    )
                    return response.json()
            except Exception as e:
                logger.error(f"Error in calibration analysis: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Report generation
        @self.app.post("/reports/generate")
        async def generate_report(report_data: Dict):
            """Generate Quarto report."""
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.n8n_url}/webhook/report-generation",
                        json=report_data
                    )
                    return response.json()
            except Exception as e:
                logger.error(f"Error generating report: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Federated learning
        @self.app.post("/federated/share")
        async def share_federated_data(data: Dict):
            """Share data with federated learning system (requires user consent)."""
            # Check for user consent
            if not data.get("user_consent", False):
                raise HTTPException(
                    status_code=403, 
                    detail="User consent required for federated learning"
                )
            
            # Process federated sharing
            logger.info(f"Sharing data with federated system: {data.get('data_id')}")
            
            return {
                "status": "shared",
                "data_id": data.get("data_id"),
                "message": "Data shared with federated learning system"
            }
    
    async def _handle_agent_message(self, message: Dict):
        """Handle messages from agents."""
        agent_id = message.get("agent_id")
        content = message.get("content")
        
        if agent_id in self.agents:
            logger.info(f"Message from agent {agent_id}: {content}")
            
            # Broadcast to all connected clients
            await self._broadcast({
                "type": "agent_message",
                "agent_id": agent_id,
                "content": content,
                "timestamp": message.get("timestamp")
            })
    
    async def _handle_resource_request(self, message: Dict, websocket: WebSocket):
        """Handle resource requests."""
        resource_name = message.get("resource")
        operation = message.get("operation")
        
        if resource_name not in self.resources:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Resource {resource_name} not found"
            }))
            return
        
        # Handle different operations
        if operation == "query":
            query = message.get("query")
            result = await self._query_resource(resource_name, query)
            await websocket.send_text(json.dumps({
                "type": "resource_response",
                "resource": resource_name,
                "operation": operation,
                "result": result
            }))
    
    async def _query_resource(self, resource_name: str, query: Dict) -> Dict:
        """Query a resource."""
        resource = self.resources[resource_name]
        
        if resource_name == "qdrant":
            # Query Qdrant
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{resource['url']}/collections/{query.get('collection')}/points/search",
                    json=query.get("params", {})
                )
                return response.json()
        
        elif resource_name == "faiss":
            # Query Faiss
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{resource['url']}/search",
                    json=query
                )
                return response.json()
        
        elif resource_name == "ollama":
            # Query Ollama (Mistral)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{resource['url']}/api/generate",
                    json=query
                )
                return response.json()
        
        else:
            return {"error": f"Query not supported for {resource_name}"}
    
    async def _broadcast(self, message: Dict):
        """Broadcast message to all connected WebSocket clients."""
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                self.websocket_connections.remove(websocket)
    
    async def start(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the MCP server."""
        import uvicorn
        
        logger.info(f"Starting MCP Server on {host}:{port}")
        
        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        await server.start()
    
    async def register_agent(self, agent_id: str, agent_data: Dict):
        """Register an agent with the MCP server."""
        self.agents[agent_id] = agent_data
        logger.info(f"Registered agent: {agent_id}")
        
        await self._broadcast({
            "type": "agent_registered",
            "data": agent_data
        })
    
    async def register_tool(self, tool_name: str, tool_data: Dict):
        """Register a tool with the MCP server."""
        self.tools[tool_name] = tool_data
        logger.info(f"Registered tool: {tool_name}")
    
    async def execute_analysis(self, analysis_type: str, data: Dict) -> Dict:
        """Execute an analysis using the appropriate agent."""
        endpoints = {
            "spectral": "/analysis/spectral",
            "metadata": "/analysis/metadata",
            "calibration": "/analysis/calibration"
        }
        
        if analysis_type not in endpoints:
            raise ValueError(f"Unknown analysis type: {analysis_type}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.crewai_url}{endpoints[analysis_type]}",
                    json=data
                )
                return response.json()
        except Exception as e:
            logger.error(f"Error executing analysis: {e}")
            raise


# Pydantic models for request/response validation
class AgentRegistration(BaseModel):
    id: str
    name: str
    description: str
    capabilities: List[str]
    version: str = "1.0.0"


class ToolRegistration(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    version: str = "1.0.0"


class TaskExecution(BaseModel):
    agent_id: str
    task: str
    parameters: Dict[str, Any] = {}


class AnalysisRequest(BaseModel):
    data: Dict[str, Any]
    parameters: Dict[str, Any] = {}


# Create MCP server instance
mcp_server = MCPServer()

# For running as standalone server
if __name__ == "__main__":
    import asyncio
    
    async def main():
        server = MCPServer()
        await server.start()
    
    asyncio.run(main())
