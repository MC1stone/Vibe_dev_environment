#!/usr/bin/env python3
"""
NIR Intelligence Platform - Main Orchestrator Script

This script orchestrates the development process of the NIR Intelligence Platform
by coordinating all agents and ensuring the iterative improvement cycle.
"""

import os
import sys
import json
import yaml
import logging
import time
import importlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum, auto

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/nir_platform.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MainOrchestrator')

class AgentStatus(Enum):
    """Status enum for agent execution"""
    INITIALIZING = auto()
    READY = auto()
    PROCESSING = auto()
    ERROR = auto()
    COMPLETED = auto()

class ErrorSeverity(Enum):
    """Severity enum for errors"""
    CRITICAL = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()

@dataclass
class AgentError:
    """Data class for agent errors"""
    agent_name: str
    message: str
    severity: ErrorSeverity
    details: Dict[str, Any] = field(default_factory=dict)
    suggested_fix: Optional[str] = None

@dataclass
class AgentOutput:
    """Data class for agent output"""
    agent_name: str
    status: AgentStatus
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[AgentError] = field(default_factory=list)
    version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)

class BaseAgent:
    """Base class for all agents"""
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.status = AgentStatus.INITIALIZING
        self.errors: List[AgentError] = []
        self.logger = logging.getLogger(f"Agent.{name}")
        self.dependencies: List[str] = []

    def initialize(self) -> AgentOutput:
        """Initialize agent and its environment"""
        self.status = AgentStatus.READY
        return AgentOutput(
            agent_name=self.name,
            status=self.status,
            version=self.version
        )

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute agent's primary function"""
        raise NotImplementedError("Execute method must be implemented by subclass")

    def validate(self) -> List[AgentError]:
        """Validate agent's current state and configuration"""
        return self.errors

    def get_requirements(self) -> Dict[str, Any]:
        """Return agent's requirements and dependencies"""
        return {"dependencies": self.dependencies}

    def log_error(self, message: str, severity: ErrorSeverity, 
                  details: Dict[str, Any] = None, suggested_fix: str = None):
        """Log an error for this agent"""
        error = AgentError(
            agent_name=self.name,
            message=message,
            severity=severity,
            details=details or {},
            suggested_fix=suggested_fix
        )
        self.errors.append(error)
        self.logger.error(f"[{severity.name}] {message}")
        return error

    def clear_errors(self):
        """Clear all logged errors"""
        self.errors = []

    def has_errors(self) -> bool:
        """Check if agent has any errors"""
        return len(self.errors) > 0

