"""
CrewAI Agent - Specialist for CrewAI Framework

Responsibilities:
- Crew and agent configuration
- Task management
- Tool integration
- Process orchestration
- Result aggregation
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio


class CrewAIRole(Enum):
    """CrewAI role types"""
    RESEARCHER = "researcher"
    WRITER = "writer"
    ANALYST = "analyst"
    DEVELOPER = "developer"
    DESIGNER = "designer"
    TESTER = "tester"
    COORDINATOR = "coordinator"
    CUSTOM = "custom"


class CrewAITaskType(Enum):
    """CrewAI task types"""
    RESEARCH = "research"
    WRITING = "writing"
    ANALYSIS = "analysis"
    CODING = "coding"
    DESIGN = "design"
    TESTING = "testing"
    COORDINATION = "coordination"


@dataclass
class CrewAIAgent:
    """Represents a CrewAI agent"""
    agent_id: str
    role: CrewAIRole
    goal: str
    backstory: str
    verbose: bool = True
    allow_delegation: bool = False
    tools: List[str] = field(default_factory=list)
    memory: bool = True


@dataclass
class CrewAITask:
    """Represents a CrewAI task"""
    task_id: str
    description: str
    agent: str
    expected_output: str
    async_execution: bool = False
    output_file: Optional[str] = None
    human_input: bool = False


@dataclass
class CrewAICrew:
    """Represents a CrewAI crew"""
    crew_id: str
    name: str
    description: str
    agents: List[str] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)
    process: str = "sequential"  # "sequential" or "parallel"
    memory: bool = True
    cache: bool = False
    max_rpm: Optional[int] = None
    share_crew: bool = False


@dataclass
class CrewAIAgent:
    """
    CrewAI Specialist Agent
    
    This agent specializes in CrewAI framework for multi-agent orchestration.
    It can create crews, agents, and tasks for complex workflows.
    """
    
    agent_id: str = "crewai_agent_001"
    name: str = "CrewAI Specialist"
    description: str = "Expert in CrewAI framework for multi-agent orchestration"
    version: str = "1.0.0"
    
    # Agent capabilities
    supported_roles: List[CrewAIRole] = field(default_factory=lambda: [
        CrewAIRole.RESEARCHER,
        CrewAIRole.WRITER,
        CrewAIRole.ANALYST,
        CrewAIRole.DEVELOPER,
        CrewAIRole.DESIGNER,
        CrewAIRole.TESTER,
        CrewAIRole.COORDINATOR,
        CrewAIRole.CUSTOM,
    ])
    
    supported_task_types: List[CrewAITaskType] = field(default_factory=lambda: [
        CrewAITaskType.RESEARCH,
        CrewAITaskType.WRITING,
        CrewAITaskType.ANALYSIS,
        CrewAITaskType.CODING,
        CrewAITaskType.DESIGN,
        CrewAITaskType.TESTING,
        CrewAITaskType.COORDINATION,
    ])
    
    # Agent skills
    skills: Dict[str, str] = field(default_factory=dict)
    
    # Current project state
    current_project: Optional[str] = None
    current_crew: Optional[str] = None
    
    # Crews being managed
    crews: Dict[str, CrewAICrew] = field(default_factory=dict)
    
    # Agents in crews
    agents: Dict[str, CrewAIAgent] = field(default_factory=dict)
    
    # Tasks in crews
    tasks: Dict[str, CrewAITask] = field(default_factory=dict)
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the agent with default skills"""
        self._initialize_skills()
    
    def _initialize_skills(self) -> None:
        """Initialize the agent's skill set"""
        self.skills = {
            "crew_design": "Design multi-agent crews with proper role assignments",
            "agent_configuration": "Configure CrewAI agents with goals, backstories, and tools",
            "task_management": "Create and manage tasks for agents with clear objectives",
            "process_orchestration": "Orchestrate sequential and parallel task execution",
            "tool_integration": "Integrate tools and APIs with CrewAI agents",
            "memory_management": "Manage agent memory and context across tasks",
            "result_aggregation": "Aggregate and process results from multiple agents",
            "error_handling": "Handle errors and edge cases in crew execution",
            "performance_optimization": "Optimize crew performance and resource usage",
            "testing": "Test crews and validate their functionality",
            "documentation": "Document crews, agents, and tasks",
            "deployment": "Deploy crews to production environments"
        }
    
    async def create_crew(self, crew_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new CrewAI crew
        
        Args:
            crew_spec: Crew specification
            
        Returns:
            Dictionary with crew configuration
        """
        print(f"🚀 {self.name}: Creating crew {crew_spec.get('name', 'Unnamed')}")
        
        crew_id = crew_spec.get("crew_id", f"crew_{len(self.crews) + 1}")
        crew_name = crew_spec.get("name", "Unnamed Crew")
        description = crew_spec.get("description", "")
        process = crew_spec.get("process", "sequential")
        memory = crew_spec.get("memory", True)
        cache = crew_spec.get("cache", False)
        max_rpm = crew_spec.get("max_rpm")
        share_crew = crew_spec.get("share_crew", False)
        
        # Create crew
        crew = CrewAICrew(
            crew_id=crew_id,
            name=crew_name,
            description=description,
            process=process,
            memory=memory,
            cache=cache,
            max_rpm=max_rpm,
            share_crew=share_crew
        )
        
        self.crews[crew_id] = crew
        self.current_crew = crew_id
        
        # Generate crew code
        crew_code = self._generate_crew_code(crew)
        
        result = {
            "crew_id": crew_id,
            "name": crew_name,
            "description": description,
            "process": process,
            "memory": memory,
            "cache": cache,
            "max_rpm": max_rpm,
            "share_crew": share_crew,
            "code": crew_code,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Crew {crew_name} created with ID {crew_id}")
        return result
    
    def _generate_crew_code(self, crew: CrewAICrew) -> str:
        """Generate CrewAI crew implementation code"""
        code = f'''
from crewai import Crew, Agent, Task, Process

# Create agents
agents = []

# Create tasks
tasks = []

# Create crew
{crew.name.lower().replace(' ', '_')}_crew = Crew(
    agents=agents,
    tasks=tasks,
    process=Process.{crew.process.capitalize()},
    memory={str(crew.memory).lower()},
    cache={str(crew.cache).lower()},
    max_rpm={crew.max_rpm},
    share_crew={str(crew.share_crew).lower()},
    verbose=2
)

# Execute crew
result = {crew.name.lower().replace(' ', '_')}_crew.kickoff()

# Print results
print("Crew execution completed!")
print(f"Results: {{result}}")
'''
        return code
    
    async def create_agent(self, crew_id: str, agent_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new CrewAI agent
        
        Args:
            crew_id: ID of the crew to add the agent to
            agent_spec: Agent specification
            
        Returns:
            Dictionary with agent configuration
        """
        print(f"🤖 {self.name}: Creating agent for crew {crew_id}")
        
        if crew_id not in self.crews:
            raise ValueError(f"Crew {crew_id} not found")
        
        crew = self.crews[crew_id]
        
        agent_id = agent_spec.get("agent_id", f"agent_{len(self.agents) + 1}")
        role_str = agent_spec.get("role", "custom")
        
        # Validate role
        try:
            role = CrewAIRole(role_str)
        except ValueError:
            role = CrewAIRole.CUSTOM
            print(f"⚠️  Role {role_str} not supported, defaulting to Custom")
        
        goal = agent_spec.get("goal", "")
        backstory = agent_spec.get("backstory", "")
        verbose = agent_spec.get("verbose", True)
        allow_delegation = agent_spec.get("allow_delegation", False)
        tools = agent_spec.get("tools", [])
        memory = agent_spec.get("memory", True)
        
        # Create agent
        agent = CrewAIAgent(
            agent_id=agent_id,
            role=role,
            goal=goal,
            backstory=backstory,
            verbose=verbose,
            allow_delegation=allow_delegation,
            tools=tools,
            memory=memory
        )
        
        self.agents[agent_id] = agent
        crew.agents.append(agent_id)
        
        # Generate agent code
        agent_code = self._generate_agent_code(agent)
        
        result = {
            "crew_id": crew_id,
            "agent_id": agent_id,
            "role": role.value,
            "goal": goal,
            "backstory": backstory,
            "verbose": verbose,
            "allow_delegation": allow_delegation,
            "tools": tools,
            "memory": memory,
            "code": agent_code,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Agent {agent_id} ({role.value}) created for crew {crew_id}")
        return result
    
    def _generate_agent_code(self, agent: CrewAIAgent) -> str:
        """Generate CrewAI agent implementation code"""
        role_description = self._get_role_description(agent.role)
        
        code = f'''
from crewai import Agent

# Create {agent.role.value} agent
{agent.agent_id} = Agent(
    role="{agent.role.value}",
    goal="{agent.goal}",
    backstory="""{agent.backstory}""",
    verbose={str(agent.verbose).lower()},
    allow_delegation={str(agent.allow_delegation).lower()},
    tools={agent.tools},
    memory={str(agent.memory).lower()}
)

# Agent description
# Role: {agent.role.value}
# {role_description}
# Goal: {agent.goal}
# Backstory: {agent.backstory[:100]}...
'''
        return code
    
    def _get_role_description(self, role: CrewAIRole) -> str:
        """Get description for a role"""
        descriptions = {
            CrewAIRole.RESEARCHER: "Researches information, gathers data, and provides insights",
            CrewAIRole.WRITER: "Creates content, writes documents, and generates text",
            CrewAIRole.ANALYST: "Analyzes data, identifies patterns, and provides recommendations",
            CrewAIRole.DEVELOPER: "Writes code, develops software, and implements solutions",
            CrewAIRole.DESIGNER: "Designs systems, creates architectures, and plans solutions",
            CrewAIRole.TESTER: "Tests implementations, validates results, and ensures quality",
            CrewAIRole.COORDINATOR: "Coordinates activities, manages workflows, and oversees processes",
            CrewAIRole.CUSTOM: "Custom role with specialized capabilities"
        }
        return descriptions.get(role, "Custom role")
    
    async def create_task(self, crew_id: str, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new CrewAI task
        
        Args:
            crew_id: ID of the crew to add the task to
            task_spec: Task specification
            
        Returns:
            Dictionary with task configuration
        """
        print(f"📋 {self.name}: Creating task for crew {crew_id}")
        
        if crew_id not in self.crews:
            raise ValueError(f"Crew {crew_id} not found")
        
        crew = self.crews[crew_id]
        
        task_id = task_spec.get("task_id", f"task_{len(self.tasks) + 1}")
        description = task_spec.get("description", "")
        agent_id = task_spec.get("agent")
        
        # Validate agent exists
        if agent_id and agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        expected_output = task_spec.get("expected_output", "")
        async_execution = task_spec.get("async_execution", False)
        output_file = task_spec.get("output_file")
        human_input = task_spec.get("human_input", False)
        
        # Create task
        task = CrewAITask(
            task_id=task_id,
            description=description,
            agent=agent_id or "",
            expected_output=expected_output,
            async_execution=async_execution,
            output_file=output_file,
            human_input=human_input
        )
        
        self.tasks[task_id] = task
        crew.tasks.append(task_id)
        
        # Generate task code
        task_code = self._generate_task_code(task, agent_id)
        
        result = {
            "crew_id": crew_id,
            "task_id": task_id,
            "description": description,
            "agent": agent_id,
            "expected_output": expected_output,
            "async_execution": async_execution,
            "output_file": output_file,
            "human_input": human_input,
            "code": task_code,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Task {task_id} created for crew {crew_id}")
        return result
    
    def _generate_task_code(self, task: CrewAITask, agent_id: Optional[str] = None) -> str:
        """Generate CrewAI task implementation code"""
        agent_name = agent_id or "assigned_agent"
        
        code = f'''
from crewai import Task

# Create task for {agent_name}
{task.task_id} = Task(
    description="""{task.description}""",
    agent={agent_name},
    expected_output="""{task.expected_output}""",
    async_execution={str(task.async_execution).lower()},
    output_file="{task.output_file or ''}",
    human_input={str(task.human_input).lower()}
)

# Task details
# Description: {task.description[:100]}...
# Expected Output: {task.expected_output[:100]}...
# Agent: {agent_name}
'''
        return code
    
    async def execute_crew(self, crew_id: str, execution_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a crew
        
        Args:
            crew_id: ID of the crew to execute
            execution_spec: Execution specification
            
        Returns:
            Dictionary with execution results
        """
        print(f"▶️ {self.name}: Executing crew {crew_id}")
        
        if crew_id not in self.crews:
            raise ValueError(f"Crew {crew_id} not found")
        
        crew = self.crews[crew_id]
        
        # Generate execution code
        execution_code = self._generate_execution_code(crew, execution_spec)
        
        # Simulate execution results
        execution_results = {
            "crew_id": crew_id,
            "name": crew.name,
            "status": "completed",
            "start_time": "2024-01-01T00:00:00Z",
            "end_time": "2024-01-01T00:00:00Z",
            "duration": 0.0,
            "agents_executed": len(crew.agents),
            "tasks_completed": len(crew.tasks),
            "results": {},
            "errors": [],
            "code": execution_code
        }
        
        # Simulate results for each task
        for task_id in crew.tasks:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                execution_results["results"][task_id] = {
                    "status": "completed",
                    "description": task.description,
                    "output": f"Task {task_id} completed successfully",
                    "agent": task.agent
                }
        
        print(f"✅ {self.name}: Crew {crew_id} execution completed")
        return execution_results
    
    def _generate_execution_code(self, crew: CrewAICrew, execution_spec: Dict[str, Any]) -> str:
        """Generate crew execution code"""
        code = f'''
from crewai import Crew, Agent, Task, Process
import json

# Define agents
agents = []

# Define tasks
tasks = []

# Create crew
crew = Crew(
    agents=agents,
    tasks=tasks,
    process=Process.{crew.process.capitalize()},
    memory={str(crew.memory).lower()},
    cache={str(crew.cache).lower()},
    max_rpm={crew.max_rpm},
    share_crew={str(crew.share_crew).lower()},
    verbose=2
)

# Execute crew
print(f"Starting crew execution: {{crew.name}}")
print(f"Process: {{crew.process}}")
print(f"Agents: {{len(crew.agents)}}")
print(f"Tasks: {{len(crew.tasks)}}")

try:
    result = crew.kickoff()
    
    # Process results
    print("\\nCrew execution completed successfully!")
    print(f"Results: {{json.dumps(result, indent=2)}}")
    
    # Save results if output file specified
    output_file = "{execution_spec.get('output_file', 'crew_results.json')}"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Results saved to {{output_file}}")
    
except Exception as e:
    print(f"Error executing crew: {{e}}")
    raise

# Crew execution summary
print(f"\\nCrew {{crew.name}} execution summary:")
print(f"- Status: Completed")
print(f"- Agents executed: {{len(crew.agents)}}")
print(f"- Tasks completed: {{len(crew.tasks)}}")
'''
        return code
    
    async def validate_crew(self, crew_id: str) -> Dict[str, Any]:
        """
        Validate a crew configuration
        
        Args:
            crew_id: ID of the crew to validate
            
        Returns:
            Dictionary with validation results
        """
        print(f"✅ {self.name}: Validating crew {crew_id}")
        
        if crew_id not in self.crews:
            raise ValueError(f"Crew {crew_id} not found")
        
        crew = self.crews[crew_id]
        
        validation = {
            "crew": crew_id,
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Check crew name
        if not crew.name:
            validation["valid"] = False
            validation["errors"].append("Crew name is required")
        
        # Check for agents
        if not crew.agents:
            validation["warnings"].append("Crew has no agents")
        else:
            # Check each agent
            for agent_id in crew.agents:
                if agent_id not in self.agents:
                    validation["errors"].append(f"Agent {agent_id} not found")
                else:
                    agent = self.agents[agent_id]
                    if not agent.goal:
                        validation["warnings"].append(f"Agent {agent_id} has no goal")
        
        # Check for tasks
        if not crew.tasks:
            validation["warnings"].append("Crew has no tasks")
        else:
            # Check each task
            for task_id in crew.tasks:
                if task_id not in self.tasks:
                    validation["errors"].append(f"Task {task_id} not found")
                else:
                    task = self.tasks[task_id]
                    if not task.description:
                        validation["warnings"].append(f"Task {task_id} has no description")
                    if not task.agent:
                        validation["warnings"].append(f"Task {task_id} has no assigned agent")
        
        # Check process type
        if crew.process not in ["sequential", "parallel"]:
            validation["warnings"].append(f"Process type {crew.process} may not be supported")
        
        # Recommendations
        if len(crew.agents) > 5:
            validation["recommendations"].append("Consider breaking down large crews into smaller, focused teams")
        
        if len(crew.tasks) > 10:
            validation["recommendations"].append("Consider breaking down complex workflows into smaller crews")
        
        print(f"✅ {self.name}: Crew {crew_id} validation completed")
        return validation
    
    async def generate_crew_documentation(self, crew_id: str) -> Dict[str, Any]:
        """
        Generate documentation for a crew
        
        Args:
            crew_id: ID of the crew
            
        Returns:
            Dictionary with documentation
        """
        print(f"📚 {self.name}: Generating documentation for crew {crew_id}")
        
        if crew_id not in self.crews:
            raise ValueError(f"Crew {crew_id} not found")
        
        crew = self.crews[crew_id]
        
        documentation = {
            "crew": {
                "id": crew.crew_id,
                "name": crew.name,
                "description": crew.description,
                "process": crew.process,
                "memory": crew.memory,
                "cache": crew.cache,
                "max_rpm": crew.max_rpm,
                "share_crew": crew.share_crew
            },
            "agents": [],
            "tasks": [],
            "execution": {},
            "usage": {}
        }
        
        # Document agents
        for agent_id in crew.agents:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                agent_doc = {
                    "id": agent.agent_id,
                    "role": agent.role.value,
                    "goal": agent.goal,
                    "backstory": agent.backstory,
                    "verbose": agent.verbose,
                    "allow_delegation": agent.allow_delegation,
                    "tools": agent.tools,
                    "memory": agent.memory
                }
                documentation["agents"].append(agent_doc)
        
        # Document tasks
        for task_id in crew.tasks:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task_doc = {
                    "id": task.task_id,
                    "description": task.description,
                    "agent": task.agent,
                    "expected_output": task.expected_output,
                    "async_execution": task.async_execution,
                    "output_file": task.output_file,
                    "human_input": task.human_input
                }
                documentation["tasks"].append(task_doc)
        
        # Generate execution documentation
        execution_code = self._generate_execution_code(crew, {})
        documentation["execution"] = {
            "code": execution_code,
            "instructions": f'''
# Execute the {crew.name} crew

1. Save the crew configuration to a Python file
2. Install required dependencies: `pip install crewai`
3. Run the execution script: `python crew_{crew.crew_id}.py`
4. Monitor the execution logs for progress and errors
5. Check the output files for results
'''
        }
        
        # Generate usage examples
        documentation["usage"] = {
            "quick_start": f'''
# Quick Start: {crew.name}

```python
from crewai import Crew, Agent, Task

# Create agents
{chr(10).join([f'{agent.agent_id} = Agent(role="{agent.role.value}", goal="{agent.goal}")' for agent_id in crew.agents if agent_id in self.agents])}

# Create tasks
{chr(10).join([f'{task.task_id} = Task(description="{task.description}", agent={task.agent})' for task_id in crew.tasks if task_id in self.tasks])}

# Create and execute crew
crew = Crew(
    agents=[{', '.join(crew.agents)}],
    tasks=[{', '.join(crew.tasks)}],
    process="{crew.process}"
)

result = crew.kickoff()
print(result)
```
''',
            "best_practices": """
# Best Practices for CrewAI

1. **Agent Design**:
   - Give each agent a clear, specific role
   - Define goals that are achievable and measurable
   - Use backstories to provide context and personality

2. **Task Design**:
   - Make task descriptions clear and specific
   - Define expected outputs explicitly
   - Break complex tasks into smaller subtasks

3. **Crew Management**:
   - Use sequential processing for dependent tasks
   - Use parallel processing for independent tasks
   - Monitor resource usage (max_rpm)

4. **Error Handling**:
   - Enable verbose logging for debugging
   - Use try-catch blocks in custom functions
   - Validate inputs and outputs

5. **Performance**:
   - Limit crew size for better performance
   - Use caching for repeated operations
   - Monitor memory usage
"""
        }
        
        print(f"✅ {self.name}: Documentation generated for crew {crew_id}")
        return documentation
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "current_project": self.current_project,
            "current_crew": self.current_crew,
            "crews_count": len(self.crews),
            "agents_count": len(self.agents),
            "tasks_count": len(self.tasks),
            "performance_metrics": self.performance_metrics,
            "skills": list(self.skills.keys())
        }
    
    def reset(self) -> None:
        """Reset agent state"""
        self.current_project = None
        self.current_crew = None
        self.crews.clear()
        self.agents.clear()
        self.tasks.clear()
        self.performance_metrics.clear()
        print(f"🔄 {self.name}: Agent state reset")
