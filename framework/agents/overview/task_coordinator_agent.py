"""
Task Coordinator Agent - Task Distribution and Workflow Management

Responsibilities:
- Task distribution and assignment
- Workflow coordination
- Dependency management
- Progress tracking
- Load balancing
- Communication facilitation
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
from datetime import datetime
from collections import defaultdict


class TaskStatus(Enum):
    """Task status types"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    REVIEW = "review"


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class WorkflowType(Enum):
    """Workflow types"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


@dataclass
class WorkflowTask:
    """Represents a task in a workflow"""
    task_id: str
    name: str
    description: str = ""
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0  # in hours
    actual_duration: float = 0.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class Workflow:
    """Represents a workflow of tasks"""
    workflow_id: str
    name: str
    description: str = ""
    workflow_type: WorkflowType = WorkflowType.SEQUENTIAL
    tasks: Dict[str, WorkflowTask] = field(default_factory=dict)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str = "planned"  # "planned", "in_progress", "completed", "failed"


@dataclass
class AgentWorkload:
    """Represents an agent's current workload"""
    agent_id: str
    current_tasks: List[str] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)
    workload: float = 0.0  # 0-1
    capacity: float = 1.0  # 0-1
    efficiency: float = 0.0  # 0-1


@dataclass
class Communication:
    """Represents a communication between agents"""
    communication_id: str
    sender: str
    receiver: str
    timestamp: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    status: str = "sent"  # "sent", "delivered", "read", "responded"


