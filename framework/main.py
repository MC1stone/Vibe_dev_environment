#!/usr/bin/env python3
"""
Main Entry Point for the Multi-Agent Framework

This module provides the main interface for initializing and running the multi-agent team.
"""

import asyncio
import json
import yaml
from typing import Dict, List, Optional, Any
from datetime import datetime

from agents import (
    # Specialist Agents
    BackendAgent,
    FrontendAgent,
    DataAnalysisAgent,
    MCPAgent,
    N8NAgent,
    CrewAIAgent,
    FaissAgent,
    PostgreSQLAgent,
    QuadrantAgent,
    QuartoAgent,
    # Overview Agents
    TeamLeadAgent,
    ProjectManagerAgent,
    TaskCoordinatorAgent,
    # Quality Agents
    QualityAssuranceAgent,
    CodeReviewAgent,
    TestingAgent,
)

from orchestration import (
    TeamOrchestrator,
    TaskDistributor,
    CommunicationBus,
    WorkflowManager,
)


class MultiAgentFramework:
    """
    Main class for the Multi-Agent Framework
    
    This class provides a high-level interface for working with the multi-agent team.
    It handles team initialization, project execution, and result aggregation.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the multi-agent framework
        
        Args:
            config_path: Path to team configuration file (optional)
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.agents: Dict[str, Any] = {}
        self.orchestrator: Optional[TeamOrchestrator] = None
        self.communication_bus: Optional[CommunicationBus] = None
        self.workflow_manager: Optional[WorkflowManager] = None
        self.task_distributor: Optional[TaskDistributor] = None
        
        # Initialize components
        self._initialize_components()
        
        # Load configuration
        if config_path:
            self.load_config(config_path)
    
    def _initialize_components(self) -> None:
        """Initialize framework components"""
        print("🚀 Initializing Multi-Agent Framework components...")
        
        # Initialize orchestrator
        self.orchestrator = TeamOrchestrator()
        print("✅ Team Orchestrator initialized")
        
        # Initialize communication bus
        self.communication_bus = CommunicationBus()
        print("✅ Communication Bus initialized")
        
        # Initialize workflow manager
        self.workflow_manager = WorkflowManager()
        print("✅ Workflow Manager initialized")
        
        # Initialize task distributor
        self.task_distributor = TaskDistributor()
        print("✅ Task Distributor initialized")
        
        print("🎉 All components initialized successfully!")
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load team configuration from a YAML file
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Dictionary with loaded configuration
        """
        print(f"📖 Loading configuration from {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            print(f"✅ Configuration loaded successfully")
            return self.config
            
        except FileNotFoundError:
            print(f"⚠️  Configuration file {config_path} not found, using defaults")
            self._load_default_config()
            return self.config
        except yaml.YAMLError as e:
            print(f"❌ Error loading configuration: {e}")
            self._load_default_config()
            return self.config
    
    def _load_default_config(self) -> None:
        """Load default configuration"""
        self.config = {
            "team": {
                "name": "Default Team",
                "description": "Default multi-agent team configuration"
            },
            "orchestrator": {
                "max_concurrent_projects": 5,
                "max_agents_per_project": 10,
                "task_timeout": 3600,
                "project_timeout": 86400,
                "retry_attempts": 3
            },
            "agents": []
        }
    
    async def initialize_team(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Initialize the team with a configuration
        
        Args:
            config: Team configuration (optional, uses loaded config if not provided)
            
        Returns:
            Dictionary with initialization results
        """
        print("🚀 Initializing team...")
        
        # Use provided config or loaded config
        team_config = config or self.config
        
        # Initialize orchestrator
        if self.orchestrator:
            init_result = await self.orchestrator.initialize_team(team_config)
        else:
            raise RuntimeError("Orchestrator not initialized")
        
        # Register agents
        agents_config = team_config.get("agents", [])
        for agent_config in agents_config:
            await self._register_agent(agent_config)
        
        # Initialize communication bus
        if self.communication_bus:
            await self.communication_bus.initialize()
        
        # Initialize workflow manager
        if self.workflow_manager:
            await self.workflow_manager.initialize()
        
        # Initialize task distributor
        if self.task_distributor:
            await self.task_distributor.initialize(self.agents)
        
        print(f"✅ Team initialized with {len(self.agents)} agents")
        return init_result
    
    async def _register_agent(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register an agent with the framework
        
        Args:
            agent_config: Agent configuration
            
        Returns:
            Dictionary with registration results
        """
        agent_id = agent_config.get("agent_id", "")
        module_path = agent_config.get("module", "")
        
        try:
            # Dynamically import and instantiate the agent class
            module_parts = module_path.split('.')
            module_name = '.'.join(module_parts[:-1])
            class_name = module_parts[-1]
            
            # Import the module
            import importlib
            module = importlib.import_module(module_name)
            
            # Get the class
            agent_class = getattr(module, class_name)
            
            # Instantiate the agent
            agent = agent_class()
            
            # Register with orchestrator
            if self.orchestrator:
                await self.orchestrator.register_agent(agent_config)
            
            # Store agent reference
            self.agents[agent_id] = agent
            
            print(f"✅ Agent {agent_config.get('name', agent_id)} registered")
            return {"status": "success", "agent_id": agent_id}
            
        except Exception as e:
            print(f"❌ Error registering agent {agent_id}: {e}")
            return {"status": "error", "agent_id": agent_id, "error": str(e)}
    
    async def create_project(self, project_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new project
        
        Args:
            project_spec: Project specification
            
        Returns:
            Dictionary with project creation results
        """
        print(f"📁 Creating project: {project_spec.get('name', 'Unnamed')}")
        
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
        
        result = await self.orchestrator.create_project(project_spec)
        return result
    
    async def execute_project(self, project_id: str, execution_spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a project with the team
        
        Args:
            project_id: ID of the project to execute
            execution_spec: Execution specification (optional)
            
        Returns:
            Dictionary with execution results
        """
        print(f"▶️ Executing project: {project_id}")
        
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
        
        execution_spec = execution_spec or {}
        result = await self.orchestrator.execute_project(project_id, execution_spec)
        return result
    
    async def monitor_project(self, project_id: str) -> Dict[str, Any]:
        """
        Monitor the status of a project
        
        Args:
            project_id: ID of the project to monitor
            
        Returns:
            Dictionary with monitoring results
        """
        print(f"📊 Monitoring project: {project_id}")
        
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
        
        result = await self.orchestrator.monitor_project(project_id)
        return result
    
    async def get_team_status(self) -> Dict[str, Any]:
        """
        Get the current team status
        
        Returns:
            Dictionary with team status
        """
        print("📊 Getting team status...")
        
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
        
        result = await self.orchestrator.get_team_status()
        return result
    
    async def shutdown(self) -> Dict[str, Any]:
        """
        Shutdown the framework
        
        Returns:
            Dictionary with shutdown results
        """
        print("🛑 Shutting down Multi-Agent Framework...")
        
        results = {}
        
        # Shutdown components
        if self.orchestrator:
            results["orchestrator"] = await self.orchestrator.shutdown()
        
        if self.communication_bus:
            results["communication_bus"] = await self.communication_bus.shutdown()
        
        if self.workflow_manager:
            results["workflow_manager"] = await self.workflow_manager.shutdown()
        
        if self.task_distributor:
            results["task_distributor"] = await self.task_distributor.shutdown()
        
        print("✅ Multi-Agent Framework shutdown completed")
        return results
    
    def get_agent(self, agent_id: str) -> Optional[Any]:
        """
        Get a specific agent by ID
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[str]:
        """
        List all registered agent IDs
        
        Returns:
            List of agent IDs
        """
        return list(self.agents.keys())
    
    def list_projects(self) -> List[str]:
        """
        List all project IDs
        
        Returns:
            List of project IDs
        """
        if self.orchestrator:
            return list(self.orchestrator.projects.keys())
        return []


# Convenience functions for direct usage
def create_framework(config_path: Optional[str] = None) -> MultiAgentFramework:
    """
    Create a new Multi-Agent Framework instance
    
    Args:
        config_path: Path to team configuration file (optional)
        
    Returns:
        MultiAgentFramework instance
    """
    return MultiAgentFramework(config_path)


async def run_project(project_spec: Dict[str, Any], config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to create a framework and run a project
    
    Args:
        project_spec: Project specification
        config_path: Path to team configuration file (optional)
        
    Returns:
        Dictionary with project execution results
    """
    # Create framework
    framework = create_framework(config_path)
    
    try:
        # Initialize team
        await framework.initialize_team()
        
        # Create project
        project = await framework.create_project(project_spec)
        project_id = project["project_id"]
        
        # Execute project
        result = await framework.execute_project(project_id)
        
        return result
        
    finally:
        # Shutdown framework
        await framework.shutdown()


# Example usage
async def main():
    """Example usage of the Multi-Agent Framework"""
    
    # Create a project specification
    project_spec = {
        "name": "My Software Project",
        "description": "A comprehensive software project with backend, frontend, and data analysis",
        "requirements": {
            "backend": {
                "api": True,
                "database": True,
                "implementation": True,
                "testing": True
            },
            "frontend": {
                "ui_design": True,
                "components": True,
                "pages": True,
                "testing": True
            },
            "data_analysis": {
                "data_loading": True,
                "eda": True,
                "feature_engineering": False,
                "model_training": False
            },
            "tools": ["postgresql", "faiss"]
        }
    }
    
    # Run the project
    result = await run_project(project_spec)
    
    # Print results
    print("\n" + "="*50)
    print("PROJECT EXECUTION RESULTS")
    print("="*50)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