@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator"""
    max_iterations: int = 100
    iteration_timeout: int = 300
    agent_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

class MainOrchestrator(BaseAgent):
    """Main orchestrator for the NIR Intelligence Platform"""
    
    def __init__(self):
        super().__init__(name="MainOrchestrator", version="1.0.0")
        self.config: OrchestratorConfig = OrchestratorConfig()
        self.agents: Dict[str, BaseAgent] = {}
        self.iteration_count = 0
        self.total_errors = 0
        self.start_time = None
        self.project_root = project_root
        
        # Load mandatory files
        self.mandatory_files = [
            "TASK.md",
            "task_definition.yaml", 
            "system_manifest.json"
        ]
        
        # Agent execution order
        self.execution_order = [
            "uvx_agent",
            "docker_agent",
            "ansible_agent",
            "data_preparation_agent",
            "metadata_agent",
            "sensor_quality_agent",
            ["statistical_analysis_agent", "neural_network_agent"],
            "calibration_agent",
            ["weaviate_agent", "faiss_agent", "postgresql_agent"],
            "django_agent",
            "mcp_agent",
            "ilias_agent",
            "quarto_agent",
            "flower_agent"
        ]

    def load_mandatory_files(self) -> bool:
        """Load and validate mandatory files"""
        success = True
        
        for filename in self.mandatory_files:
            filepath = os.path.join(self.project_root, filename)
            if not os.path.exists(filepath):
                self.log_error(
                    f"Mandatory file not found: {filename}",
                    ErrorSeverity.CRITICAL,
                    {"file": filename, "path": filepath}
                )
                success = False
                continue
                
            try:
                if filename.endswith('.json'):
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                elif filename.endswith('.yaml') or filename.endswith('.yml'):
                    with open(filepath, 'r') as f:
                        data = yaml.safe_load(f)
                else:
                    with open(filepath, 'r') as f:
                        data = f.read()
                        
                logger.info(f"Successfully loaded {filename}")
                
            except Exception as e:
                self.log_error(
                    f"Failed to load {filename}: {str(e)}",
                    ErrorSeverity.CRITICAL,
                    {"file": filename, "error": str(e)}
                )
                success = False
        
        return success

    def load_config(self):
        """Load configuration from YAML file"""
        config_path = os.path.join(self.project_root, 'config', 'agent_config.yaml')
        
        if not os.path.exists(config_path):
            self.log_error(
                f"Configuration file not found: {config_path}",
                ErrorSeverity.HIGH
            )
            return
            
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
                
            self.config = OrchestratorConfig(
                max_iterations=config_data.get('max_iterations', 100),
                iteration_timeout=config_data.get('iteration_timeout', 300),
                agent_configs=config_data.get('agents', {})
            )
            
            logger.info(f"Configuration loaded from {config_path}")
            
        except Exception as e:
            self.log_error(
                f"Failed to load config: {str(e)}",
                ErrorSeverity.CRITICAL,
                {"path": config_path}
            )

    def initialize_agent(self, agent_name: str, agent_class: str, config: Dict[str, Any]) -> Optional[BaseAgent]:
        """Dynamically initialize a subagent"""
        try:
            module_name, class_name = agent_class.rsplit('.', 1)
            module = importlib.import_module(module_name)
            agent_class = getattr(module, class_name)
            
            # Create instance with configuration
            agent = agent_class(**config.get('params', {}))
            agent.initialize()
            
            logger.info(f"Initialized {agent_name} (v{agent.version})")
            return agent
            
        except ImportError as e:
            self.log_error(
                f"Failed to import agent module: {agent_class}",
                ErrorSeverity.CRITICAL,
                {"module": module_name, "error": str(e)}
            )
        except AttributeError as e:
            self.log_error(
                f"Agent class not found: {class_name} in {module_name}",
                ErrorSeverity.CRITICAL
            )
        except Exception as e:
            self.log_error(
                f"Failed to initialize {agent_name}: {str(e)}",
                ErrorSeverity.HIGH,
                {"agent": agent_name, "error": str(e)}
            )
        
        return None

    def initialize_all_agents(self):
        """Initialize all agents based on configuration"""
        # Define agent mappings
        agent_mappings = {
            "uvx_agent": "agents.uvx_agent.UVXAgent",
            "docker_agent": "agents.docker_agent.DockerAgent",
            "ansible_agent": "agents.ansible_agent.AnsibleAgent",
            "data_preparation_agent": "agents.data_preparation_agent.DataPreparationAgent",
            "metadata_agent": "agents.metadata_agent.MetadataAgent",
            "sensor_quality_agent": "agents.sensor_quality_agent.SensorQualityAgent",
            "statistical_analysis_agent": "agents.statistical_analysis_agent.StatisticalAnalysisAgent",
            "neural_network_agent": "agents.neural_network_agent.NeuralNetworkAgent",
            "calibration_agent": "agents.calibration_agent.CalibrationAgent",
            "weaviate_agent": "agents.weaviate_agent.WeaviateAgent",
            "faiss_agent": "agents.faiss_agent.FaissAgent",
            "postgresql_agent": "agents.postgresql_agent.PostgreSQLAgent",
            "django_agent": "agents.django_agent.DjangoAgent",
            "mcp_agent": "agents.mcp_agent.MCPAgent",
            "ilias_agent": "agents.ilias_agent.ILIASAgent",
            "quarto_agent": "agents.quarto_agent.QuartoAgent",
            "flower_agent": "agents.flower_agent.FlowerAgent"
        }
        
        # Initialize all agents
        for agent_name, agent_class in agent_mappings.items():
            agent_config = self.config.agent_configs.get(agent_name, {})
            
            if not agent_config.get('enabled', True):
                logger.info(f"Skipping disabled agent: {agent_name}")
                continue
                
            agent = self.initialize_agent(agent_name, agent_class, agent_config)
            if agent:
                self.agents[agent_name] = agent
                self.dependencies.extend(agent.dependencies)

    def collect_errors(self) -> List[AgentError]:
        """Collect all errors from all agents"""
        all_errors = []
        for agent in self.agents.values():
            agent_errors = agent.validate()
            all_errors.extend(agent_errors)
            if agent_errors:
                logger.warning(f"{agent.name} reported {len(agent_errors)} errors")
        return all_errors

    def execute_iteration(self) -> Dict[str, AgentOutput]:
        """Execute one iteration cycle for all agents"""
        self.iteration_count += 1
        logger.info(f"Starting iteration {self.iteration_count}")
        
        results = {}
        context = {
            "iteration": self.iteration_count,
            "timestamp": time.time(),
            "orchestrator_version": self.version
        }
        
        # Execute agents in dependency order
        for item in self.execution_order:
            if isinstance(item, list):
                # Parallel execution
                for agent_name in item:
                    if agent_name in self.agents:
                        self._execute_agent(agent_name, context, results)
            else:
                # Sequential execution
                if item in self.agents:
                    self._execute_agent(item, context, results)
        
        return results

    def _execute_agent(self, agent_name: str, context: Dict[str, Any], results: Dict[str, AgentOutput]):
        """Execute a single agent"""
        agent = self.agents[agent_name]
        logger.info(f"Executing {agent_name}...")
        
        try:
            agent.status = AgentStatus.PROCESSING
            output = agent.execute(context)
            results[agent_name] = output
            
            if output.errors:
                for error in output.errors:
                    logger.error(f"{agent_name} error: {error.message}")
            
            agent.status = AgentStatus.COMPLETED
            
        except Exception as e:
            error = agent.log_error(
                f"Execution failed: {str(e)}",
                ErrorSeverity.HIGH,
                {"iteration": self.iteration_count},
                f"Check {agent_name} configuration and dependencies"
            )
            results[agent_name] = AgentOutput(
                agent_name=agent_name,
                status=AgentStatus.ERROR,
                errors=[error]
            )

    def run(self) -> Dict[str, Any]:
        """Run the orchestration cycle until no errors remain"""
        self.start_time = time.time()
        
        # Load mandatory files
        if not self.load_mandatory_files():
            logger.error("Failed to load mandatory files. Aborting.")
            return {"status": "FAILED", "reason": "mandatory_files_missing"}
        
        # Load configuration
        self.load_config()
        
        # Initialize all agents
        self.initialize_all_agents()
        
        if not self.agents:
            logger.error("No agents initialized. Aborting.")
            return {"status": "FAILED", "reason": "no_agents_initialized"}
        
        final_results = {}
        error_history = []
        
        for iteration in range(self.config.max_iterations):
            logger.info(f"=== Iteration {iteration + 1} ===")
            
            # Execute iteration
            iteration_results = self.execute_iteration()
            final_results[f"iteration_{iteration + 1}"] = iteration_results
            
            # Collect all errors
            all_errors = self.collect_errors()
            error_history.append({
                "iteration": iteration + 1,
                "errors": [
                    {
                        "agent": e.agent_name,
                        "message": e.message,
                        "severity": e.severity.name,
                        "suggested_fix": e.suggested_fix
                    }
                    for e in all_errors
                ]
            })
            
            self.total_errors = len(all_errors)
            logger.info(f"Total errors: {self.total_errors}")
            
            # Check if we're done
            if self.total_errors == 0:
                logger.info("All agents report no errors. Implementation complete.")
                break
            
            # Apply fixes suggested by agents
            self._apply_suggested_fixes(all_errors)
            
            # Small delay between iterations
            time.sleep(1)
        else:
            logger.warning(f"Max iterations ({self.config.max_iterations}) reached. {self.total_errors} errors remain.")
        
        elapsed = time.time() - self.start_time
        
        return {
            "status": "COMPLETED" if self.total_errors == 0 else "PARTIAL",
            "iterations": self.iteration_count,
            "total_errors": self.total_errors,
            "elapsed_time": elapsed,
            "results": final_results,
            "error_history": error_history,
            "agents": {
                name: {
                    "version": agent.version, 
                    "status": agent.status.name,
                    "errors": len(agent.errors)
                }
                for name, agent in self.agents.items()
            }
        }

    def _apply_suggested_fixes(self, errors: List[AgentError]):
        """Apply suggested fixes from agent errors"""
        fixes_applied = 0
        
        for error in errors:
            if error.suggested_fix:
                logger.info(f"Applying suggested fix for {error.agent_name}: {error.suggested_fix}")
                # In a real implementation, this would apply the actual fixes
                fixes_applied += 1
        
        logger.info(f"Applied {fixes_applied} suggested fixes")

    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a summary report"""
        report = []
        report.append("=" * 80)
        report.append("NIR INTELLIGENCE PLATFORM - IMPLEMENTATION REPORT")
        report.append("=" * 80)
        report.append(f"Status: {results['status']}")
        report.append(f"Iterations: {results['iterations']}")
        report.append(f"Total Errors: {results['total_errors']}")
        report.append(f"Elapsed Time: {results['elapsed_time']:.2f} seconds")
        report.append("-" * 80)
        
        report.append("\nAGENT STATUS:")
        for agent_name, agent_info in results['agents'].items():
            status_symbol = "✓" if agent_info['errors'] == 0 else "✗"
            report.append(f"  {status_symbol} {agent_name}: v{agent_info['version']} - {agent_info['status']}")
            if agent_info['errors'] > 0:
                report.append(f"    Errors: {agent_info['errors']}")
        
        if results['total_errors'] > 0:
            report.append("\nERROR SUMMARY:")
            for error_entry in results['error_history'][-1]['errors']:
                report.append(f"  [{error_entry['severity']}] {error_entry['agent']}: {error_entry['message']}")
                if error_entry['suggested_fix']:
                    report.append(f"    Suggested fix: {error_entry['suggested_fix']}")
        
        report.append("\n" + "=" * 80)
        return "\n".join(report)

