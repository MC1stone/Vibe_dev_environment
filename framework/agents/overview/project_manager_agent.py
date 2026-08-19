"""
Project Manager Agent - Project Planning and Execution Management

Responsibilities:
- Project planning and scheduling
- Task breakdown and assignment
- Timeline management
- Risk assessment
- Resource planning
- Progress tracking
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
from datetime import datetime, timedelta


class ProjectPhase(Enum):
    """Project phase types"""
    INITIATION = "initiation"
    PLANNING = "planning"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    CLOSURE = "closure"


class ProjectStatus(Enum):
    """Project status types"""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RiskLevel(Enum):
    """Risk level types"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DependencyType(Enum):
    """Dependency types"""
    TASK = "task"
    RESOURCE = "resource"
    EXTERNAL = "external"
    TECHNICAL = "technical"


@dataclass
class ProjectPlan:
    """Represents a project plan"""
    plan_id: str
    project_id: str
    phases: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    timeline: Dict[str, Any] = field(default_factory=dict)
    budget: Dict[str, Any] = field(default_factory=dict)
    resources: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskBreakdown:
    """Represents a task breakdown structure"""
    task_id: str
    subtasks: List[str] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    critical_path: List[str] = field(default_factory=list)


@dataclass
class Risk:
    """Represents a project risk"""
    risk_id: str
    title: str
    description: str
    level: RiskLevel = RiskLevel.MEDIUM
    probability: float = 0.5
    impact: float = 0.5
    mitigation: str = ""
    owner: Optional[str] = None
    status: str = "open"  # "open", "mitigated", "accepted", "closed"


@dataclass
class Resource:
    """Represents a project resource"""
    resource_id: str
    name: str
    type: str  # "human", "equipment", "budget", "time"
    allocated: float = 0.0
    available: float = 0.0
    cost: float = 0.0
    schedule: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressUpdate:
    """Represents a progress update"""
    update_id: str
    project_id: str
    timestamp: str
    progress: float  # 0-1
    notes: str = ""
    issues: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)


