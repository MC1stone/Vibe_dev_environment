"""
Backend Agent - Specialist for Backend Development

Responsibilities:
- API design and implementation
- Server architecture
- Database integration
- Authentication and authorization
- Performance optimization
- Microservices architecture
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio


class BackendTechnology(Enum):
    """Supported backend technologies"""
    PYTHON_FASTAPI = "python_fastapi"
    PYTHON_FLASK = "python_flask"
    PYTHON_DJANGO = "python_django"
    NODEJS_EXPRESS = "nodejs_express"
    NODEJS_NESTJS = "nodejs_nestjs"
    JAVA_SPRING = "java_spring"
    GO_GIN = "go_gin"
    RUST_ACTIX = "rust_actix"
    GRAPHQL_APOLLO = "graphql_apollo"


class BackendArchitecture(Enum):
    """Backend architecture patterns"""
    MONOLITHIC = "monolithic"
    MICROSERVICES = "microservices"
    SERVERLESS = "serverless"
    EVENT_DRIVEN = "event_driven"
    CQRS = "cqrs"


@dataclass
class BackendSkill:
    """Represents a backend development skill"""
    name: str
    description: str
    technology: BackendTechnology
    difficulty: str  # "beginner", "intermediate", "advanced"
    dependencies: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.difficulty not in ["beginner", "intermediate", "advanced"]:
            raise ValueError("Difficulty must be beginner, intermediate, or advanced")


@dataclass
class APIEndpoint:
    """Represents an API endpoint specification"""
    path: str
    method: str  # "GET", "POST", "PUT", "DELETE", "PATCH"
    description: str
    parameters: Dict[str, str] = field(default_factory=dict)
    request_schema: Optional[Dict] = None
    response_schema: Optional[Dict] = None
    authentication_required: bool = False
    rate_limit: Optional[int] = None


@dataclass
class BackendAgent:
    """
    Backend Development Specialist Agent
    
    This agent specializes in backend development, API design, and server architecture.
    It can work with various backend technologies and architectural patterns.
    """
    
    agent_id: str = "backend_agent_001"
    name: str = "Backend Specialist"
    description: str = "Expert in backend development, API design, and server architecture"
    version: str = "1.0.0"
    
    # Agent capabilities
    supported_technologies: List[BackendTechnology] = field(default_factory=lambda: [
        BackendTechnology.PYTHON_FASTAPI,
        BackendTechnology.PYTHON_FLASK,
        BackendTechnology.NODEJS_EXPRESS,
        BackendTechnology.GO_GIN,
    ])
    
    supported_architectures: List[BackendArchitecture] = field(default_factory=lambda: [
        BackendArchitecture.MONOLITHIC,
        BackendArchitecture.MICROSERVICES,
        BackendArchitecture.SERVERLESS,
    ])
    
    # Agent skills
    skills: Dict[str, BackendSkill] = field(default_factory=dict)
    
    # Current project state
    current_project: Optional[str] = None
    current_technology: Optional[BackendTechnology] = None
    current_architecture: Optional[BackendArchitecture] = None
    
    # API endpoints being developed
    api_endpoints: Dict[str, APIEndpoint] = field(default_factory=dict)
    
    # Database schemas
    database_schemas: Dict[str, Dict] = field(default_factory=dict)
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the agent with default skills"""
        self._initialize_skills()
    
    def _initialize_skills(self) -> None:
        """Initialize the agent's skill set"""
        self.skills = {
            "api_design": BackendSkill(
                name="API Design",
                description="Design RESTful and GraphQL APIs with best practices",
                technology=BackendTechnology.PYTHON_FASTAPI,
                difficulty="intermediate",
                dependencies=["requirements_analysis", "architecture_design"]
            ),
            "authentication": BackendSkill(
                name="Authentication",
                description="Implement JWT, OAuth2, and session-based authentication",
                technology=BackendTechnology.PYTHON_FASTAPI,
                difficulty="intermediate",
                dependencies=["security_basics", "database_integration"]
            ),
            "database_integration": BackendSkill(
                name="Database Integration",
                description="Integrate with PostgreSQL, MongoDB, and other databases",
                technology=BackendTechnology.PYTHON_FASTAPI,
                difficulty="intermediate",
                dependencies=["sql_basics", "orm_usage"]
            ),
            "performance_optimization": BackendSkill(
                name="Performance Optimization",
                description="Optimize backend performance with caching, indexing, and query optimization",
                technology=BackendTechnology.PYTHON_FASTAPI,
                difficulty="advanced",
                dependencies=["profiling", "caching_strategies"]
            ),
            "microservices_design": BackendSkill(
                name="Microservices Design",
                description="Design and implement microservices architecture",
                technology=BackendTechnology.NODEJS_EXPRESS,
                difficulty="advanced",
                dependencies=["api_design", "containerization"]
            ),
            "testing": BackendSkill(
                name="Backend Testing",
                description="Write unit, integration, and end-to-end tests",
                technology=BackendTechnology.PYTHON_FASTAPI,
                difficulty="intermediate",
                dependencies=["testing_frameworks", "mocking"]
            ),
            "security": BackendSkill(
                name="Backend Security",
                description="Implement security best practices and vulnerability prevention",
                technology=BackendTechnology.PYTHON_FASTAPI,
                difficulty="advanced",
                dependencies=["authentication", "input_validation"]
            ),
            "documentation": BackendSkill(
                name="API Documentation",
                description="Generate comprehensive API documentation",
                technology=BackendTechnology.PYTHON_FASTAPI,
                difficulty="beginner",
                dependencies=["api_design"]
            ),
        }
    
    async def design_api(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Design an API based on requirements
        
        Args:
            requirements: Dictionary containing API requirements
            
        Returns:
            Dictionary with API design specification
        """
        print(f"🎯 {self.name}: Designing API based on requirements")
        
        # Extract requirements
        api_name = requirements.get("name", "Unnamed API")
        description = requirements.get("description", "")
        endpoints = requirements.get("endpoints", [])
        technology = requirements.get("technology", BackendTechnology.PYTHON_FASTAPI.value)
        
        # Validate technology
        try:
            tech = BackendTechnology(technology)
        except ValueError:
            tech = BackendTechnology.PYTHON_FASTAPI
            print(f"⚠️  Technology {technology} not supported, defaulting to FastAPI")
        
        self.current_technology = tech
        
        # Design endpoints
        api_design = {
            "name": api_name,
            "description": description,
            "technology": tech.value,
            "version": "1.0.0",
            "endpoints": [],
            "authentication": requirements.get("authentication", False),
            "rate_limiting": requirements.get("rate_limiting", None),
            "cors": requirements.get("cors", {"origins": ["*"]}),
        }
        
        # Create endpoints from requirements
        for endpoint_req in endpoints:
            endpoint = APIEndpoint(
                path=endpoint_req.get("path", "/"),
                method=endpoint_req.get("method", "GET").upper(),
                description=endpoint_req.get("description", ""),
                parameters=endpoint_req.get("parameters", {}),
                request_schema=endpoint_req.get("request_schema"),
                response_schema=endpoint_req.get("response_schema"),
                authentication_required=endpoint_req.get("authentication", False),
                rate_limit=endpoint_req.get("rate_limit")
            )
            
            self.api_endpoints[endpoint.path] = endpoint
            
            api_design["endpoints"].append({
                "path": endpoint.path,
                "method": endpoint.method,
                "description": endpoint.description,
                "parameters": endpoint.parameters,
                "authentication_required": endpoint.authentication_required,
            })
        
        print(f"✅ {self.name}: API design completed with {len(api_design['endpoints'])} endpoints")
        return api_design
    
    async def implement_endpoint(self, endpoint_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement a single API endpoint
        
        Args:
            endpoint_spec: Endpoint specification
            
        Returns:
            Dictionary with implementation details
        """
        print(f"🔨 {self.name}: Implementing endpoint {endpoint_spec.get('path', '/')}")
        
        path = endpoint_spec.get("path", "/")
        method = endpoint_spec.get("method", "GET").upper()
        
        # Create endpoint object
        endpoint = APIEndpoint(
            path=path,
            method=method,
            description=endpoint_spec.get("description", ""),
            parameters=endpoint_spec.get("parameters", {}),
            request_schema=endpoint_spec.get("request_schema"),
            response_schema=endpoint_spec.get("response_schema"),
            authentication_required=endpoint_spec.get("authentication", False),
            rate_limit=endpoint_spec.get("rate_limit")
        )
        
        self.api_endpoints[path] = endpoint
        
        # Generate implementation code based on technology
        if self.current_technology == BackendTechnology.PYTHON_FASTAPI:
            code = self._generate_fastapi_endpoint(endpoint)
        elif self.current_technology == BackendTechnology.NODEJS_EXPRESS:
            code = self._generate_express_endpoint(endpoint)
        else:
            code = self._generate_generic_endpoint(endpoint)
        
        implementation = {
            "endpoint": {
                "path": path,
                "method": method,
                "description": endpoint.description,
            },
            "code": code,
            "status": "implemented",
            "technology": self.current_technology.value if self.current_technology else "unknown"
        }
        
        print(f"✅ {self.name}: Endpoint {path} implemented")
        return implementation
    
    def _generate_fastapi_endpoint(self, endpoint: APIEndpoint) -> str:
        """Generate FastAPI endpoint code"""
        code = f'''from fastapi import FastAPI, HTTPException, Request, Depends
from typing import Optional, Dict, Any
from pydantic import BaseModel

app = FastAPI()


class RequestModel(BaseModel):
    """Request model for {endpoint.path}"""
    pass  # Add your request schema here


class ResponseModel(BaseModel):
    """Response model for {endpoint.path}"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


@app.{endpoint.method.lower()}("{endpoint.path}")
async def {endpoint.path.replace('/', '_').replace('-', '_')}_endpoint(
    request: Request,
    params: Optional[Dict[str, Any]] = None
):
    """
    {endpoint.description}
    
    Parameters:
        {json.dumps(endpoint.parameters, indent=4)}
    """
    try:
        # TODO: Implement endpoint logic
        result = {{"message": "Endpoint implemented", "path": "{endpoint.path}"}}
        
        return ResponseModel(
            success=True,
            data=result,
            message="Request processed successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''
        return code
    
    def _generate_express_endpoint(self, endpoint: APIEndpoint) -> str:
        """Generate Express.js endpoint code"""
        code = f'''const express = require('express');
const router = express.Router();

/**
 * {endpoint.description}
 * 
 * Parameters: {JSON.stringify(endpoint.parameters, null, 2)}
 */
router.{endpoint.method.lower()}("{endpoint.path}", async (req, res) => {{
    try {{
        // TODO: Implement endpoint logic
        const result = {{ message: "Endpoint implemented", path: "{endpoint.path}" }};
        
        res.status(200).json({{
            success: true,
            data: result,
            message: "Request processed successfully"
        }});
    }} catch (error) {{
        console.error("Error in {endpoint.path}:", error);
        res.status(500).json({{
            success: false,
            error: error.message
        }});
    }}
}});

module.exports = router;
'''
        return code
    
    def _generate_generic_endpoint(self, endpoint: APIEndpoint) -> str:
        """Generate generic endpoint pseudocode"""
        code = f"""# Endpoint: {endpoint.method} {endpoint.path}
# Description: {endpoint.description}
# Parameters: {json.dumps(endpoint.parameters, indent=2)}

# TODO: Implement endpoint logic
# - Validate input parameters
# - Process request
# - Return appropriate response

# Example response structure:
{{
    "success": True,
    "data": {{}},
    "message": "Request processed successfully"
}}
"""
        return code
    
    async def design_database_schema(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Design a database schema based on requirements
        
        Args:
            requirements: Database requirements
            
        Returns:
            Dictionary with schema design
        """
        print(f"🗄️  {self.name}: Designing database schema")
        
        schema_name = requirements.get("name", "main_schema")
        tables = requirements.get("tables", [])
        
        schema = {
            "name": schema_name,
            "tables": {},
            "relationships": [],
            "indexes": [],
            "constraints": []
        }
        
        for table_req in tables:
            table_name = table_req.get("name", "unnamed_table")
            columns = table_req.get("columns", [])
            
            table_schema = {
                "name": table_name,
                "columns": {},
                "primary_key": table_req.get("primary_key", "id"),
                "foreign_keys": table_req.get("foreign_keys", []),
                "indexes": table_req.get("indexes", []),
                "constraints": table_req.get("constraints", [])
            }
            
            for column in columns:
                col_name = column.get("name", "unnamed_column")
                col_type = column.get("type", "TEXT")
                col_nullable = column.get("nullable", True)
                col_default = column.get("default", None)
                
                table_schema["columns"][col_name] = {
                    "type": col_type,
                    "nullable": col_nullable,
                    "default": col_default,
                    "description": column.get("description", "")
                }
            
            schema["tables"][table_name] = table_schema
        
        self.database_schemas[schema_name] = schema
        print(f"✅ {self.name}: Database schema '{schema_name}' designed with {len(schema['tables'])} tables")
        
        return schema
    
    async def optimize_performance(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze and optimize backend performance
        
        Args:
            analysis: Performance analysis data
            
        Returns:
            Dictionary with optimization recommendations
        """
        print(f"⚡ {self.name}: Analyzing and optimizing performance")
        
        recommendations = {
            "caching": [],
            "database": [],
            "code": [],
            "infrastructure": []
        }
        
        # Analyze slow endpoints
        slow_endpoints = analysis.get("slow_endpoints", [])
        for endpoint in slow_endpoints:
            path = endpoint.get("path", "/")
            avg_response_time = endpoint.get("avg_response_time", 0)
            
            if avg_response_time > 1000:  # > 1 second
                recommendations["caching"].append({
                    "action": "Add caching",
                    "endpoint": path,
                    "reason": f"Average response time: {avg_response_time}ms",
                    "suggestion": "Implement Redis caching for frequent queries"
                })
        
        # Analyze database queries
        slow_queries = analysis.get("slow_queries", [])
        for query in slow_queries:
            execution_time = query.get("execution_time", 0)
            query_text = query.get("query", "")
            
            if execution_time > 500:  # > 500ms
                recommendations["database"].append({
                    "action": "Optimize query",
                    "query": query_text[:100] + "...",
                    "reason": f"Execution time: {execution_time}ms",
                    "suggestions": [
                        "Add indexes on frequently queried columns",
                        "Consider query rewriting",
                        "Use pagination for large result sets"
                    ]
                })
        
        self.performance_metrics["optimization_recommendations"] = recommendations
        print(f"✅ {self.name}: Performance analysis completed with {len(recommendations['caching']) + len(recommendations['database'])} recommendations")
        
        return recommendations
    
    async def generate_documentation(self, api_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive API documentation
        
        Args:
            api_spec: API specification
            
        Returns:
            Dictionary with documentation
        """
        print(f"📚 {self.name}: Generating API documentation")
        
        documentation = {
            "title": api_spec.get("name", "API Documentation"),
            "description": api_spec.get("description", ""),
            "version": api_spec.get("version", "1.0.0"),
            "base_url": api_spec.get("base_url", "http://localhost:8000"),
            "endpoints": [],
            "authentication": api_spec.get("authentication", {}),
            "examples": {},
            "error_codes": {}
        }
        
        # Generate endpoint documentation
        for endpoint in api_spec.get("endpoints", []):
            endpoint_doc = {
                "path": endpoint.get("path", "/"),
                "method": endpoint.get("method", "GET"),
                "description": endpoint.get("description", ""),
                "parameters": endpoint.get("parameters", {}),
                "request_example": self._generate_request_example(endpoint),
                "response_example": self._generate_response_example(endpoint),
                "authentication_required": endpoint.get("authentication_required", False)
            }
            documentation["endpoints"].append(endpoint_doc)
        
        # Add common error codes
        documentation["error_codes"] = {
            "400": "Bad Request - Invalid input parameters",
            "401": "Unauthorized - Authentication required",
            "403": "Forbidden - Insufficient permissions",
            "404": "Not Found - Resource not found",
            "500": "Internal Server Error - Server-side error"
        }
        
        print(f"✅ {self.name}: Documentation generated for {len(documentation['endpoints'])} endpoints")
        return documentation
    
    def _generate_request_example(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """Generate request example"""
        method = endpoint.get("method", "GET").upper()
        path = endpoint.get("path", "/")
        parameters = endpoint.get("parameters", {})
        
        if method == "GET":
            return {
                "url": f"{path}?{ '&'.join([f'{k}={v}' for k, v in parameters.items()])}",
                "method": method,
                "headers": {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            }
        else:
            return {
                "url": path,
                "method": method,
                "headers": {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                "body": {"example": "request_data"}
            }
    
    def _generate_response_example(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response example"""
        return {
            "status": 200,
            "content": {
                "success": True,
                "data": {"example": "response_data"},
                "message": "Request processed successfully"
            }
        }
    
    async def validate_architecture(self, architecture_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate backend architecture design
        
        Args:
            architecture_spec: Architecture specification
            
        Returns:
            Dictionary with validation results
        """
        print(f"🏗️  {self.name}: Validating architecture design")
        
        validation = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Check architecture type
        arch_type = architecture_spec.get("type", "monolithic")
        try:
            architecture = BackendArchitecture(arch_type)
            self.current_architecture = architecture
        except ValueError:
            validation["valid"] = False
            validation["errors"].append(f"Unsupported architecture type: {arch_type}")
        
        # Check technology compatibility
        technologies = architecture_spec.get("technologies", [])
        for tech in technologies:
            try:
                BackendTechnology(tech)
            except ValueError:
                validation["warnings"].append(f"Technology {tech} may not be fully supported")
        
        # Check scalability requirements
        expected_load = architecture_spec.get("expected_load", "low")
        if expected_load in ["high", "very_high"] and architecture == BackendArchitecture.MONOLITHIC:
            validation["recommendations"].append(
                "Consider microservices architecture for high load expectations"
            )
        
        print(f"✅ {self.name}: Architecture validation completed")
        return validation
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "current_project": self.current_project,
            "current_technology": self.current_technology.value if self.current_technology else None,
            "current_architecture": self.current_architecture.value if self.current_architecture else None,
            "api_endpoints_count": len(self.api_endpoints),
            "database_schemas_count": len(self.database_schemas),
            "performance_metrics": self.performance_metrics,
            "skills": list(self.skills.keys())
        }
    
    def reset(self) -> None:
        """Reset agent state"""
        self.current_project = None
        self.current_technology = None
        self.current_architecture = None
        self.api_endpoints.clear()
        self.database_schemas.clear()
        self.performance_metrics.clear()
        print(f"🔄 {self.name}: Agent state reset")
