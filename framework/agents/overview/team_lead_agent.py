"""
Team Lead Agent - Overall Team Coordination and Leadership

Responsibilities:
- Team oversight and direction
- Strategic planning
- Resource allocation
- Conflict resolution
- Performance monitoring
- Stakeholder communication
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
    WORKING = "working"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    BLOCKED = "blocked"


class Priority(Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TeamMember:
    """Represents a team member (agent)"""
    agent_id: str
    name: str
    role: str
    status: TeamStatus = TeamStatus.IDLE
    current_task: Optional[str] = None
    workload: float = 0.0  # 0-1
    performance: float = 0.0  # 0-1
    skills: List[str] = field(default_factory=list)


@dataclass
class Project:
    """Represents a project being worked on"""
    project_id: str
    name: str
    description: str = ""
    start_date: str = ""
    end_date: str = ""
    status: str = "planned"  # "planned", "in_progress", "completed", "on_hold", "cancelled"
    priority: Priority = Priority.MEDIUM
    budget: Optional[float] = None
    team: List[str] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class Task:
    """Represents a task to be completed"""
    task_id: str
    name: str
    description: str = ""
    project_id: Optional[str] = None
    assigned_to: Optional[str] = None
    status: str = "todo"  # "todo", "in_progress", "done", "blocked", "cancelled"
    priority: Priority = Priority.MEDIUM
    start_date: str = ""
    due_date: str = ""
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    dependencies: List[str] = field(default_factory=list)


@dataclass
class Decision:
    """Represents a team decision"""
    decision_id: str
    title: str
    description: str = ""
    options: List[str] = field(default_factory=list)
    chosen_option: Optional[str] = None
    rationale: str = ""
    date: str = ""
    stakeholders: List[str] = field(default_factory=list)


@dataclass
class TeamLeadAgent:
    """
    Team Lead Agent
    
    This agent provides overall leadership and coordination for the multi-agent team.
    It oversees all agents, manages resources, and ensures the team works effectively together.
    """
    
    agent_id: str = "team_lead_agent_001"
    name: str = "Team Lead"
    description: str = "Overall team coordination and leadership"
    version: str = "1.0.0"
    
    # Team state
    team_members: Dict[str, TeamMember] = field(default_factory=dict)
    projects: Dict[str, Project] = field(default_factory=dict)
    tasks: Dict[str, Task] = field(default_factory=dict)
    decisions: Dict[str, Decision] = field(default_factory=dict)
    
    # Current state
    current_project: Optional[str] = None
    current_focus: str = "overall_coordination"
    
    # Performance metrics
    team_performance: Dict[str, float] = field(default_factory=dict)
    project_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Communication log
    communication_log: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize the agent"""
        self._initialize_team()
    
    def _initialize_team(self) -> None:
        """Initialize with default team structure"""
        # This will be populated with actual agents when they're registered
        pass
    
    async def register_agent(self, agent_id: str, agent_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new agent with the team
        
        Args:
            agent_id: ID of the agent
            agent_info: Agent information
            
        Returns:
            Dictionary with registration results
        """
        print(f"👤 {self.name}: Registering agent {agent_id}")
        
        name = agent_info.get("name", "Unknown Agent")
        role = agent_info.get("role", "specialist")
        skills = agent_info.get("skills", [])
        
        # Create team member
        team_member = TeamMember(
            agent_id=agent_id,
            name=name,
            role=role,
            status=TeamStatus.IDLE,
            workload=0.0,
            performance=0.5,  # Start with average performance
            skills=skills
        )
        
        self.team_members[agent_id] = team_member
        
        # Log registration
        self._log_communication(
            "agent_registration",
            f"Agent {name} ({agent_id}) registered as {role}",
            {"agent_id": agent_id, "name": name, "role": role, "skills": skills}
        )
        
        result = {
            "agent_id": agent_id,
            "name": name,
            "role": role,
            "status": "registered",
            "skills": skills
        }
        
        print(f"✅ {self.name}: Agent {name} registered successfully")
        return result
    
    async def create_project(self, project_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new project
        
        Args:
            project_spec: Project specification
            
        Returns:
            Dictionary with project configuration
        """
        print(f"🚀 {self.name}: Creating project {project_spec.get('name', 'Unnamed')}")
        
        project_id = project_spec.get("project_id", f"project_{len(self.projects) + 1}")
        project_name = project_spec.get("name", "Unnamed Project")
        description = project_spec.get("description", "")
        start_date = project_spec.get("start_date", datetime.now().isoformat())
        end_date = project_spec.get("end_date", "")
        priority_str = project_spec.get("priority", "medium")
        budget = project_spec.get("budget")
        team = project_spec.get("team", [])
        dependencies = project_spec.get("dependencies", [])
        
        # Validate priority
        try:
            priority = Priority(priority_str)
        except ValueError:
            priority = Priority.MEDIUM
            print(f"⚠️  Priority {priority_str} not valid, defaulting to MEDIUM")
        
        # Create project
        project = Project(
            project_id=project_id,
            name=project_name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            priority=priority,
            budget=budget,
            team=team,
            dependencies=dependencies
        )
        
        self.projects[project_id] = project
        self.current_project = project_id
        
        # Initialize project metrics
        self.project_metrics[project_id] = {
            "progress": 0.0,
            "quality": 0.0,
            "timeliness": 0.0,
            "budget_adherence": 1.0
        }
        
        # Log project creation
        self._log_communication(
            "project_creation",
            f"Project {project_name} created with ID {project_id}",
            {"project_id": project_id, "name": project_name, "priority": priority.value}
        )
        
        result = {
            "project_id": project_id,
            "name": project_name,
            "description": description,
            "start_date": start_date,
            "end_date": end_date,
            "priority": priority.value,
            "budget": budget,
            "team": team,
            "dependencies": dependencies,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Project {project_name} created successfully")
        return result
    
    async def assign_task(self, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assign a task to a team member
        
        Args:
            task_spec: Task specification
            
        Returns:
            Dictionary with assignment results
        """
        print(f"📋 {self.name}: Assigning task {task_spec.get('name', 'Unnamed')}")
        
        task_id = task_spec.get("task_id", f"task_{len(self.tasks) + 1}")
        task_name = task_spec.get("name", "Unnamed Task")
        description = task_spec.get("description", "")
        project_id = task_spec.get("project_id")
        assigned_to = task_spec.get("assigned_to")
        priority_str = task_spec.get("priority", "medium")
        start_date = task_spec.get("start_date", datetime.now().isoformat())
        due_date = task_spec.get("due_date", "")
        estimated_hours = task_spec.get("estimated_hours", 0.0)
        dependencies = task_spec.get("dependencies", [])
        
        # Validate priority
        try:
            priority = Priority(priority_str)
        except ValueError:
            priority = Priority.MEDIUM
            print(f"⚠️  Priority {priority_str} not valid, defaulting to MEDIUM")
        
        # Validate project
        if project_id and project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        # Validate assignee
        if assigned_to and assigned_to not in self.team_members:
            raise ValueError(f"Team member {assigned_to} not found")
        
        # Create task
        task = Task(
            task_id=task_id,
            name=task_name,
            description=description,
            project_id=project_id,
            assigned_to=assigned_to,
            priority=priority,
            start_date=start_date,
            due_date=due_date,
            estimated_hours=estimated_hours,
            dependencies=dependencies
        )
        
        self.tasks[task_id] = task
        
        # Update team member status
        if assigned_to and assigned_to in self.team_members:
            member = self.team_members[assigned_to]
            member.status = TeamStatus.WORKING
            member.current_task = task_id
            member.workload = min(member.workload + estimated_hours / 40, 1.0)  # Assuming 40h work week
        
        # Update project
        if project_id and project_id in self.projects:
            project = self.projects[project_id]
            project.tasks.append(task_id)
            if assigned_to:
                project.team.append(assigned_to)
        
        # Log task assignment
        self._log_communication(
            "task_assignment",
            f"Task {task_name} assigned to {assigned_to or 'unassigned'}",
            {
                "task_id": task_id,
                "name": task_name,
                "assigned_to": assigned_to,
                "priority": priority.value,
                "project_id": project_id
            }
        )
        
        result = {
            "task_id": task_id,
            "name": task_name,
            "description": description,
            "project_id": project_id,
            "assigned_to": assigned_to,
            "priority": priority.value,
            "start_date": start_date,
            "due_date": due_date,
            "estimated_hours": estimated_hours,
            "dependencies": dependencies,
            "status": "assigned"
        }
        
        print(f"✅ {self.name}: Task {task_name} assigned successfully")
        return result
    
    async def monitor_team_status(self) -> Dict[str, Any]:
        """
        Monitor the current status of the team
        
        Returns:
            Dictionary with team status information
        """
        print(f"📊 {self.name}: Monitoring team status")
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "team_members": [],
            "projects": [],
            "tasks": [],
            "overall_status": "healthy",
            "warnings": [],
            "recommendations": []
        }
        
        # Check team members
        for agent_id, member in self.team_members.items():
            member_status = {
                "agent_id": agent_id,
                "name": member.name,
                "role": member.role,
                "status": member.status.value,
                "workload": member.workload,
                "performance": member.performance,
                "current_task": member.current_task,
                "skills": member.skills
            }
            status["team_members"].append(member_status)
            
            # Check for issues
            if member.workload > 0.8:
                status["warnings"].append(f"{member.name} is overloaded (workload: {member.workload:.1%})")
            if member.performance < 0.3:
                status["warnings"].append(f"{member.name} has low performance ({member.performance:.1%})")
        
        # Check projects
        for project_id, project in self.projects.items():
            project_status = {
                "project_id": project_id,
                "name": project.name,
                "status": project.status,
                "priority": project.priority.value,
                "start_date": project.start_date,
                "end_date": project.end_date,
                "team_size": len(project.team),
                "task_count": len(project.tasks)
            }
            status["projects"].append(project_status)
            
            # Check for issues
            if project.status == "blocked":
                status["warnings"].append(f"Project {project.name} is blocked")
            if project.end_date and project.end_date < datetime.now().isoformat():
                status["warnings"].append(f"Project {project.name} is overdue")
        
        # Check tasks
        for task_id, task in self.tasks.items():
            task_status = {
                "task_id": task_id,
                "name": task.name,
                "status": task.status,
                "priority": task.priority.value,
                "assigned_to": task.assigned_to,
                "due_date": task.due_date,
                "estimated_hours": task.estimated_hours,
                "actual_hours": task.actual_hours
            }
            status["tasks"].append(task_status)
            
            # Check for issues
            if task.status == "blocked":
                status["warnings"].append(f"Task {task.name} is blocked")
            if task.due_date and task.due_date < datetime.now().isoformat():
                status["warnings"].append(f"Task {task.name} is overdue")
        
        # Generate recommendations
        idle_members = [m for m in self.team_members.values() if m.status == TeamStatus.IDLE]
        if idle_members and [t for t in self.tasks.values() if t.status == "todo"]:
            status["recommendations"].append(f"Assign tasks to {len(idle_members)} idle team members")
        
        overloaded_members = [m for m in self.team_members.values() if m.workload > 0.8]
        if overloaded_members:
            status["recommendations"].append(f"Redistribute workload from {len(overloaded_members)} overloaded members")
        
        # Determine overall status
        if status["warnings"]:
            status["overall_status"] = "needs_attention"
        if any(w for w in status["warnings"] if "blocked" in w.lower()):
            status["overall_status"] = "blocked"
        
        # Log monitoring
        self._log_communication(
            "team_monitoring",
            f"Team status: {status['overall_status']}",
            {"status": status["overall_status"], "warnings": len(status["warnings"]), "recommendations": len(status["recommendations"])}
        )
        
        print(f"✅ {self.name}: Team status monitoring completed")
        return status
    
    async def make_decision(self, decision_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a team decision
        
        Args:
            decision_spec: Decision specification
            
        Returns:
            Dictionary with decision results
        """
        print(f"🤔 {self.name}: Making decision: {decision_spec.get('title', 'Unnamed')}")
        
        decision_id = decision_spec.get("decision_id", f"decision_{len(self.decisions) + 1}")
        title = decision_spec.get("title", "Unnamed Decision")
        description = decision_spec.get("description", "")
        options = decision_spec.get("options", [])
        stakeholders = decision_spec.get("stakeholders", [])
        
        # Create decision
        decision = Decision(
            decision_id=decision_id,
            title=title,
            description=description,
            options=options,
            date=datetime.now().isoformat(),
            stakeholders=stakeholders
        )
        
        self.decisions[decision_id] = decision
        
        # Log decision
        self._log_communication(
            "decision_making",
            f"Decision {title} created with {len(options)} options",
            {"decision_id": decision_id, "title": title, "options": options}
        )
        
        result = {
            "decision_id": decision_id,
            "title": title,
            "description": description,
            "options": options,
            "stakeholders": stakeholders,
            "status": "pending",
            "date": decision.date
        }
        
        print(f"✅ {self.name}: Decision {title} created, awaiting choice")
        return result
    
    async def resolve_decision(self, decision_id: str, choice: str, rationale: str = "") -> Dict[str, Any]:
        """
        Resolve a team decision
        
        Args:
            decision_id: ID of the decision
            choice: Chosen option
            rationale: Rationale for the choice
            
        Returns:
            Dictionary with decision resolution
        """
        print(f"✅ {self.name}: Resolving decision {decision_id}")
        
        if decision_id not in self.decisions:
            raise ValueError(f"Decision {decision_id} not found")
        
        decision = self.decisions[decision_id]
        
        # Validate choice
        if choice not in decision.options:
            raise ValueError(f"Option {choice} not in decision options: {decision.options}")
        
        # Update decision
        decision.chosen_option = choice
        decision.rationale = rationale
        
        # Log decision resolution
        self._log_communication(
            "decision_resolution",
            f"Decision {decision.title} resolved: {choice}",
            {"decision_id": decision_id, "choice": choice, "rationale": rationale}
        )
        
        result = {
            "decision_id": decision_id,
            "title": decision.title,
            "chosen_option": choice,
            "rationale": rationale,
            "date": decision.date,
            "status": "resolved"
        }
        
        print(f"✅ {self.name}: Decision {decision.title} resolved with choice: {choice}")
        return result
    
    async def allocate_resources(self, allocation_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Allocate resources to projects or tasks
        
        Args:
            allocation_spec: Resource allocation specification
            
        Returns:
            Dictionary with allocation results
        """
        print(f"💰 {self.name}: Allocating resources")
        
        project_id = allocation_spec.get("project_id")
        task_id = allocation_spec.get("task_id")
        agent_id = allocation_spec.get("agent_id")
        resources = allocation_spec.get("resources", {})
        
        # Validate references
        if project_id and project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        if task_id and task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        if agent_id and agent_id not in self.team_members:
            raise ValueError(f"Agent {agent_id} not found")
        
        allocation = {
            "project_id": project_id,
            "task_id": task_id,
            "agent_id": agent_id,
            "resources": resources,
            "timestamp": datetime.now().isoformat(),
            "status": "allocated"
        }
        
        # Update project budget if specified
        if project_id and "budget" in resources:
            project = self.projects[project_id]
            if project.budget is not None:
                project.budget += resources["budget"]
        
        # Update team member workload if specified
        if agent_id and "workload" in resources:
            member = self.team_members[agent_id]
            member.workload = min(max(member.workload + resources["workload"], 0), 1)
        
        # Log allocation
        self._log_communication(
            "resource_allocation",
            f"Resources allocated to {project_id or task_id or agent_id}",
            allocation
        )
        
        print(f"✅ {self.name}: Resources allocated successfully")
        return allocation
    
    async def resolve_conflict(self, conflict_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve a team conflict
        
        Args:
            conflict_spec: Conflict specification
            
        Returns:
            Dictionary with conflict resolution
        """
        print(f"⚖️ {self.name}: Resolving conflict")
        
        conflict_id = conflict_spec.get("conflict_id", f"conflict_{len(self.communication_log) + 1}")
        title = conflict_spec.get("title", "Unnamed Conflict")
        description = conflict_spec.get("description", "")
        parties = conflict_spec.get("parties", [])
        resolution = conflict_spec.get("resolution", "")
        
        # Log conflict
        self._log_communication(
            "conflict",
            f"Conflict {title} identified",
            {"conflict_id": conflict_id, "title": title, "parties": parties}
        )
        
        # Generate resolution
        if not resolution:
            resolution = self._generate_conflict_resolution(conflict_spec)
        
        resolution_result = {
            "conflict_id": conflict_id,
            "title": title,
            "description": description,
            "parties": parties,
            "resolution": resolution,
            "status": "resolved",
            "timestamp": datetime.now().isoformat()
        }
        
        # Log resolution
        self._log_communication(
            "conflict_resolution",
            f"Conflict {title} resolved",
            resolution_result
        )
        
        print(f"✅ {self.name}: Conflict {title} resolved")
        return resolution_result
    
    def _generate_conflict_resolution(self, conflict_spec: Dict[str, Any]) -> str:
        """Generate a conflict resolution"""
        title = conflict_spec.get("title", "")
        description = conflict_spec.get("description", "")
        parties = conflict_spec.get("parties", [])
        
        # Simple conflict resolution logic
        if "priority" in description.lower():
            return "Prioritize tasks based on project requirements and deadlines. Higher priority tasks should be addressed first."
        elif "resource" in description.lower():
            return "Reallocate resources to balance workload. Consider bringing in additional help if needed."
        elif "technical" in description.lower():
            return "Schedule a technical discussion to align on the approach. Document the agreed solution."
        elif "communication" in description.lower():
            return "Improve communication channels. Schedule regular sync meetings and use shared documentation."
        else:
            return "Open dialogue between parties to understand concerns and find a mutually acceptable solution."
    
    async def generate_report(self, report_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a team report
        
        Args:
            report_spec: Report specification
            
        Returns:
            Dictionary with report content
        """
        print(f"📊 {self.name}: Generating team report")
        
        report_type = report_spec.get("type", "status")
        period = report_spec.get("period", "weekly")
        
        # Generate report based on type
        if report_type == "status":
            report = self._generate_status_report(period)
        elif report_type == "performance":
            report = self._generate_performance_report(period)
        elif report_type == "financial":
            report = self._generate_financial_report(period)
        else:
            report = self._generate_custom_report(report_spec)
        
        # Log report generation
        self._log_communication(
            "report_generation",
            f"{report_type} report generated for {period}",
            {"report_type": report_type, "period": period}
        )
        
        print(f"✅ {self.name}: {report_type} report generated")
        return report
    
    def _generate_status_report(self, period: str) -> Dict[str, Any]:
        """Generate a status report"""
        report = {
            "type": "status",
            "period": period,
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "projects": [],
            "team": [],
            "tasks": [],
            "recommendations": []
        }
        
        # Generate summary
        total_projects = len(self.projects)
        active_projects = len([p for p in self.projects.values() if p.status == "in_progress"])
        completed_projects = len([p for p in self.projects.values() if p.status == "completed"])
        
        report["summary"] = {
            "total_projects": total_projects,
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "team_size": len(self.team_members),
            "active_tasks": len([t for t in self.tasks.values() if t.status == "in_progress"]),
            "completed_tasks": len([t for t in self.tasks.values() if t.status == "done"])
        }
        
        # Add project statuses
        for project_id, project in self.projects.items():
            project_status = {
                "project_id": project_id,
                "name": project.name,
                "status": project.status,
                "progress": self.project_metrics.get(project_id, {}).get("progress", 0.0),
                "priority": project.priority.value,
                "team_size": len(project.team),
                "task_count": len(project.tasks)
            }
            report["projects"].append(project_status)
        
        # Add team status
        for agent_id, member in self.team_members.items():
            member_status = {
                "agent_id": agent_id,
                "name": member.name,
                "role": member.role,
                "status": member.status.value,
                "workload": member.workload,
                "performance": member.performance,
                "current_task": member.current_task
            }
            report["team"].append(member_status)
        
        # Add task status
        for task_id, task in self.tasks.items():
            task_status = {
                "task_id": task_id,
                "name": task.name,
                "status": task.status,
                "priority": task.priority.value,
                "assigned_to": task.assigned_to,
                "progress": 0.0  # Would be calculated based on subtasks
            }
            report["tasks"].append(task_status)
        
        # Generate recommendations
        if active_projects == 0:
            report["recommendations"].append("Consider starting new projects to keep the team productive")
        
        overloaded_members = [m for m in self.team_members.values() if m.workload > 0.8]
        if overloaded_members:
            report["recommendations"].append(f"Redistribute workload from {len(overloaded_members)} overloaded team members")
        
        return report
    
    def _generate_performance_report(self, period: str) -> Dict[str, Any]:
        """Generate a performance report"""
        report = {
            "type": "performance",
            "period": period,
            "timestamp": datetime.now().isoformat(),
            "team_performance": {},
            "project_performance": {},
            "trends": {},
            "recommendations": []
        }
        
        # Calculate team performance
        total_performance = sum(m.performance for m in self.team_members.values())
        avg_performance = total_performance / len(self.team_members) if self.team_members else 0
        
        report["team_performance"] = {
            "average": avg_performance,
            "high_performers": [m.name for m in self.team_members.values() if m.performance > 0.8],
            "needs_improvement": [m.name for m in self.team_members.values() if m.performance < 0.5]
        }
        
        # Calculate project performance
        for project_id, metrics in self.project_metrics.items():
            report["project_performance"][project_id] = {
                "progress": metrics.get("progress", 0.0),
                "quality": metrics.get("quality", 0.0),
                "timeliness": metrics.get("timeliness", 0.0),
                "budget_adherence": metrics.get("budget_adherence", 1.0)
            }
        
        # Generate trends
        report["trends"] = {
            "performance_trend": "stable",
            "workload_trend": "stable",
            "quality_trend": "improving"
        }
        
        # Generate recommendations
        if avg_performance < 0.6:
            report["recommendations"].append("Investigate reasons for below-average team performance")
        
        if report["team_performance"]["needs_improvement"]:
            report["recommendations"].append("Provide additional support or training to underperforming team members")
        
        return report
    
    def _generate_financial_report(self, period: str) -> Dict[str, Any]:
        """Generate a financial report"""
        report = {
            "type": "financial",
            "period": period,
            "timestamp": datetime.now().isoformat(),
            "budget_summary": {},
            "project_budgets": {},
            "recommendations": []
        }
        
        # Calculate budget summary
        total_budget = sum(p.budget or 0 for p in self.projects.values() if p.budget)
        allocated_budget = sum(p.budget or 0 for p in self.projects.values() if p.budget and p.status == "in_progress")
        
        report["budget_summary"] = {
            "total_budget": total_budget,
            "allocated_budget": allocated_budget,
            "remaining_budget": total_budget - allocated_budget
        }
        
        # Add project budgets
        for project_id, project in self.projects.items():
            if project.budget:
                report["project_budgets"][project_id] = {
                    "name": project.name,
                    "budget": project.budget,
                    "status": project.status,
                    "utilization": 0.0  # Would be calculated based on actual spending
                }
        
        # Generate recommendations
        if allocated_budget > total_budget * 0.8:
            report["recommendations"].append("Consider reallocating budget from lower priority projects")
        
        return report
    
    def _generate_custom_report(self, report_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a custom report"""
        report = {
            "type": "custom",
            "title": report_spec.get("title", "Custom Report"),
            "timestamp": datetime.now().isoformat(),
            "content": report_spec.get("content", {}),
            "metadata": report_spec.get("metadata", {})
        }
        
        return report
    
    def _log_communication(self, event_type: str, message: str, data: Dict[str, Any]) -> None:
        """Log a communication event"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "message": message,
            "data": data
        }
        self.communication_log.append(log_entry)
        
        # Keep log size manageable
        if len(self.communication_log) > 1000:
            self.communication_log = self.communication_log[-500:]
    
    async def get_team_status(self) -> Dict[str, Any]:
        """
        Get the current team status
        
        Returns:
            Dictionary with team status
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "current_project": self.current_project,
            "current_focus": self.current_focus,
            "team_size": len(self.team_members),
            "projects_count": len(self.projects),
            "tasks_count": len(self.tasks),
            "decisions_count": len(self.decisions),
            "communication_log_size": len(self.communication_log),
            "team_performance": self.team_performance,
            "project_metrics": self.project_metrics
        }
    
    def reset(self) -> None:
        """Reset agent state"""
        self.current_project = None
        self.current_focus = "overall_coordination"
        self.team_members.clear()
        self.projects.clear()
        self.tasks.clear()
        self.decisions.clear()
        self.team_performance.clear()
        self.project_metrics.clear()
        self.communication_log.clear()
        print(f"🔄 {self.name}: Agent state reset")