@dataclass
class ProjectManagerAgent:
    """
    Project Manager Agent
    
    This agent specializes in project planning, execution, and monitoring.
    It manages project timelines, resources, risks, and progress tracking.
    """
    
    agent_id: str = "project_manager_agent_001"
    name: str = "Project Manager"
    description: str = "Project planning, execution, and monitoring specialist"
    version: str = "1.0.0"
    
    # Project state
    project_plans: Dict[str, ProjectPlan] = field(default_factory=dict)
    task_breakdowns: Dict[str, TaskBreakdown] = field(default_factory=dict)
    risks: Dict[str, Risk] = field(default_factory=dict)
    resources: Dict[str, Resource] = field(default_factory=dict)
    progress_updates: Dict[str, ProgressUpdate] = field(default_factory=dict)
    
    # Current state
    current_project: Optional[str] = None
    current_phase: Optional[ProjectPhase] = None
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the agent"""
        pass
    
    async def create_project_plan(self, project_id: str, plan_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a comprehensive project plan
        
        Args:
            project_id: ID of the project to plan
            plan_spec: Project plan specification
            
        Returns:
            Dictionary with project plan
        """
        print(f"📅 {self.name}: Creating project plan for project {project_id}")
        
        plan_id = plan_spec.get("plan_id", f"plan_{project_id}")
        phases_spec = plan_spec.get("phases", [])
        milestones_spec = plan_spec.get("milestones", [])
        timeline_spec = plan_spec.get("timeline", {})
        budget_spec = plan_spec.get("budget", {})
        resources_spec = plan_spec.get("resources", {})
        
        # Create project plan
        project_plan = ProjectPlan(
            plan_id=plan_id,
            project_id=project_id,
            phases=self._create_phases(phases_spec),
            milestones=self._create_milestones(milestones_spec),
            timeline=timeline_spec,
            budget=budget_spec,
            resources=resources_spec
        )
        
        self.project_plans[plan_id] = project_plan
        self.current_project = project_id
        
        # Generate Gantt chart data
        gantt_data = self._generate_gantt_data(project_plan)
        
        result = {
            "plan_id": plan_id,
            "project_id": project_id,
            "phases": project_plan.phases,
            "milestones": project_plan.milestones,
            "timeline": project_plan.timeline,
            "budget": project_plan.budget,
            "resources": project_plan.resources,
            "gantt_data": gantt_data,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Project plan created for project {project_id}")
        return result
    
    def _create_phases(self, phases_spec: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Create project phases from specification"""
        phases = {}
        
        for phase_spec in phases_spec:
            phase_id = phase_spec.get("phase_id", f"phase_{len(phases) + 1}")
            phase_name = phase_spec.get("name", "Unnamed Phase")
            phase_type_str = phase_spec.get("type", "execution")
            
            try:
                phase_type = ProjectPhase(phase_type_str)
            except ValueError:
                phase_type = ProjectPhase.EXECUTION
            
            start_date = phase_spec.get("start_date", "")
            end_date = phase_spec.get("end_date", "")
            duration = phase_spec.get("duration", 0)
            description = phase_spec.get("description", "")
            deliverables = phase_spec.get("deliverables", [])
            
            phases[phase_id] = {
                "phase_id": phase_id,
                "name": phase_name,
                "type": phase_type.value,
                "start_date": start_date,
                "end_date": end_date,
                "duration": duration,
                "description": description,
                "deliverables": deliverables,
                "status": "planned"
            }
        
        return phases
    
    def _create_milestones(self, milestones_spec: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create project milestones from specification"""
        milestones = []
        
        for milestone_spec in milestones_spec:
            milestone_id = milestone_spec.get("milestone_id", f"milestone_{len(milestones) + 1}")
            milestone_name = milestone_spec.get("name", "Unnamed Milestone")
            description = milestone_spec.get("description", "")
            due_date = milestone_spec.get("due_date", "")
            phase_id = milestone_spec.get("phase_id", "")
            dependencies = milestone_spec.get("dependencies", [])
            
            milestones.append({
                "milestone_id": milestone_id,
                "name": milestone_name,
                "description": description,
                "due_date": due_date,
                "phase_id": phase_id,
                "dependencies": dependencies,
                "status": "planned",
                "completed": False
            })
        
        return milestones
    
    def _generate_gantt_data(self, project_plan: ProjectPlan) -> Dict[str, Any]:
        """Generate Gantt chart data from project plan"""
        tasks = []
        
        # Add phases as tasks
        for phase_id, phase in project_plan.phases.items():
            task = {
                "id": phase_id,
                "name": phase["name"],
                "start_date": phase["start_date"],
                "end_date": phase["end_date"],
                "duration": phase["duration"],
                "type": "phase",
                "dependencies": [],
                "progress": 0
            }
            tasks.append(task)
        
        # Add milestones
        for milestone in project_plan.milestones:
            task = {
                "id": milestone["milestone_id"],
                "name": milestone["name"],
                "start_date": milestone["due_date"],
                "end_date": milestone["due_date"],
                "duration": 0,
                "type": "milestone",
                "dependencies": milestone["dependencies"],
                "progress": 0
            }
            tasks.append(task)
        
        return {
            "tasks": tasks,
            "timeline": project_plan.timeline
        }
    
    async def break_down_task(self, task_id: str, breakdown_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Break down a task into subtasks
        
        Args:
            task_id: ID of the task to break down
            breakdown_spec: Task breakdown specification
            
        Returns:
            Dictionary with task breakdown
        """
        print(f"🔧 {self.name}: Breaking down task {task_id}")
        
        subtasks_spec = breakdown_spec.get("subtasks", [])
        dependencies_spec = breakdown_spec.get("dependencies", {})
        critical_path_spec = breakdown_spec.get("critical_path", [])
        
        # Create task breakdown
        task_breakdown = TaskBreakdown(
            task_id=task_id,
            subtasks=subtasks_spec,
            dependencies=self._create_dependencies(dependencies_spec),
            critical_path=critical_path_spec
        )
        
        self.task_breakdowns[task_id] = task_breakdown
        
        # Generate dependency graph
        dependency_graph = self._generate_dependency_graph(task_breakdown)
        
        result = {
            "task_id": task_id,
            "subtasks": subtasks_spec,
            "dependencies": task_breakdown.dependencies,
            "critical_path": task_breakdown.critical_path,
            "dependency_graph": dependency_graph,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Task {task_id} broken down into {len(subtasks_spec)} subtasks")
        return result
    
    def _create_dependencies(self, dependencies_spec: Dict[str, Any]) -> Dict[str, List[str]]:
        """Create dependencies from specification"""
        dependencies = {}
        
        for task_id, deps in dependencies_spec.items():
            dependencies[task_id] = deps
        
        return dependencies
    
    def _generate_dependency_graph(self, task_breakdown: TaskBreakdown) -> Dict[str, Any]:
        """Generate a dependency graph from task breakdown"""
        nodes = []
        edges = []
        
        # Add all tasks as nodes
        all_tasks = [task_breakdown.task_id] + task_breakdown.subtasks
        for task_id in all_tasks:
            nodes.append({
                "id": task_id,
                "label": task_id,
                "type": "task"
            })
        
        # Add dependencies as edges
        for source, targets in task_breakdown.dependencies.items():
            for target in targets:
                edges.append({
                    "source": source,
                    "target": target,
                    "type": "dependency"
                })
        
        # Highlight critical path
        for task_id in task_breakdown.critical_path:
            for node in nodes:
                if node["id"] == task_id:
                    node["critical"] = True
        
        return {
            "nodes": nodes,
            "edges": edges,
            "critical_path": task_breakdown.critical_path
        }
    
    async def identify_risks(self, project_id: str, risk_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify and assess project risks
        
        Args:
            project_id: ID of the project
            risk_spec: Risk identification specification
            
        Returns:
            Dictionary with identified risks
        """
        print(f"⚠️  {self.name}: Identifying risks for project {project_id}")
        
        risk_types = risk_spec.get("risk_types", ["technical", "schedule", "resource", "quality"])
        threshold = risk_spec.get("threshold", 0.5)
        
        # Identify risks based on project data
        risks = []
        
        # Check for schedule risks
        if "schedule" in risk_types:
            schedule_risks = self._identify_schedule_risks(project_id)
            risks.extend(schedule_risks)
        
        # Check for resource risks
        if "resource" in risk_types:
            resource_risks = self._identify_resource_risks(project_id)
            risks.extend(resource_risks)
        
        # Check for technical risks
        if "technical" in risk_types:
            technical_risks = self._identify_technical_risks(project_id)
            risks.extend(technical_risks)
        
        # Check for quality risks
        if "quality" in risk_types:
            quality_risks = self._identify_quality_risks(project_id)
            risks.extend(quality_risks)
        
        # Filter by threshold
        filtered_risks = [r for r in risks if r["probability"] * r["impact"] >= threshold]
        
        # Store risks
        for risk in filtered_risks:
            risk_id = f"risk_{len(self.risks) + 1}"
            risk_obj = Risk(
                risk_id=risk_id,
                title=risk["title"],
                description=risk["description"],
                level=risk["level"],
                probability=risk["probability"],
                impact=risk["impact"],
                mitigation=risk.get("mitigation", ""),
                owner=risk.get("owner"),
                status="open"
            )
            self.risks[risk_id] = risk_obj
        
        result = {
            "project_id": project_id,
            "risks_identified": len(filtered_risks),
            "risks": filtered_risks,
            "risk_matrix": self._generate_risk_matrix(filtered_risks),
            "status": "completed"
        }
        
        print(f"✅ {self.name}: Identified {len(filtered_risks)} risks for project {project_id}")
        return result
    
    def _identify_schedule_risks(self, project_id: str) -> List[Dict[str, Any]]:
        """Identify schedule-related risks"""
        risks = []
        
        # Check if project plan exists
        if project_id not in [p.project_id for p in self.project_plans.values()]:
            return risks
        
        project_plan = next(p for p in self.project_plans.values() if p.project_id == project_id)
        
        # Check for tight deadlines
        today = datetime.now()
        for phase_id, phase in project_plan.phases.items():
            if phase["end_date"]:
                end_date = datetime.fromisoformat(phase["end_date"])
                days_until_deadline = (end_date - today).days
                
                if days_until_deadline < 7:
                    risks.append({
                        "title": f"Tight deadline for phase: {phase['name']}",
                        "description": f"Phase {phase['name']} has only {days_until_deadline} days until deadline",
                        "level": RiskLevel.HIGH,
                        "probability": 0.8,
                        "impact": 0.9,
                        "mitigation": "Consider extending deadline or allocating additional resources",
                        "type": "schedule"
                    })
                elif days_until_deadline < 14:
                    risks.append({
                        "title": f"Approaching deadline for phase: {phase['name']}",
                        "description": f"Phase {phase['name']} has {days_until_deadline} days until deadline",
                        "level": RiskLevel.MEDIUM,
                        "probability": 0.6,
                        "impact": 0.7,
                        "mitigation": "Monitor progress closely and address any blockers",
                        "type": "schedule"
                    })
        
        # Check for milestone dependencies
        for milestone in project_plan.milestones:
            if milestone["dependencies"] and milestone["due_date"]:
                end_date = datetime.fromisoformat(milestone["due_date"])
                days_until_deadline = (end_date - today).days
                
                if days_until_deadline < len(milestone["dependencies"]) * 3:
                    risks.append({
                        "title": f"Milestone dependency risk: {milestone['name']}",
                        "description": f"Milestone {milestone['name']} has {len(milestone['dependencies'])} dependencies and only {days_until_deadline} days until deadline",
                        "level": RiskLevel.MEDIUM,
                        "probability": 0.7,
                        "impact": 0.8,
                        "mitigation": "Ensure all dependencies are on track",
                        "type": "schedule"
                    })
        
        return risks
    
    def _identify_resource_risks(self, project_id: str) -> List[Dict[str, Any]]:
        """Identify resource-related risks"""
        risks = []
        
        # Check for resource constraints
        if project_id in self.resources:
            project_resources = [r for r in self.resources.values() if r.resource_id.startswith(f"{project_id}_")]
            
            for resource in project_resources:
                if resource.allocated > resource.available * 0.8:
                    risks.append({
                        "title": f"Resource constraint: {resource.name}",
                        "description": f"Resource {resource.name} is {resource.allocated/resource.available:.0%} allocated",
                        "level": RiskLevel.HIGH,
                        "probability": 0.9,
                        "impact": 0.8,
                        "mitigation": f"Acquire additional {resource.type} resources or optimize usage",
                        "type": "resource",
                        "owner": resource.resource_id
                    })
        
        return risks
    
    def _identify_technical_risks(self, project_id: str) -> List[Dict[str, Any]]:
        """Identify technical risks"""
        risks = []
        
        # Check for technical dependencies
        if project_id in self.task_breakdowns:
            task_breakdown = self.task_breakdowns[project_id]
            
            # Check for long critical paths
            if len(task_breakdown.critical_path) > 10:
                risks.append({
                    "title": "Long critical path",
                    "description": f"Critical path has {len(task_breakdown.critical_path)} tasks, increasing project risk",
                    "level": RiskLevel.MEDIUM,
                    "probability": 0.7,
                    "impact": 0.8,
                    "mitigation": "Consider breaking down large tasks or parallelizing work",
                    "type": "technical"
                })
            
            # Check for complex dependencies
            total_dependencies = sum(len(deps) for deps in task_breakdown.dependencies.values())
            if total_dependencies > len(task_breakdown.subtasks):
                risks.append({
                    "title": "Complex dependency network",
                    "description": f"Project has {total_dependencies} dependencies for {len(task_breakdown.subtasks)} tasks",
                    "level": RiskLevel.MEDIUM,
                    "probability": 0.6,
                    "impact": 0.7,
                    "mitigation": "Simplify task dependencies where possible",
                    "type": "technical"
                })
        
        return risks
    
    def _identify_quality_risks(self, project_id: str) -> List[Dict[str, Any]]:
        """Identify quality-related risks"""
        risks = []
        
        # Check for quality metrics
        if project_id in self.performance_metrics:
            metrics = self.performance_metrics[project_id]
            
            if "quality" in metrics and metrics["quality"] < 0.7:
                risks.append({
                    "title": "Low quality metrics",
                    "description": f"Project quality score is {metrics['quality']:.1%}",
                    "level": RiskLevel.HIGH,
                    "probability": 0.8,
                    "impact": 0.9,
                    "mitigation": "Implement additional quality assurance measures",
                    "type": "quality"
                })
        
        return risks
    
    def _generate_risk_matrix(self, risks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a risk matrix from identified risks"""
        matrix = {
            "low": {"count": 0, "risks": []},
            "medium": {"count": 0, "risks": []},
            "high": {"count": 0, "risks": []},
            "critical": {"count": 0, "risks": []}
        }
        
        for risk in risks:
            level = risk["level"].lower()
            if level in matrix:
                matrix[level]["count"] += 1
                matrix[level]["risks"].append(risk)
        
        return matrix
    
    async def plan_resources(self, project_id: str, resource_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plan resources for a project
        
        Args:
            project_id: ID of the project
            resource_spec: Resource planning specification
            
        Returns:
            Dictionary with resource plan
        """
        print(f"💰 {self.name}: Planning resources for project {project_id}")
        
        resources_spec = resource_spec.get("resources", [])
        budget = resource_spec.get("budget", 0.0)
        timeline = resource_spec.get("timeline", {})
        
        # Create resources
        resources = []
        for res_spec in resources_spec:
            resource_id = res_spec.get("resource_id", f"res_{len(self.resources) + 1}")
            name = res_spec.get("name", "Unnamed Resource")
            res_type = res_spec.get("type", "human")
            allocated = res_spec.get("allocated", 0.0)
            available = res_spec.get("available", 0.0)
            cost = res_spec.get("cost", 0.0)
            schedule = res_spec.get("schedule", {})
            
            resource = Resource(
                resource_id=resource_id,
                name=name,
                type=res_type,
                allocated=allocated,
                available=available,
                cost=cost,
                schedule=schedule
            )
            
            self.resources[resource_id] = resource
            resources.append(resource_id)
        
        # Generate resource allocation plan
        allocation_plan = self._generate_allocation_plan(project_id, resources, budget, timeline)
        
        result = {
            "project_id": project_id,
            "resources": resources,
            "budget": budget,
            "timeline": timeline,
            "allocation_plan": allocation_plan,
            "status": "planned"
        }
        
        print(f"✅ {self.name}: Resources planned for project {project_id}")
        return result
    
    def _generate_allocation_plan(self, project_id: str, resources: List[str], budget: float, timeline: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a resource allocation plan"""
        plan = {
            "project_id": project_id,
            "resources": [],
            "budget_allocation": {},
            "timeline": timeline,
            "total_cost": 0.0
        }
        
        # Add resource allocations
        for resource_id in resources:
            if resource_id in self.resources:
                resource = self.resources[resource_id]
                plan["resources"].append({
                    "resource_id": resource_id,
                    "name": resource.name,
                    "type": resource.type,
                    "allocated": resource.allocated,
                    "available": resource.available,
                    "cost": resource.cost,
                    "schedule": resource.schedule
                })
                plan["total_cost"] += resource.cost
        
        # Calculate budget allocation
        if budget > 0:
            for resource_id in resources:
                if resource_id in self.resources:
                    resource = self.resources[resource_id]
                    percentage = (resource.cost / plan["total_cost"]) * 100 if plan["total_cost"] > 0 else 0
                    plan["budget_allocation"][resource_id] = {
                        "amount": resource.cost,
                        "percentage": percentage
                    }
        
        return plan
    
    async def update_progress(self, project_id: str, update_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update project progress
        
        Args:
            project_id: ID of the project
            update_spec: Progress update specification
            
        Returns:
            Dictionary with progress update
        """
        print(f"📈 {self.name}: Updating progress for project {project_id}")
        
        update_id = update_spec.get("update_id", f"update_{len(self.progress_updates) + 1}")
        progress = update_spec.get("progress", 0.0)
        notes = update_spec.get("notes", "")
        issues = update_spec.get("issues", [])
        next_steps = update_spec.get("next_steps", [])
        
        # Create progress update
        progress_update = ProgressUpdate(
            update_id=update_id,
            project_id=project_id,
            timestamp=datetime.now().isoformat(),
            progress=progress,
            notes=notes,
            issues=issues,
            next_steps=next_steps
        )
        
        self.progress_updates[update_id] = progress_update
        
        # Update project metrics
        if project_id not in self.performance_metrics:
            self.performance_metrics[project_id] = {}
        
        self.performance_metrics[project_id]["progress"] = progress
        
        # Generate progress report
        progress_report = self._generate_progress_report(project_id, progress_update)
        
        result = {
            "update_id": update_id,
            "project_id": project_id,
            "progress": progress,
            "notes": notes,
            "issues": issues,
            "next_steps": next_steps,
            "progress_report": progress_report,
            "status": "updated"
        }
        
        print(f"✅ {self.name}: Progress updated for project {project_id} to {progress:.1%}")
        return result
    
    def _generate_progress_report(self, project_id: str, progress_update: ProgressUpdate) -> Dict[str, Any]:
        """Generate a progress report"""
        report = {
            "project_id": project_id,
            "update_id": progress_update.update_id,
            "timestamp": progress_update.timestamp,
            "progress": progress_update.progress,
            "notes": progress_update.notes,
            "issues": progress_update.issues,
            "next_steps": progress_update.next_steps,
            "trends": {},
            "recommendations": []
        }
        
        # Calculate trends
        if project_id in self.progress_updates:
            updates = [u for u in self.progress_updates.values() if u.project_id == project_id]
            if len(updates) > 1:
                # Calculate progress trend
                progresses = [u.progress for u in sorted(updates, key=lambda x: x.timestamp)]
                if len(progresses) >= 2:
                    trend = progresses[-1] - progresses[-2]
                    report["trends"]["progress"] = "improving" if trend > 0 else "declining" if trend < 0 else "stable"
        
        # Generate recommendations
        if progress_update.issues:
            report["recommendations"].append(f"Address {len(progress_update.issues)} identified issues")
        
        if progress_update.progress < 0.5 and progress_update.next_steps:
            report["recommendations"].append("Focus on completing next steps to accelerate progress")
        
        return report
    
    async def generate_timeline(self, project_id: str, timeline_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a project timeline
        
        Args:
            project_id: ID of the project
            timeline_spec: Timeline specification
            
        Returns:
            Dictionary with project timeline
        """
        print(f"📅 {self.name}: Generating timeline for project {project_id}")
        
        # Check if project plan exists
        if project_id not in [p.project_id for p in self.project_plans.values()]:
            raise ValueError(f"Project plan for {project_id} not found")
        
        project_plan = next(p for p in self.project_plans.values() if p.project_id == project_id)
        
        # Generate timeline
        timeline = {
            "project_id": project_id,
            "phases": [],
            "milestones": [],
            "critical_path": [],
            "gantt_chart": {}
        }
        
        # Add phases to timeline
        for phase_id, phase in project_plan.phases.items():
            phase_timeline = {
                "phase_id": phase_id,
                "name": phase["name"],
                "start_date": phase["start_date"],
                "end_date": phase["end_date"],
                "duration": phase["duration"],
                "deliverables": phase["deliverables"],
                "status": phase["status"]
            }
            timeline["phases"].append(phase_timeline)
        
        # Add milestones to timeline
        for milestone in project_plan.milestones:
            milestone_timeline = {
                "milestone_id": milestone["milestone_id"],
                "name": milestone["name"],
                "due_date": milestone["due_date"],
                "description": milestone["description"],
                "status": milestone["status"],
                "completed": milestone["completed"]
            }
            timeline["milestones"].append(milestone_timeline)
        
        # Generate Gantt chart data
        timeline["gantt_chart"] = self._generate_gantt_data(project_plan)
        
        # Identify critical path
        if project_id in self.task_breakdowns:
            task_breakdown = self.task_breakdowns[project_id]
            timeline["critical_path"] = task_breakdown.critical_path
        
        result = {
            "project_id": project_id,
            "timeline": timeline,
            "status": "generated"
        }
        
        print(f"✅ {self.name}: Timeline generated for project {project_id}")
        return result
    
    async def get_project_status(self) -> Dict[str, Any]:
        """
        Get the current project management status
        
        Returns:
            Dictionary with project management status
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "current_project": self.current_project,
            "current_phase": self.current_phase.value if self.current_phase else None,
            "project_plans_count": len(self.project_plans),
            "task_breakdowns_count": len(self.task_breakdowns),
            "risks_count": len(self.risks),
            "resources_count": len(self.resources),
            "progress_updates_count": len(self.progress_updates),
            "performance_metrics": self.performance_metrics
        }
    
    def reset(self) -> None:
        """Reset agent state"""
        self.current_project = None
        self.current_phase = None
        self.project_plans.clear()
        self.task_breakdowns.clear()
        self.risks.clear()
        self.resources.clear()
        self.progress_updates.clear()
        self.performance_metrics.clear()
        print(f"🔄 {self.name}: Agent state reset")
