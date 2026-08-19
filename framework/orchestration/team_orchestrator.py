"""
Team Orchestrator - Main Orchestration System

Responsibilities:
- Team initialization and management
- Project execution coordination
- Agent registration and discovery
- Task distribution and monitoring
- Result aggregation
- Error handling and recovery
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
from datetime import datetime


class TeamStatus(Enum):
    """Team status types"""
    IDLE = "idle"
    READY = "ready"
    WORKING = "working"
    BUSY = "busy"
    ERROR = "error"


class ProjectStatus(Enum):
    """Project status types"""
    PLANNED = "planned"
    INITIALIZING = "initializing"
    IN_PROGRESS = "in_progress"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentRegistration:
    """Represents an agent registration"""
    agent_id: str
    agent_type: str
    name: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    status: str = "available"  # "available", "busy", "unavailable"
    registered_at: str = ""
    last_heartbeat: str = ""
    workload: float = 0.0


@dataclass
class Project:
    """Represents a project being executed"""
    project_id: str
    name: str
    description: str = ""
    requirements: Dict[str, Any] = field(default_factory=dict)
    status: ProjectStatus = ProjectStatus.PLANNED
    start_time: str = ""
    end_time: str = ""
    agents_involved: List[str] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class Task:
    """Represents a task to be executed"""
    task_id: str
    name: str
    description: str = ""
    task_type: str = "generic"
    priority: int = 0  # 0-10, higher is more important
    status: str = "pending"  # "pending", "assigned", "in_progress", "completed", "failed"
    assigned_to: Optional[str] = None
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TeamOrchestrator:
    """
    Team Orchestrator
    
    This is the main orchestration system that manages the multi-agent team.
    It coordinates project execution, task distribution, and result aggregation.
    """
    
    orchestrator_id: str = "team_orchestrator_001"
    name: str = "Team Orchestrator"
    description: str = "Main orchestration system for multi-agent team"
    version: str = "1.0.0"
    
    # Team state
    agents: Dict[str, AgentRegistration] = field(default_factory=dict)
    projects: Dict[str, Project] = field(default_factory=dict)
    tasks: Dict[str, Task] = field(default_factory=dict)
    
    # Current state
    current_project: Optional[str] = None
    team_status: TeamStatus = TeamStatus.IDLE
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the orchestrator"""
        self._initialize_config()
    
    def _initialize_config(self) -> None:
        """Initialize with default configuration"""
        self.config = {
            "max_concurrent_projects": 5,
            "max_agents_per_project": 10,
            "task_timeout": 3600,  # 1 hour
            "project_timeout": 86400,  # 24 hours
            "retry_attempts": 3,
            "auto_retry": True,
            "load_balancing": "round_robin",
            "logging": {
                "level": "info",
                "file": "orchestrator.log",
                "console": True
            }
        }
    
    async def initialize_team(self, team_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize the team with a configuration
        
        Args:
            team_config: Team configuration
            
        Returns:
            Dictionary with initialization results
        """
        print(f"🚀 {self.name}: Initializing team")
        
        # Update configuration
        if "config" in team_config:
            self.config.update(team_config["config"])
        
        # Register agents
        agents_config = team_config.get("agents", [])
        for agent_config in agents_config:
            await self.register_agent(agent_config)
        
        # Set team status
        self.team_status = TeamStatus.READY
        
        result = {
            "orchestrator_id": self.orchestrator_id,
            "name": self.name,
            "status": self.team_status.value,
            "agents_registered": len(self.agents),
            "config": self.config,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"✅ {self.name}: Team initialized with {len(self.agents)} agents")
        return result
    
    async def register_agent(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register an agent with the orchestrator
        
        Args:
            agent_config: Agent configuration
            
        Returns:
            Dictionary with registration results
        """
        print(f"👤 {self.name}: Registering agent {agent_config.get('agent_id', 'Unknown')}")
        
        agent_id = agent_config.get("agent_id", f"agent_{len(self.agents) + 1}")
        agent_type = agent_config.get("agent_type", "generic")
        name = agent_config.get("name", "Unknown Agent")
        description = agent_config.get("description", "")
        capabilities = agent_config.get("capabilities", [])
        skills = agent_config.get("skills", [])
        
        # Create agent registration
        agent_registration = AgentRegistration(
            agent_id=agent_id,
            agent_type=agent_type,
            name=name,
            description=description,
            capabilities=capabilities,
            skills=skills,
            status="available",
            registered_at=datetime.now().isoformat(),
            last_heartbeat=datetime.now().isoformat(),
            workload=0.0
        )
        
        self.agents[agent_id] = agent_registration
        
        result = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "name": name,
            "status": "registered",
            "capabilities": capabilities,
            "skills": skills,
            "registered_at": agent_registration.registered_at
        }
        
        print(f"✅ {self.name}: Agent {name} ({agent_id}) registered")
        return result
    
    async def unregister_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Unregister an agent from the orchestrator
        
        Args:
            agent_id: ID of the agent to unregister
            
        Returns:
            Dictionary with unregistration results
        """
        print(f"🔄 {self.name}: Unregistering agent {agent_id}")
        
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent = self.agents[agent_id]
        del self.agents[agent_id]
        
        result = {
            "agent_id": agent_id,
            "name": agent.name,
            "status": "unregistered",
            "unregistered_at": datetime.now().isoformat()
        }
        
        print(f"✅ {self.name}: Agent {agent.name} ({agent_id}) unregistered")
        return result
    
    async def create_project(self, project_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new project
        
        Args:
            project_spec: Project specification
            
        Returns:
            Dictionary with project creation results
        """
        print(f"📁 {self.name}: Creating project {project_spec.get('name', 'Unnamed')}")
        
        project_id = project_spec.get("project_id", f"project_{len(self.projects) + 1}")
        name = project_spec.get("name", "Unnamed Project")
        description = project_spec.get("description", "")
        requirements = project_spec.get("requirements", {})
        
        # Create project
        project = Project(
            project_id=project_id,
            name=name,
            description=description,
            requirements=requirements,
            status=ProjectStatus.PLANNED,
            start_time="",
            end_time="",
            agents_involved=[],
            tasks=[],
            results={},
            errors=[]
        )
        
        self.projects[project_id] = project
        self.current_project = project_id
        
        result = {
            "project_id": project_id,
            "name": name,
            "description": description,
            "requirements": requirements,
            "status": project.status.value,
            "created_at": datetime.now().isoformat()
        }
        
        print(f"✅ {self.name}: Project {name} created with ID {project_id}")
        return result
    
    async def execute_project(self, project_id: str, execution_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a project with the team
        
        Args:
            project_id: ID of the project to execute
            execution_spec: Execution specification
            
        Returns:
            Dictionary with execution results
        """
        print(f"▶️ {self.name}: Executing project {project_id}")
        
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        project = self.projects[project_id]
        
        # Update project status
        project.status = ProjectStatus.INITIALIZING
        project.start_time = datetime.now().isoformat()
        
        # Break down project into tasks
        tasks = await self._break_down_project(project, execution_spec)
        project.tasks = [task.task_id for task in tasks]
        
        # Assign tasks to agents
        assignments = await self._assign_tasks_to_agents(tasks)
        project.agents_involved = list(set(assignments.values()))
        
        # Update project status
        project.status = ProjectStatus.IN_PROGRESS
        
        # Execute tasks
        execution_results = await self._execute_tasks(tasks, assignments)
        
        # Aggregate results
        project.results = self._aggregate_results(execution_results)
        project.errors = [
            error for task_id, result in execution_results.items()
            if result.get("status") == "failed" and result.get("error")
        ]
        
        # Update project status
        if all(result.get("status") == "completed" for result in execution_results.values()):
            project.status = ProjectStatus.COMPLETED
        elif any(result.get("status") == "failed" for result in execution_results.values()):
            project.status = ProjectStatus.FAILED
        else:
            project.status = ProjectStatus.COMPLETING
        
        project.end_time = datetime.now().isoformat()
        
        # Update team status
        if project.status == ProjectStatus.COMPLETED:
            self.team_status = TeamStatus.READY
        elif project.status == ProjectStatus.FAILED:
            self.team_status = TeamStatus.ERROR
        
        result = {
            "project_id": project_id,
            "name": project.name,
            "status": project.status.value,
            "start_time": project.start_time,
            "end_time": project.end_time,
            "agents_involved": project.agents_involved,
            "tasks_executed": len(execution_results),
            "results": project.results,
            "errors": project.errors
        }
        
        print(f"✅ {self.name}: Project {project_id} execution completed with status {project.status.value}")
        return result
    
    async def _break_down_project(self, project: Project, execution_spec: Dict[str, Any]) -> List[Task]:
        """Break down a project into executable tasks"""
        tasks = []
        
        # Extract requirements
        requirements = project.requirements
        
        # Create tasks based on requirements
        if "backend" in requirements:
            backend_tasks = self._create_backend_tasks(requirements["backend"])
            tasks.extend(backend_tasks)
        
        if "frontend" in requirements:
            frontend_tasks = self._create_frontend_tasks(requirements["frontend"])
            tasks.extend(frontend_tasks)
        
        if "data_analysis" in requirements:
            data_tasks = self._create_data_analysis_tasks(requirements["data_analysis"])
            tasks.extend(data_tasks)
        
        if "tools" in requirements:
            tool_tasks = self._create_tool_tasks(requirements["tools"])
            tasks.extend(tool_tasks)
        
        # Add general tasks
        general_tasks = self._create_general_tasks(project, execution_spec)
        tasks.extend(general_tasks)
        
        # Store tasks
        for task in tasks:
            self.tasks[task.task_id] = task
        
        return tasks
    
    def _create_backend_tasks(self, backend_reqs: Dict[str, Any]) -> List[Task]:
        """Create backend-specific tasks"""
        tasks = []
        
        # API Design task
        if backend_reqs.get("api", False):
            task = Task(
                task_id=f"backend_api_design_{len(self.tasks) + 1}",
                name="Design Backend API",
                description="Design RESTful API endpoints based on requirements",
                task_type="backend",
                priority=8,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            tasks.append(task)
        
        # Database Design task
        if backend_reqs.get("database", False):
            task = Task(
                task_id=f"backend_db_design_{len(self.tasks) + 1}",
                name="Design Database Schema",
                description="Design database schema and models",
                task_type="backend",
                priority=9,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            tasks.append(task)
        
        # API Implementation task
        if backend_reqs.get("implementation", False):
            task = Task(
                task_id=f"backend_api_implementation_{len(self.tasks) + 1}",
                name="Implement Backend API",
                description="Implement API endpoints and business logic",
                task_type="backend",
                priority=7,
                status="pending",
                created_at=datetime.now().isoformat(),
                dependencies=[f"backend_api_design_{len(self.tasks)}"] if tasks else []
            )
            tasks.append(task)
        
        # Testing task
        if backend_reqs.get("testing", False):
            task = Task(
                task_id=f"backend_testing_{len(self.tasks) + 1}",
                name="Test Backend Implementation",
                description="Write and execute tests for backend code",
                task_type="backend",
                priority=6,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            tasks.append(task)
        
        return tasks
    
    def _create_frontend_tasks(self, frontend_reqs: Dict[str, Any]) -> List[Task]:
        """Create frontend-specific tasks"""
        tasks = []
        
        # UI Design task
        if frontend_reqs.get("ui_design", False):
            task = Task(
                task_id=f"frontend_ui_design_{len(self.tasks) + 1}",
                name="Design User Interface",
                description="Design UI components and layouts",
                task_type="frontend",
                priority=8,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            tasks.append(task)
        
        # Component Development task
        if frontend_reqs.get("components", False):
            task = Task(
                task_id=f"frontend_components_{len(self.tasks) + 1}",
                name="Develop UI Components",
                description="Develop reusable UI components",
                task_type="frontend",
                priority=7,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            tasks.append(task)
        
        # Page Development task
        if frontend_reqs.get("pages", False):
            task = Task(
                task_id=f"frontend_pages_{len(self.tasks) + 1}",
                name="Develop Application Pages",
                description="Develop application pages and routes",
                task_type="frontend",
                priority=7,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            tasks.append(task)
        
        # Testing task
        if frontend_reqs.get("testing", False):
            task = Task(
                task_id=f"frontend_testing_{len(self.tasks) + 1}",
                name="Test Frontend Implementation",
                description="Write and execute tests for frontend code",
                task_type="frontend",
                priority=6,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            tasks.append(task)
        
        return tasks
    
    def _create_data_analysis_tasks(self, data_reqs: Dict[str, Any]) -> List[Task]:
        """Create data analysis-specific tasks"""
        tasks = []
        
        # Data Loading task
        if data_reqs.get("data_loading", False):
            task = Task(
                task_id=f"data_loading_{len(self.tasks) + 1}",
                name="Load and Prepare Data",
                description="Load data from various sources and prepare for analysis",
                task_type="data_analysis",
                priority=8,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            tasks.append(task)
        
        # EDA task
        if data_reqs.get("eda", False):
            task = Task(
                task_id=f"data_eda_{len(self.tasks) + 1}",
                name="Perform Exploratory Data Analysis",
                description="Perform EDA and generate insights",
                task_type="data_analysis",
                priority=7,
                status="pending",
                created_at=datetime.now().isoformat(),
                dependencies=[f"data_loading_{len(self.tasks)}"] if tasks else []
            )
            tasks.append(task)
        
        # Feature Engineering task
        if data_reqs.get("feature_engineering", False):
            task = Task(
                task_id=f"data_feature_engineering_{len(self.tasks) + 1}",
                name="Feature Engineering",
                description="Create and transform features for modeling",
                task_type="data_analysis",
                priority=7,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            tasks.append(task)
        
        # Model Training task
        if data_reqs.get("model_training", False):
            task = Task(
                task_id=f"data_model_training_{len(self.tasks) + 1}",
                name="Train Machine Learning Model",
                description="Train and evaluate ML models",
                task_type="data_analysis",
                priority=6,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            tasks.append(task)
        
        return tasks
    
    def _create_tool_tasks(self, tool_reqs: List[str]) -> List[Task]:
        """Create tool-specific tasks"""
        tasks = []
        
        for tool in tool_reqs:
            task = Task(
                task_id=f"tool_{tool}_{len(self.tasks) + 1}",
                name=f"Configure {tool}",
                description=f"Set up and configure {tool} for the project",
                task_type="tool",
                priority=5,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            tasks.append(task)
        
        return tasks
    
    def _create_general_tasks(self, project: Project, execution_spec: Dict[str, Any]) -> List[Task]:
        """Create general project tasks"""
        tasks = []
        
        # Project Setup task
        task = Task(
            task_id=f"project_setup_{len(self.tasks) + 1}",
            name="Project Setup",
            description="Set up project structure and configuration",
            task_type="general",
            priority=10,
            status="pending",
            created_at=datetime.now().isoformat()
        )
        tasks.append(task)
        
        # Documentation task
        if execution_spec.get("documentation", True):
            task = Task(
                task_id=f"project_documentation_{len(self.tasks) + 1}",
                name="Project Documentation",
                description="Create and update project documentation",
                task_type="general",
                priority=4,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            tasks.append(task)
        
        # Quality Assurance task
        if execution_spec.get("quality_assurance", True):
            task = Task(
                task_id=f"project_qa_{len(self.tasks) + 1}",
                name="Quality Assurance",
                description="Perform quality checks and validations",
                task_type="quality",
                priority=5,
                status="pending",
                created_at=datetime.now().isoformat()
            )
            tasks.append(task)
        
        return tasks
    
    async def _assign_tasks_to_agents(self, tasks: List[Task]) -> Dict[str, str]:
        """Assign tasks to appropriate agents"""
        assignments = {}
        
        for task in tasks:
            # Find the best agent for this task
            best_agent = self._find_best_agent(task)
            
            if best_agent:
                task.assigned_to = best_agent
                task.status = "assigned"
                assignments[task.task_id] = best_agent
                
                # Update agent workload
                if best_agent in self.agents:
                    self.agents[best_agent].workload += 0.1
                    self.agents[best_agent].status = "busy"
            else:
                task.status = "pending"
                print(f"⚠️  No available agent for task {task.name}")
        
        return assignments
    
    def _find_best_agent(self, task: Task) -> Optional[str]:
        """Find the best agent for a task based on capabilities and workload"""
        best_agent = None
        best_score = -1
        
        for agent_id, agent in self.agents.items():
            if agent.status != "available":
                continue
            
            # Calculate score based on:
            # 1. Capability match (higher is better)
            # 2. Workload (lower is better)
            # 3. Skill match (higher is better)
            
            capability_score = 0
            if task.task_type in agent.capabilities:
                capability_score = 1.0
            elif any(task.task_type in cap for cap in agent.capabilities):
                capability_score = 0.5
            
            workload_score = 1 - agent.workload
            
            skill_score = 0
            if task.task_type in [cap.split('_')[0] for cap in agent.skills]:
                skill_score = 1.0
            elif any(task.task_type in skill for skill in agent.skills):
                skill_score = 0.5
            
            # Weighted score
            score = (capability_score * 0.5) + (workload_score * 0.3) + (skill_score * 0.2)
            
            if score > best_score:
                best_score = score
                best_agent = agent_id
        
        return best_agent
    
    async def _execute_tasks(self, tasks: List[Task], assignments: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """Execute tasks with assigned agents"""
        execution_results = {}
        
        # Simulate task execution (in real implementation, this would call actual agents)
        for task in tasks:
            if task.assigned_to and task.assigned_to in self.agents:
                agent = self.agents[task.assigned_to]
                
                # Simulate execution
                import random
                
                # Higher priority tasks have higher success rate
                success_probability = 0.7 + (task.priority / 20)
                
                if random.random() < success_probability:
                    # Task succeeds
                    task.status = "completed"
                    task.started_at = datetime.now().isoformat()
                    task.completed_at = datetime.now().isoformat()
                    
                    result = {
                        "task_id": task.task_id,
                        "name": task.name,
                        "status": "completed",
                        "assigned_to": task.assigned_to,
                        "started_at": task.started_at,
                        "completed_at": task.completed_at,
                        "result": {
                            "message": f"Task {task.name} completed successfully",
                            "agent": agent.name,
                            "agent_type": agent.agent_type
                        }
                    }
                    
                    # Update agent status
                    agent.workload = max(agent.workload - 0.1, 0)
                    if agent.workload == 0:
                        agent.status = "available"
                else:
                    # Task fails
                    task.status = "failed"
                    task.started_at = datetime.now().isoformat()
                    task.completed_at = datetime.now().isoformat()
                    
                    error = f"Task {task.name} failed - simulated error"
                    task.error = error
                    
                    result = {
                        "task_id": task.task_id,
                        "name": task.name,
                        "status": "failed",
                        "assigned_to": task.assigned_to,
                        "started_at": task.started_at,
                        "completed_at": task.completed_at,
                        "error": error
                    }
                    
                    # Update agent status
                    agent.workload = max(agent.workload - 0.05, 0)
                    if agent.workload == 0:
                        agent.status = "available"
            else:
                # Task not assigned
                result = {
                    "task_id": task.task_id,
                    "name": task.name,
                    "status": "pending",
                    "assigned_to": None,
                    "error": "No agent available for this task"
                }
            
            execution_results[task.task_id] = result
        
        return execution_results
    
    def _aggregate_results(self, execution_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate execution results"""
        aggregated = {
            "total_tasks": len(execution_results),
            "completed": 0,
            "failed": 0,
            "pending": 0,
            "by_type": {},
            "by_agent": {},
            "execution_time": 0.0
        }
        
        for task_id, result in execution_results.items():
            status = result.get("status", "pending")
            
            if status == "completed":
                aggregated["completed"] += 1
            elif status == "failed":
                aggregated["failed"] += 1
            else:
                aggregated["pending"] += 1
            
            # Group by task type
            task_type = result.get("name", "unknown").split()[0].lower()
            if task_type not in aggregated["by_type"]:
                aggregated["by_type"][task_type] = {"completed": 0, "failed": 0, "pending": 0}
            
            if status == "completed":
                aggregated["by_type"][task_type]["completed"] += 1
            elif status == "failed":
                aggregated["by_type"][task_type]["failed"] += 1
            else:
                aggregated["by_type"][task_type]["pending"] += 1
            
            # Group by agent
            agent_id = result.get("assigned_to")
            if agent_id:
                if agent_id not in aggregated["by_agent"]:
                    agent_name = self.agents[agent_id].name if agent_id in self.agents else "Unknown"
                    aggregated["by_agent"][agent_id] = {
                        "name": agent_name,
                        "completed": 0,
                        "failed": 0,
                        "pending": 0
                    }
                
                if status == "completed":
                    aggregated["by_agent"][agent_id]["completed"] += 1
                elif status == "failed":
                    aggregated["by_agent"][agent_id]["failed"] += 1
                else:
                    aggregated["by_agent"][agent_id]["pending"] += 1
        
        return aggregated
    
    async def monitor_project(self, project_id: str) -> Dict[str, Any]:
        """
        Monitor the status of a project
        
        Args:
            project_id: ID of the project to monitor
            
        Returns:
            Dictionary with monitoring results
        """
        print(f"📊 {self.name}: Monitoring project {project_id}")
        
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        project = self.projects[project_id]
        
        # Get task statuses
        task_statuses = {}
        for task_id in project.tasks:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task_statuses[task_id] = {
                    "name": task.name,
                    "status": task.status,
                    "assigned_to": task.assigned_to,
                    "priority": task.priority
                }
        
        # Get agent statuses
        agent_statuses = {}
        for agent_id in project.agents_involved:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                agent_statuses[agent_id] = {
                    "name": agent.name,
                    "status": agent.status,
                    "workload": agent.workload,
                    "agent_type": agent.agent_type
                }
        
        # Calculate progress
        total_tasks = len(project.tasks)
        completed_tasks = len([t for t in project.tasks if t in self.tasks and self.tasks[t].status == "completed"])
        progress = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        result = {
            "project_id": project_id,
            "name": project.name,
            "status": project.status.value,
            "progress": progress,
            "start_time": project.start_time,
            "end_time": project.end_time or "In Progress",
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": len([t for t in project.tasks if t in self.tasks and self.tasks[t].status == "failed"]),
            "pending_tasks": len([t for t in project.tasks if t in self.tasks and self.tasks[t].status == "pending"]),
            "task_statuses": task_statuses,
            "agent_statuses": agent_statuses,
            "results": project.results,
            "errors": project.errors
        }
        
        print(f"✅ {self.name}: Project {project_id} monitoring completed")
        return result
    
    async def get_team_status(self) -> Dict[str, Any]:
        """
        Get the current team status
        
        Returns:
            Dictionary with team status
        """
        # Calculate overall statistics
        total_agents = len(self.agents)
        available_agents = len([a for a in self.agents.values() if a.status == "available"])
        busy_agents = len([a for a in self.agents.values() if a.status == "busy"])
        
        total_projects = len(self.projects)
        completed_projects = len([p for p in self.projects.values() if p.status == ProjectStatus.COMPLETED])
        in_progress_projects = len([p for p in self.projects.values() if p.status == ProjectStatus.IN_PROGRESS])
        
        total_tasks = len(self.tasks)
        completed_tasks = len([t for t in self.tasks.values() if t.status == "completed"])
        failed_tasks = len([t for t in self.tasks.values() if t.status == "failed"])
        
        return {
            "orchestrator_id": self.orchestrator_id,
            "name": self.name,
            "status": self.team_status.value,
            "timestamp": datetime.now().isoformat(),
            "agents": {
                "total": total_agents,
                "available": available_agents,
                "busy": busy_agents,
                "details": {a_id: {"name": a.name, "status": a.status, "workload": a.workload} for a_id, a in self.agents.items()}
            },
            "projects": {
                "total": total_projects,
                "completed": completed_projects,
                "in_progress": in_progress_projects,
                "current_project": self.current_project
            },
            "tasks": {
                "total": total_tasks,
                "completed": completed_tasks,
                "failed": failed_tasks,
                "pending": total_tasks - completed_tasks - failed_tasks
            },
            "config": self.config,
            "performance_metrics": self.performance_metrics
        }
    
    async def shutdown(self) -> Dict[str, Any]:
        """
        Shutdown the orchestrator
        
        Returns:
            Dictionary with shutdown results
        """
        print(f"🛑 {self.name}: Shutting down")
        
        # Update team status
        self.team_status = TeamStatus.IDLE
        
        # Reset current project
        self.current_project = None
        
        result = {
            "orchestrator_id": self.orchestrator_id,
            "name": self.name,
            "status": self.team_status.value,
            "shutdown_at": datetime.now().isoformat(),
            "agents_unregistered": len(self.agents),
            "projects_completed": len([p for p in self.projects.values() if p.status == ProjectStatus.COMPLETED])
        }
        
        print(f"✅ {self.name}: Shutdown completed")
        return result
    
    def reset(self) -> None:
        """Reset orchestrator state"""
        self.agents.clear()
        self.projects.clear()
        self.tasks.clear()
        self.current_project = None
        self.team_status = TeamStatus.IDLE
        self.performance_metrics.clear()
        self._initialize_config()
        print(f"🔄 {self.name}: State reset")