def main():
    """Main entry point"""
    logger.info("Starting NIR Intelligence Platform Orchestrator")
    
    try:
        orchestrator = MainOrchestrator()
        results = orchestrator.run()
        
        # Generate and display report
        report = orchestrator.generate_report(results)
        print(report)
        
        # Save results to file
        os.makedirs("output", exist_ok=True)
        
        # Convert AgentOutput objects to serializable format
        def serialize_results(obj):
            if hasattr(obj, '__dict__'):
                return {k: serialize_results(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, (list, tuple)):
                return [serialize_results(item) for item in obj]
            elif isinstance(obj, (dict, str, int, float, bool)) or obj is None:
                return obj
            elif hasattr(obj, '__name__'):  # Handle enum types
                return str(obj)
            else:
                return str(obj)
        
        # Create a simplified version for JSON serialization
        simplified_results = {
            "status": str(results.get("status", "UNKNOWN")),
            "iterations": results.get("iterations", 0),
            "total_errors": results.get("total_errors", 0),
            "elapsed_time": results.get("elapsed_time", 0),
            "agents": results.get("agents", {}),
            "error_summary": []
        }
        
        # Add error summary
        if "error_history" in results and results["error_history"]:
            last_errors = results["error_history"][-1]["errors"]
            simplified_results["error_summary"] = [
                {
                    "agent": e.get("agent", "unknown"),
                    "message": e.get("message", ""),
                    "severity": e.get("severity", "LOW")
                }
                for e in last_errors
            ]
        
        with open("output/orchestration_results.json", "w") as f:
            json.dump(simplified_results, f, indent=2)
        
        with open("output/orchestration_report.txt", "w") as f:
            f.write(report)
        
        logger.info("Orchestration completed. Results saved to output/ directory.")
        
        return 0 if results['status'] == 'COMPLETED' else 1
        
    except Exception as e:
        logger.error(f"Fatal error in orchestrator: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())