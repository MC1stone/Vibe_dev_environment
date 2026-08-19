"""
Backend Skills Module

Specialized skills for backend development agents.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json


class BackendSkillType(Enum):
    """Backend skill types"""
    API_DESIGN = "api_design"
    AUTHENTICATION = "authentication"
    DATABASE_INTEGRATION = "database_integration"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    SECURITY = "security"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    DEPLOYMENT = "deployment"


@dataclass
class BackendSkill:
    """Represents a backend development skill"""
    skill_id: str
    name: str
    skill_type: BackendSkillType
    description: str
    difficulty: str  # "beginner", "intermediate", "advanced"
    technologies: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.difficulty not in ["beginner", "intermediate", "advanced"]:
            raise ValueError("Difficulty must be beginner, intermediate, or advanced")


class BackendSkills:
    """
    Backend Skills Collection
    
    This class contains all specialized skills for backend development.
    """
    
    def __init__(self):
        self.skills: Dict[str, BackendSkill] = {}
        self._initialize_skills()
    
    def _initialize_skills(self) -> None:
        """Initialize all backend skills"""
        
        # API Design Skills
        self.skills["rest_api_design"] = BackendSkill(
            skill_id="rest_api_design",
            name="REST API Design",
            skill_type=BackendSkillType.API_DESIGN,
            description="Design RESTful APIs following best practices and standards",
            difficulty="intermediate",
            technologies=["FastAPI", "Flask", "Django", "Express", "Spring Boot"],
            dependencies=["requirements_analysis", "architecture_design"],
            examples=[
                "Design a CRUD API for a user management system",
                "Create a RESTful API with proper HTTP methods and status codes",
                "Implement versioning for API endpoints"
            ],
            best_practices=[
                "Use proper HTTP methods (GET, POST, PUT, DELETE)",
                "Return appropriate HTTP status codes",
                "Implement consistent naming conventions",
                "Use pagination for large datasets",
                "Document all endpoints with OpenAPI/Swagger",
                "Implement proper error handling",
                "Use query parameters for filtering and sorting"
            ]
        )
        
        self.skills["graphql_api_design"] = BackendSkill(
            skill_id="graphql_api_design",
            name="GraphQL API Design",
            skill_type=BackendSkillType.API_DESIGN,
            description="Design GraphQL APIs with efficient queries and mutations",
            difficulty="intermediate",
            technologies=["GraphQL", "Apollo Server", "Hasura", "Graphene"],
            dependencies=["schema_design", "data_modeling"],
            examples=[
                "Design a GraphQL schema for a blog platform",
                "Implement complex queries with nested relationships",
                "Optimize GraphQL queries to avoid N+1 problems"
            ],
            best_practices=[
                "Design schemas based on business requirements",
                "Use proper typing for all fields",
                "Implement query complexity analysis",
                "Use DataLoader for batch loading",
                "Implement proper error handling",
                "Add rate limiting to prevent abuse"
            ]
        )
        
        # Authentication Skills
        self.skills["jwt_authentication"] = BackendSkill(
            skill_id="jwt_authentication",
            name="JWT Authentication",
            skill_type=BackendSkillType.AUTHENTICATION,
            description="Implement JSON Web Token (JWT) based authentication",
            difficulty="intermediate",
            technologies=["JWT", "PyJWT", "jsonwebtoken", "Passport.js"],
            dependencies=["security_basics", "database_integration"],
            examples=[
                "Implement JWT login and token generation",
                "Create middleware for JWT verification",
                "Implement token refresh functionality"
            ],
            best_practices=[
                "Use strong signing algorithms (HS256, RS256)",
                "Set appropriate token expiration times",
                "Store tokens securely (HttpOnly, Secure cookies)",
                "Implement token blacklisting for logout",
                "Use refresh tokens for long-lived sessions",
                "Validate token claims properly"
            ]
        )
        
        self.skills["oauth2_implementation"] = BackendSkill(
            skill_id="oauth2_implementation",
            name="OAuth 2.0 Implementation",
            skill_type=BackendSkillType.AUTHENTICATION,
            description="Implement OAuth 2.0 authentication with various providers",
            difficulty="advanced",
            technologies=["OAuth 2.0", "OpenID Connect", "Auth0", "Okta", "Keycloak"],
            dependencies=["api_integration", "security_basics"],
            examples=[
                "Implement Google OAuth login",
                "Create a multi-provider OAuth system",
                "Implement token-based API authentication"
            ],
            best_practices=[
                "Use established OAuth libraries",
                "Implement proper PKCE flow for web apps",
                "Store client secrets securely",
                "Validate state parameters to prevent CSRF",
                "Use short-lived access tokens",
                "Implement proper token storage"
            ]
        )
        
        # Database Integration Skills
        self.skills["sql_database_integration"] = BackendSkill(
            skill_id="sql_database_integration",
            name="SQL Database Integration",
            skill_type=BackendSkillType.DATABASE_INTEGRATION,
            description="Integrate with SQL databases (PostgreSQL, MySQL, etc.)",
            difficulty="intermediate",
            technologies=["PostgreSQL", "MySQL", "SQLite", "SQLAlchemy", "TypeORM", "Prisma"],
            dependencies=["sql_basics", "orm_usage"],
            examples=[
                "Create database models and migrations",
                "Implement CRUD operations with SQL",
                "Optimize database queries"
            ],
            best_practices=[
                "Use connection pooling for better performance",
                "Implement proper transaction management",
                "Use prepared statements to prevent SQL injection",
                "Implement proper error handling for database operations",
                "Use migrations for schema changes",
                "Implement database indexing for performance"
            ]
        )
        
        self.skills["nosql_database_integration"] = BackendSkill(
            skill_id="nosql_database_integration",
            name="NoSQL Database Integration",
            skill_type=BackendSkillType.DATABASE_INTEGRATION,
            description="Integrate with NoSQL databases (MongoDB, Redis, etc.)",
            difficulty="intermediate",
            technologies=["MongoDB", "Redis", "Cassandra", "Firebase", "DynamoDB"],
            dependencies=["data_modeling", "nosql_basics"],
            examples=[
                "Design document schemas for MongoDB",
                "Implement caching with Redis",
                "Create data access layers for NoSQL databases"
            ],
            best_practices=[
                "Design schemas based on query patterns",
                "Use appropriate data types for fields",
                "Implement proper indexing for performance",
                "Handle connection errors gracefully",
                "Use connection pooling",
                "Implement proper data validation"
            ]
        )
        
        # Performance Optimization Skills
        self.skills["caching_implementation"] = BackendSkill(
            skill_id="caching_implementation",
            name="Caching Implementation",
            skill_type=BackendSkillType.PERFORMANCE_OPTIMIZATION,
            description="Implement caching strategies for better performance",
            difficulty="intermediate",
            technologies=["Redis", "Memcached", "Cache-Control", "ETag"],
            dependencies=["performance_analysis", "database_integration"],
            examples=[
                "Implement Redis caching for API responses",
                "Create a multi-level caching strategy",
                "Implement cache invalidation logic"
            ],
            best_practices=[
                "Use appropriate cache keys",
                "Set proper TTL (Time To Live) values",
                "Implement cache invalidation for data changes",
                "Use cache-aside pattern for most use cases",
                "Monitor cache hit/miss ratios",
                "Consider cache warming for critical data"
            ]
        )
        
        self.skills["query_optimization"] = BackendSkill(
            skill_id="query_optimization",
            name="Query Optimization",
            skill_type=BackendSkillType.PERFORMANCE_OPTIMIZATION,
            description="Optimize database queries for better performance",
            difficulty="advanced",
            technologies=["SQL", "ORM", "Indexing", "Query Planning"],
            dependencies=["sql_basics", "database_integration"],
            examples=[
                "Optimize slow SQL queries",
                "Implement proper indexing",
                "Use query explain to analyze performance"
            ],
            best_practices=[
                "Use EXPLAIN to analyze query plans",
                "Add indexes on frequently queried columns",
                "Avoid SELECT * - specify only needed columns",
                "Use JOINs instead of subqueries when appropriate",
                "Implement pagination for large result sets",
                "Use query caching for repeated queries"
            ]
        )
        
        # Security Skills
        self.skills["api_security"] = BackendSkill(
            skill_id="api_security",
            name="API Security",
            skill_type=BackendSkillType.SECURITY,
            description="Implement security best practices for APIs",
            difficulty="advanced",
            technologies=["HTTPS", "CORS", "CSRF", "Rate Limiting", "Input Validation"],
            dependencies=["security_basics", "authentication"],
            examples=[
                "Implement HTTPS for all API endpoints",
                "Add rate limiting to prevent abuse",
                "Implement proper CORS configuration"
            ],
            best_practices=[
                "Always use HTTPS in production",
                "Implement proper CORS headers",
                "Validate all input data",
                "Sanitize output to prevent XSS",
                "Implement rate limiting",
                "Use security headers (HSTS, X-Frame-Options, etc.)",
                "Implement proper authentication and authorization"
            ]
        )
        
        self.skills["data_validation"] = BackendSkill(
            skill_id="data_validation",
            name="Data Validation",
            skill_type=BackendSkillType.SECURITY,
            description="Validate and sanitize all input data",
            difficulty="intermediate",
            technologies=["Pydantic", "Joi", "Zod", "Validator.js"],
            dependencies=["security_basics"],
            examples=[
                "Validate user input in API endpoints",
                "Implement form validation",
                "Sanitize database inputs"
            ],
            best_practices=[
                "Validate data on both client and server",
                "Use allowlists instead of denylists",
                "Validate data types and formats",
                "Implement proper error messages",
                "Sanitize data before processing",
                "Use established validation libraries"
            ]
        )
        
        # Testing Skills
        self.skills["unit_testing"] = BackendSkill(
            skill_id="unit_testing",
            name="Unit Testing",
            skill_type=BackendSkillType.TESTING,
            description="Write and execute unit tests for backend code",
            difficulty="intermediate",
            technologies=["pytest", "Jest", "JUnit", "Mocha", "unittest"],
            dependencies=["testing_basics"],
            examples=[
                "Write unit tests for a service class",
                "Implement test cases for utility functions",
                "Mock dependencies in unit tests"
            ],
            best_practices=[
                "Test one thing per test case",
                "Use descriptive test names",
                "Mock external dependencies",
                "Test both happy paths and error cases",
                "Keep tests fast and isolated",
                "Use test fixtures for common setup"
            ]
        )
        
        self.skills["integration_testing"] = BackendSkill(
            skill_id="integration_testing",
            name="Integration Testing",
            skill_type=BackendSkillType.TESTING,
            description="Test integration between different components and services",
            difficulty="intermediate",
            technologies=["pytest", "Jest", "Supertest", "Postman", "Newman"],
            dependencies=["unit_testing", "api_design"],
            examples=[
                "Test API endpoint integrations",
                "Test database integration",
                "Test service-to-service communication"
            ],
            best_practices=[
                "Test real interactions between components",
                "Use test databases for integration tests",
                "Test error handling and edge cases",
                "Clean up test data after execution",
                "Use realistic test data",
                "Test performance under load"
            ]
        )
        
        # Architecture Skills
        self.skills["microservices_architecture"] = BackendSkill(
            skill_id="microservices_architecture",
            name="Microservices Architecture",
            skill_type=BackendSkillType.ARCHITECTURE,
            description="Design and implement microservices architecture",
            difficulty="advanced",
            technologies=["Docker", "Kubernetes", "Service Mesh", "API Gateway"],
            dependencies=["distributed_systems", "api_design"],
            examples=[
                "Design a microservices-based application",
                "Implement service communication patterns",
                "Create a service discovery mechanism"
            ],
            best_practices=[
                "Design services around business capabilities",
                "Keep services loosely coupled",
                "Use appropriate communication patterns (sync/async)",
                "Implement proper service discovery",
                "Use API Gateway for routing and load balancing",
                "Implement centralized logging and monitoring"
            ]
        )
        
        self.skills["serverless_architecture"] = BackendSkill(
            skill_id="serverless_architecture",
            name="Serverless Architecture",
            skill_type=BackendSkillType.ARCHITECTURE,
            description="Design and implement serverless applications",
            difficulty="advanced",
            technologies=["AWS Lambda", "Azure Functions", "Google Cloud Functions", "Serverless Framework"],
            dependencies=["cloud_computing", "event_driven_architecture"],
            examples=[
                "Create a serverless API with AWS Lambda",
                "Implement event-driven serverless functions",
                "Design a serverless data processing pipeline"
            ],
            best_practices=[
                "Design for stateless execution",
                "Use appropriate trigger types",
                "Implement proper error handling",
                "Optimize function execution time",
                "Use environment variables for configuration",
                "Implement proper logging and monitoring"
            ]
        )
        
        # Deployment Skills
        self.skills["containerization"] = BackendSkill(
            skill_id="containerization",
            name="Containerization",
            skill_type=BackendSkillType.DEPLOYMENT,
            description="Containerize applications using Docker",
            difficulty="intermediate",
            technologies=["Docker", "Docker Compose", "Containerd"],
            dependencies=["linux_basics", "networking_basics"],
            examples=[
                "Create a Dockerfile for a Python application",
                "Set up Docker Compose for multi-container applications",
                "Optimize Docker images for production"
            ],
            best_practices=[
                "Use minimal base images",
                "Multi-stage builds for production",
                "Use .dockerignore to exclude unnecessary files",
                "Set appropriate resource limits",
                "Use environment variables for configuration",
                "Implement health checks"
            ]
        )
        
        self.skills["ci_cd_pipeline"] = BackendSkill(
            skill_id="ci_cd_pipeline",
            name="CI/CD Pipeline",
            skill_type=BackendSkillType.DEPLOYMENT,
            description="Create and manage CI/CD pipelines",
            difficulty="intermediate",
            technologies=["GitHub Actions", "GitLab CI", "Jenkins", "CircleCI", "Travis CI"],
            dependencies=["version_control", "testing"],
            examples=[
                "Create a GitHub Actions workflow",
                "Set up automated testing in CI pipeline",
                "Implement deployment pipeline"
            ],
            best_practices=[
                "Automate testing in CI pipeline",
                "Implement proper build caching",
                "Use environment-specific configurations",
                "Implement rollback mechanisms",
                "Monitor pipeline performance",
                "Secure pipeline with proper permissions"
            ]
        )
    
    def get_skill(self, skill_id: str) -> Optional[BackendSkill]:
        """Get a specific skill by ID"""
        return self.skills.get(skill_id)
    
    def get_skills_by_type(self, skill_type: BackendSkillType) -> List[BackendSkill]:
        """Get all skills of a specific type"""
        return [skill for skill in self.skills.values() if skill.skill_type == skill_type]
    
    def get_skills_by_technology(self, technology: str) -> List[BackendSkill]:
        """Get all skills that use a specific technology"""
        return [skill for skill in self.skills.values() if technology in skill.technologies]
    
    def get_skills_by_difficulty(self, difficulty: str) -> List[BackendSkill]:
        """Get all skills of a specific difficulty level"""
        return [skill for skill in self.skills.values() if skill.difficulty == difficulty]
    
    def search_skills(self, query: str) -> List[BackendSkill]:
        """Search skills by name or description"""
        query_lower = query.lower()
        return [
            skill for skill in self.skills.values()
            if query_lower in skill.name.lower() or query_lower in skill.description.lower()
        ]
    
    def list_all_skills(self) -> List[Dict[str, Any]]:
        """List all available skills"""
        return [
            {
                "skill_id": skill.skill_id,
                "name": skill.name,
                "type": skill.skill_type.value,
                "description": skill.description,
                "difficulty": skill.difficulty,
                "technologies": skill.technologies
            }
            for skill in self.skills.values()
        ]
    
    def get_skill_statistics(self) -> Dict[str, Any]:
        """Get statistics about available skills"""
        statistics = {
            "total_skills": len(self.skills),
            "by_type": {},
            "by_difficulty": {},
            "by_technology": {}
        }
        
        # Count by type
        for skill_type in BackendSkillType:
            count = len(self.get_skills_by_type(skill_type))
            if count > 0:
                statistics["by_type"][skill_type.value] = count
        
        # Count by difficulty
        for difficulty in ["beginner", "intermediate", "advanced"]:
            count = len(self.get_skills_by_difficulty(difficulty))
            if count > 0:
                statistics["by_difficulty"][difficulty] = count
        
        # Count by technology
        all_technologies = set()
        for skill in self.skills.values():
            for tech in skill.technologies:
                all_technologies.add(tech)
        
        for tech in all_technologies:
            count = len(self.get_skills_by_technology(tech))
            statistics["by_technology"][tech] = count
        
        return statistics
