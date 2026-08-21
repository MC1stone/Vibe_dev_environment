# NIR Intelligence Platform - Base Agent Class
# This class provides the foundation for all NIR platform agents

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


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
    """Base class for all NIR Intelligence Platform agents"""

    def __init__(self, name: str, version: str = "1.0.0", **kwargs):
        self.name = name
        self.version = version
        self.status = AgentStatus.INITIALIZING
        self.errors: List[AgentError] = []
        self.logger = logging.getLogger(f"Agent.{name}")
        self.dependencies: List[str] = []
        self.config = kwargs.get("config", {})

        # Initialize logging
        self._setup_logging()

    def _setup_logging(self):
        """Setup agent-specific logging"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def initialize(self) -> AgentOutput:
        """Initialize agent and its environment"""
        self.status = AgentStatus.READY
        self.logger.info(f"{self.name} v{self.version} initialized")
        return AgentOutput(
            agent_name=self.name, status=self.status, version=self.version, dependencies=self.dependencies
        )

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute agent's primary function - must be implemented by subclass"""
        raise NotImplementedError(f"Execute method must be implemented by {self.__class__.__name__}")

    def validate(self) -> List[AgentError]:
        """Validate agent's current state and configuration"""
        return self.errors

    def get_requirements(self) -> Dict[str, Any]:
        """Return agent's requirements and dependencies"""
        return {"dependencies": self.dependencies}

    def log_error(
        self, message: str, severity: ErrorSeverity, details: Dict[str, Any] = None, suggested_fix: str = None
    ) -> AgentError:
        """Log an error for this agent"""
        error = AgentError(
            agent_name=self.name, message=message, severity=severity, details=details or {}, suggested_fix=suggested_fix
        )
        self.errors.append(error)
        self.logger.error(f"[{severity.name}] {message}")
        if details:
            self.logger.debug(f"Error details: {details}")
        if suggested_fix:
            self.logger.info(f"Suggested fix: {suggested_fix}")
        return error

    def clear_errors(self):
        """Clear all logged errors"""
        self.errors = []

    def has_errors(self) -> bool:
        """Check if agent has any errors"""
        return len(self.errors) > 0

    def _handle_error(self, exception: Exception) -> AgentOutput:
        """Handle exceptions and return appropriate AgentOutput"""
        error = self.log_error(
            f"Execution failed: {str(exception)}",
            ErrorSeverity.HIGH,
            {"exception_type": type(exception).__name__},
            "Check agent configuration and dependencies",
        )

        return AgentOutput(agent_name=self.name, status=AgentStatus.ERROR, errors=[error])

    def _create_success_output(self, data: Dict[str, Any] = None) -> AgentOutput:
        """Create a successful AgentOutput"""
        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            data=data or {},
            version=self.version,
            dependencies=self.dependencies,
        )