@dataclass
class TaskCoordinatorAgent:
    """
    Task Coordinator Agent
    
    This agent specializes in task distribution, workflow management, and coordination
    between multiple agents working on related tasks.
    """
    
    agent_id: str = "task_coordinator_agent_001"
    name: str = "Task Coordinator"
    description: str = "Task distribution and workflow coordination specialist"
    version: str = "1.0.0"
    
    # Workflow state
    workflows: Dict[str, Workflow] = field(default_factory=dict)
    agent_workloads: Dict[str, AgentWorkload] = field(default_factory=dict)
    communications: Dict[str, Communication] = field(default_factory=dict)
    
    # Current state
    current_workflow: Optional[str] = None
    current_focus: str = "task_distribution"
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the agent"""
        pass
    
    async def create_workflow(self, workflow_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new workflow
        
        Args:
            workflow_spec: Workflow specification
            
        Returns:
            Dictionary with workflow configuration
        """
        print(f"🚀 {self.name}: Creating workflow {workflow_spec.get('name', 'Unnamed')}")
        
        workflow_id = workflow_spec.get("workflow_id", f"workflow_{len(self.workflows) + 1}")
        workflow_name = workflow_spec.get("name", "Unnamed Workflow")
        description = workflow_spec.get("description", "")
        workflow_type_str = workflow_spec.get("workflow_type", "sequential")
        tasks_spec = workflow_spec.get("tasks", [])
        dependencies_spec = workflow_spec.get("dependencies", {})
        
        # Validate workflow type
        try:
            workflow_type = WorkflowType(workflow_type_str)
        except ValueError:
            workflow_type = WorkflowType.SEQUENTIAL
            print(f"⚠️  Workflow type {workflow_type_str} not valid, defaulting to SEQUENTIAL")
        
        # Create workflow
        workflow = Workflow(
            workflow_id=workflow_id,
            name=workflow_name,
            description=description,
            workflow_type=workflow_type,
            dependencies=dependencies_spec
        )
        
        # Add tasks
        for task_spec in tasks_spec:
            task = self._create_task_from_spec(task_spec)
            workflow.tasks[task.task_id] = task
        
        self.workflows[workflow_id] = workflow
        self.current_workflow = workflow_id
        
        # Generate workflow visualization
        workflow_viz = self._generate_workflow_visualization(workflow)
        
        result = {
            "workflow_id": workflow_id,
            "name": workflow_name,
            "description": description,
            "workflow_type": workflow_type.value,
            "tasks": list(workflow.tasks.keys()),
            "dependencies": workflow.dependencies,
            "visualization": workflow_viz,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Workflow {workflow_name} created with {len(workflow.tasks)} tasks")
        return result
    
    def _create_task_from_spec(self, task_spec: Dict[str, Any]) -> WorkflowTask:
        """Create a task from specification"""
        task_id = task_spec.get("task_id", f"task_{len(self.workflows) + 1}")
        name = task_spec.get("name", "Unnamed Task")
        description = task_spec.get("description", "")
        status_str = task_spec.get("status", "todo")
        priority_str = task_spec.get("priority", "medium")
        assigned_to = task_spec.get("assigned_to")
        dependencies = task_spec.get("dependencies", [])
        estimated_duration = task_spec.get("estimated_duration", 0.0)
        
        # Validate status
        try:
            status = TaskStatus(status_str)
        except ValueError:
            status = TaskStatus.TODO
        
        # Validate priority
        try:
            priority = TaskPriority(priority_str)
        except ValueError:
            priority = TaskPriority.MEDIUM
        
        return WorkflowTask(
            task_id=task_id,
            name=name,
            description=description,
            status=status,
            priority=priority,
            assigned_to=assigned_to,
            dependencies=dependencies,
            estimated_duration=estimated_duration
        )
    
    def _generate_workflow_visualization(self, workflow: Workflow) -> Dict[str, Any]:
        """Generate a visualization of the workflow"""
        nodes = []
        edges = []
        
        # Add tasks as nodes
        for task_id, task in workflow.tasks.items():
            node = {
                "id": task_id,
                "label": task.name,
                "status": task.status.value,
                "priority": task.priority.value,
                "assigned_to": task.assigned_to,
                "type": "task"
            }
            nodes.append(node)
        
        # Add dependencies as edges
        for source, targets in workflow.dependencies.items():
            for target in targets:
                edge = {
                    "source": source,
                    "target": target,
                    "type": "dependency"
                }
                edges.append(edge)
        
        # Add workflow information
        workflow_info = {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "type": workflow.workflow_type.value,
            "task_count": len(workflow.tasks),
            "dependency_count": len(edges)
        }
        
        return {
            "workflow": workflow_info,
            "nodes": nodes,
            "edges": edges
        }
    
    async def distribute_tasks(self, workflow_id: str, agents: List[str]) -> Dict[str, Any]:
        """
        Distribute tasks to agents based on workload and capabilities
        
        Args:
            workflow_id: ID of the workflow
            agents: List of available agent IDs
            
        Returns:
            Dictionary with task distribution
        """
        print(f"📤 {self.name}: Distributing tasks for workflow {workflow_id}")
        
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        
        # Initialize agent workloads if not exists
        for agent_id in agents:
            if agent_id not in self.agent_workloads:
                self.agent_workloads[agent_id] = AgentWorkload(
                    agent_id=agent_id,
                    current_tasks=[],
                    completed_tasks=[],
                    workload=0.0,
                    capacity=1.0,
                    efficiency=0.5
                )
        
        # Get unassigned tasks
        unassigned_tasks = [
            task for task in workflow.tasks.values() 
            if task.status == TaskStatus.TODO and task.assigned_to is None
        ]
        
        # Sort tasks by priority (highest first)
        unassigned_tasks.sort(key=lambda t: {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3
        }.get(t.priority, 4))
        
        # Distribute tasks
        distribution = {
            "workflow_id": workflow_id,
            "assignments": [],
            "unassigned": [],
            "workload_balance": {}
        }
        
        for task in unassigned_tasks:
            # Find the best agent for this task
            best_agent = self._find_best_agent(task, agents)
            
            if best_agent:
                # Assign task to agent
                task.assigned_to = best_agent
                task.status = TaskStatus.IN_PROGRESS
                
                # Update agent workload
                agent_workload = self.agent_workloads[best_agent]
                agent_workload.current_tasks.append(task.task_id)
                agent_workload.workload = min(agent_workload.workload + task.estimated_duration / 40, 1.0)
                
                distribution["assignments"].append({
                    "task_id": task.task_id,
                    "task_name": task.name,
                    "assigned_to": best_agent,
                    "priority": task.priority.value,
                    "estimated_duration": task.estimated_duration
                })
            else:
                distribution["unassigned"].append(task.task_id)
        
        # Calculate workload balance
        for agent_id in agents:
            workload = self.agent_workloads[agent_id].workload
            distribution["workload_balance"][agent_id] = {
                "workload": workload,
                "capacity": self.agent_workloads[agent_id].capacity,
                "utilization": workload / self.agent_workloads[agent_id].capacity if self.agent_workloads[agent_id].capacity > 0 else 0
            }
        
        print(f"✅ {self.name}: Distributed {len(distribution['assignments'])} tasks to {len(set(a['assigned_to'] for a in distribution['assignments']))} agents")
        return distribution
    
    def _find_best_agent(self, task: WorkflowTask, agents: List[str]) -> Optional[str]:
        """Find the best agent for a task based on workload and capabilities"""
        best_agent = None
        best_score = -1
        
        for agent_id in agents:
            if agent_id not in self.agent_workloads:
                continue
            
            agent_workload = self.agent_workloads[agent_id]
            
            # Calculate score based on:
            # 1. Current workload (lower is better)
            # 2. Capacity (higher is better)
            # 3. Efficiency (higher is better)
            # 4. Priority matching (if agent has relevant skills)
            
            workload_score = 1 - agent_workload.workload  # 0-1, higher is better
            capacity_score = agent_workload.capacity  # 0-1, higher is better
            efficiency_score = agent_workload.efficiency  # 0-1, higher is better
            
            # Simple weighted score
            score = (workload_score * 0.4) + (capacity_score * 0.3) + (efficiency_score * 0.3)
            
            if score > best_score:
                best_score = score
                best_agent = agent_id
        
        return best_agent
    
    async def manage_dependencies(self, workflow_id: str) -> Dict[str, Any]:
        """
        Manage task dependencies in a workflow
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Dictionary with dependency management results
        """
        print(f"🔗 {self.name}: Managing dependencies for workflow {workflow_id}")
        
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        
        # Check for blocked tasks
        blocked_tasks = []
        ready_tasks = []
        in_progress_tasks = []
        
        for task_id, task in workflow.tasks.items():
            if task.status == TaskStatus.BLOCKED:
                blocked_tasks.append(task_id)
            elif task.status == TaskStatus.TODO:
                # Check if all dependencies are completed
                dependencies_met = all(
                    workflow.tasks[dep].status == TaskStatus.DONE 
                    for dep in task.dependencies 
                    if dep in workflow.tasks
                )
                
                if dependencies_met:
                    ready_tasks.append(task_id)
                else:
                    # Mark as blocked if dependencies not met
                    task.status = TaskStatus.BLOCKED
                    blocked_tasks.append(task_id)
            elif task.status == TaskStatus.IN_PROGRESS:
                in_progress_tasks.append(task_id)
        
        # Update workflow status
        all_tasks_completed = all(
            task.status == TaskStatus.DONE 
            for task in workflow.tasks.values()
        )
        
        if all_tasks_completed:
            workflow.status = "completed"
            workflow.end_time = datetime.now().isoformat()
        elif in_progress_tasks:
            workflow.status = "in_progress"
        
        # Generate dependency graph
        dependency_graph = self._generate_dependency_graph(workflow)
        
        result = {
            "workflow_id": workflow_id,
            "status": workflow.status,
            "blocked_tasks": blocked_tasks,
            "ready_tasks": ready_tasks,
            "in_progress_tasks": in_progress_tasks,
            "completed_tasks": [t.task_id for t in workflow.tasks.values() if t.status == TaskStatus.DONE],
            "dependency_graph": dependency_graph,
            "recommendations": self._generate_dependency_recommendations(workflow)
        }
        
        print(f"✅ {self.name}: Managed dependencies for workflow {workflow_id}")
        return result
    
    def _generate_dependency_graph(self, workflow: Workflow) -> Dict[str, Any]:
        """Generate a dependency graph for the workflow"""
        nodes = []
        edges = []
        
        # Add tasks as nodes
        for task_id, task in workflow.tasks.items():
            node = {
                "id": task_id,
                "label": task.name,
                "status": task.status.value,
                "priority": task.priority.value,
                "assigned_to": task.assigned_to,
                "type": "task"
            }
            
            # Highlight blocked tasks
            if task.status == TaskStatus.BLOCKED:
                node["blocked"] = True
                node["blocked_by"] = [
                    dep for dep in task.dependencies 
                    if dep in workflow.tasks and workflow.tasks[dep].status != TaskStatus.DONE
                ]
            
            nodes.append(node)
        
        # Add dependencies as edges
        for source, targets in workflow.dependencies.items():
            for target in targets:
                edge = {
                    "source": source,
                    "target": target,
                    "type": "dependency"
                }
                
                # Check if dependency is blocking
                if source in workflow.tasks and target in workflow.tasks:
                    source_task = workflow.tasks[source]
                    target_task = workflow.tasks[target]
                    
                    if source_task.status != TaskStatus.DONE and target_task.status == TaskStatus.BLOCKED:
                        edge["blocking"] = True
                
                edges.append(edge)
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def _generate_dependency_recommendations(self, workflow: Workflow) -> List[str]:
        """Generate recommendations for dependency management"""
        recommendations = []
        
        # Check for circular dependencies
        if self._has_circular_dependencies(workflow):
            recommendations.append("Warning: Circular dependencies detected. Review and resolve dependency loops.")
        
        # Check for long dependency chains
        max_chain_length = self._get_max_dependency_chain_length(workflow)
        if max_chain_length > 5:
            recommendations.append(f"Long dependency chain detected ({max_chain_length} tasks). Consider breaking into smaller workflows.")
        
        # Check for unassigned blocked tasks
        blocked_tasks = [
            task for task in workflow.tasks.values() 
            if task.status == TaskStatus.BLOCKED and task.assigned_to is None
        ]
        
        if blocked_tasks:
            recommendations.append(f"{len(blocked_tasks)} blocked tasks are unassigned. Assign agents to resolve blockers.")
        
        # Check for tasks with many dependencies
        for task_id, task in workflow.tasks.items():
            if len(task.dependencies) > 3:
                recommendations.append(f"Task {task.name} has {len(task.dependencies)} dependencies. Consider simplifying.")
        
        return recommendations
    
    def _has_circular_dependencies(self, workflow: Workflow) -> bool:
        """Check if workflow has circular dependencies"""
        # Simple implementation - would need more sophisticated cycle detection for production
        visited = set()
        
        def has_cycle(task_id: str, path: List[str]) -> bool:
            if task_id in path:
                return True
            
            if task_id in visited:
                return False
            
            visited.add(task_id)
            
            if task_id in workflow.dependencies:
                for dep in workflow.dependencies[task_id]:
                    if has_cycle(dep, path + [task_id]):
                        return True
            
            return False
        
        for task_id in workflow.tasks:
            if has_cycle(task_id, []):
                return True
        
        return False
    
    def _get_max_dependency_chain_length(self, workflow: Workflow) -> int:
        """Get the length of the longest dependency chain"""
        max_length = 0
        
        def get_chain_length(task_id: str, visited: set) -> int:
            if task_id in visited:
                return 0
            
            visited.add(task_id)
            
            if task_id not in workflow.dependencies or not workflow.dependencies[task_id]:
                return 1
            
            return 1 + max(
                get_chain_length(dep, visited.copy()) 
                for dep in workflow.dependencies[task_id]
            )
        
        for task_id in workflow.tasks:
            length = get_chain_length(task_id, set())
            max_length = max(max_length, length)
        
        return max_length
    
    async def track_progress(self, workflow_id: str) -> Dict[str, Any]:
        """
        Track the progress of a workflow
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Dictionary with progress tracking information
        """
        print(f"📊 {self.name}: Tracking progress for workflow {workflow_id}")
        
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        
        # Calculate progress metrics
        total_tasks = len(workflow.tasks)
        completed_tasks = len([t for t in workflow.tasks.values() if t.status == TaskStatus.DONE])
        in_progress_tasks = len([t for t in workflow.tasks.values() if t.status == TaskStatus.IN_PROGRESS])
        blocked_tasks = len([t for t in workflow.tasks.values() if t.status == TaskStatus.BLOCKED])
        todo_tasks = len([t for t in workflow.tasks.values() if t.status == TaskStatus.TODO])
        
        progress = completed_tasks / total_tasks if total_tasks > 0 else 0
        
        # Calculate time metrics
        total_estimated = sum(t.estimated_duration for t in workflow.tasks.values())
        total_actual = sum(t.actual_duration for t in workflow.tasks.values() if t.actual_duration > 0)
        
        # Calculate efficiency
        efficiency = total_actual / total_estimated if total_estimated > 0 else 0
        
        # Generate progress report
        progress_report = {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "status": workflow.status,
            "progress": progress,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "blocked_tasks": blocked_tasks,
            "todo_tasks": todo_tasks,
            "total_estimated_hours": total_estimated,
            "total_actual_hours": total_actual,
            "efficiency": efficiency,
            "task_status": {
                "todo": [t.task_id for t in workflow.tasks.values() if t.status == TaskStatus.TODO],
                "in_progress": [t.task_id for t in workflow.tasks.values() if t.status == TaskStatus.IN_PROGRESS],
                "done": [t.task_id for t in workflow.tasks.values() if t.status == TaskStatus.DONE],
                "blocked": [t.task_id for t in workflow.tasks.values() if t.status == TaskStatus.BLOCKED]
            },
            "recommendations": self._generate_progress_recommendations(workflow)
        }
        
        # Update workflow performance metrics
        self.performance_metrics[workflow_id] = {
            "progress": progress,
            "efficiency": efficiency,
            "blocked_tasks": blocked_tasks
        }
        
        print(f"✅ {self.name}: Progress tracked for workflow {workflow_id} ({progress:.1%} complete)")
        return progress_report
    
    def _generate_progress_recommendations(self, workflow: Workflow) -> List[str]:
        """Generate recommendations based on progress"""
        recommendations = []
        
        # Check for blocked tasks
        blocked_tasks = [t for t in workflow.tasks.values() if t.status == TaskStatus.BLOCKED]
        if blocked_tasks:
            recommendations.append(f"Address {len(blocked_tasks)} blocked tasks to unblock progress.")
        
        # Check for unassigned tasks
        unassigned_tasks = [t for t in workflow.tasks.values() if t.assigned_to is None and t.status == TaskStatus.TODO]
        if unassigned_tasks:
            recommendations.append(f"Assign {len(unassigned_tasks)} unassigned tasks to team members.")
        
        # Check for long-running tasks
        long_tasks = [
            t for t in workflow.tasks.values() 
            if t.status == TaskStatus.IN_PROGRESS and t.actual_duration > t.estimated_duration * 2
        ]
        if long_tasks:
            recommendations.append(f"Investigate {len(long_tasks)} tasks that are taking longer than estimated.")
        
        # Check for idle agents
        idle_agents = [
            a for a in self.agent_workloads.values() 
            if not a.current_tasks and a.workload == 0
        ]
        if idle_agents and unassigned_tasks:
            recommendations.append(f"Assign tasks to {len(idle_agents)} idle agents.")
        
        return recommendations
    
    async def facilitate_communication(self, communication_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Facilitate communication between agents
        
        Args:
            communication_spec: Communication specification
            
        Returns:
            Dictionary with communication results
        """
        print(f"💬 {self.name}: Facilitating communication")
        
        communication_id = communication_spec.get("communication_id", f"comm_{len(self.communications) + 1}")
        sender = communication_spec.get("sender")
        receiver = communication_spec.get("receiver")
        message = communication_spec.get("message", "")
        data = communication_spec.get("data", {})
        
        # Validate sender and receiver
        if sender and sender not in self.agent_workloads:
            raise ValueError(f"Sender {sender} not registered")
        if receiver and receiver not in self.agent_workloads:
            raise ValueError(f"Receiver {receiver} not registered")
        
        # Create communication
        communication = Communication(
            communication_id=communication_id,
            sender=sender or "system",
            receiver=receiver or "all",
            timestamp=datetime.now().isoformat(),
            message=message,
            data=data,
            status="sent"
        )
        
        self.communications[communication_id] = communication
        
        # Process communication based on type
        if "task_update" in data:
            await self._process_task_update(communication)
        elif "blocker" in data:
            await self._process_blocker_notification(communication)
        elif "request_help" in data:
            await self._process_help_request(communication)
        
        result = {
            "communication_id": communication_id,
            "sender": sender,
            "receiver": receiver,
            "message": message,
            "data": data,
            "status": "sent",
            "timestamp": communication.timestamp
        }
        
        print(f"✅ {self.name}: Communication {communication_id} facilitated")
        return result
    
    async def _process_task_update(self, communication: Communication) -> None:
        """Process a task update communication"""
        task_id = communication.data.get("task_id")
        status_str = communication.data.get("status")
        
        # Find the task in workflows
        for workflow in self.workflows.values():
            if task_id in workflow.tasks:
                task = workflow.tasks[task_id]
                
                # Update task status
                try:
                    task.status = TaskStatus(status_str)
                except ValueError:
                    pass
                
                # Update task result if provided
                if "result" in communication.data:
                    task.result = communication.data["result"]
                
                # Update task error if provided
                if "error" in communication.data:
                    task.error = communication.data["error"]
                
                # Update task end time
                task.end_time = datetime.now().isoformat()
                
                # Update agent workload
                if task.assigned_to and task.assigned_to in self.agent_workloads:
                    agent_workload = self.agent_workloads[task.assigned_to]
                    
                    if task.status == TaskStatus.DONE:
                        if task.task_id in agent_workload.current_tasks:
                            agent_workload.current_tasks.remove(task.task_id)
                        agent_workload.completed_tasks.append(task.task_id)
                        agent_workload.workload = max(agent_workload.workload - task.estimated_duration / 40, 0)
                    
                    # Update efficiency based on actual vs estimated
                    if task.actual_duration > 0 and task.estimated_duration > 0:
                        efficiency = task.estimated_duration / task.actual_duration
                        agent_workload.efficiency = (agent_workload.efficiency + efficiency) / 2
                
                break
    
    async def _process_blocker_notification(self, communication: Communication) -> None:
        """Process a blocker notification"""
        task_id = communication.data.get("task_id")
        blocker = communication.data.get("blocker", "")
        
        # Find the task and mark as blocked
        for workflow in self.workflows.values():
            if task_id in workflow.tasks:
                task = workflow.tasks[task_id]
                task.status = TaskStatus.BLOCKED
                task.error = f"Blocked by: {blocker}"
                break
    
    async def _process_help_request(self, communication: Communication) -> None:
        """Process a help request"""
        requester = communication.sender
        task_id = communication.data.get("task_id")
        help_type = communication.data.get("help_type", "general")
        
        # Find available agents to help
        available_agents = [
            a for a in self.agent_workloads.values() 
            if a.workload < 0.8 and a.agent_id != requester
        ]
        
        if available_agents:
            # Assign the first available agent to help
            helper = available_agents[0]
            
            # Create a help task
            help_task = WorkflowTask(
                task_id=f"help_{task_id}_{len(self.workflows) + 1}",
                name=f"Help with {task_id}",
                description=f"Provide assistance with task {task_id}",
                status=TaskStatus.TODO,
                priority=TaskPriority.HIGH,
                assigned_to=helper.agent_id,
                dependencies=[task_id]
            )
            
            # Add to current workflow or create new one
            if self.current_workflow and self.current_workflow in self.workflows:
                workflow = self.workflows[self.current_workflow]
                workflow.tasks[help_task.task_id] = help_task
            else:
                # Create a new workflow for help tasks
                help_workflow = Workflow(
                    workflow_id=f"help_workflow_{len(self.workflows) + 1}",
                    name="Help Requests",
                    workflow_type=WorkflowType.PARALLEL
                )
                help_workflow.tasks[help_task.task_id] = help_task
                self.workflows[help_workflow.workflow_id] = help_workflow
        
        print(f"🆘 Help requested by {requester} for task {task_id}")
    
    async def balance_workload(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Balance workload across agents
        
        Args:
            workflow_id: Optional workflow ID to balance (balances all if None)
            
        Returns:
            Dictionary with workload balancing results
        """
        print(f"⚖️ {self.name}: Balancing workload")
        
        if workflow_id:
            if workflow_id not in self.workflows:
                raise ValueError(f"Workflow {workflow_id} not found")
            workflows_to_balance = [self.workflows[workflow_id]]
        else:
            workflows_to_balance = list(self.workflows.values())
        
        balancing_results = {
            "workflows_balanced": len(workflows_to_balance),
            "reassignments": [],
            "workload_before": {},
            "workload_after": {}
        }
        
        # Record current workload
        for agent_id, workload in self.agent_workloads.items():
            balancing_results["workload_before"][agent_id] = workload.workload
        
        # Balance each workflow
        for workflow in workflows_to_balance:
            # Get all agents
            all_agents = list(self.agent_workloads.keys())
            
            # Re-distribute tasks
            distribution = await self.distribute_tasks(workflow.workflow_id, all_agents)
            
            # Record reassignments
            for assignment in distribution["assignments"]:
                if assignment["assigned_to"] not in [a["assigned_to"] for a in balancing_results["reassignments"]]:
                    balancing_results["reassignments"].append(assignment)
        
        # Record new workload
        for agent_id, workload in self.agent_workloads.items():
            balancing_results["workload_after"][agent_id] = workload.workload
        
        # Calculate improvement
        workload_variance_before = self._calculate_workload_variance(balancing_results["workload_before"])
        workload_variance_after = self._calculate_workload_variance(balancing_results["workload_after"])
        improvement = workload_variance_before - workload_variance_after
        
        balancing_results["improvement"] = improvement
        balancing_results["workload_variance_before"] = workload_variance_before
        balancing_results["workload_variance_after"] = workload_variance_after
        
        print(f"✅ {self.name}: Workload balanced with {improvement:.2f} improvement in variance")
        return balancing_results
    
    def _calculate_workload_variance(self, workloads: Dict[str, float]) -> float:
        """Calculate the variance of workloads"""
        if not workloads:
            return 0.0
        
        values = list(workloads.values())
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        
        return variance
    
    async def get_coordinator_status(self) -> Dict[str, Any]:
        """
        Get the current task coordinator status
        
        Returns:
            Dictionary with coordinator status
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "current_workflow": self.current_workflow,
            "current_focus": self.current_focus,
            "workflows_count": len(self.workflows),
            "agents_count": len(self.agent_workloads),
            "communications_count": len(self.communications),
            "performance_metrics": self.performance_metrics
        }
    
    def reset(self) -> None:
        """Reset agent state"""
        self.current_workflow = None
        self.current_focus = "task_distribution"
        self.workflows.clear()
        self.agent_workloads.clear()
        self.communications.clear()
        self.performance_metrics.clear()
        print(f"🔄 {self.name}: Agent state reset")
