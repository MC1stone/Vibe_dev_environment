#!/usr/bin/env python3
"""
NIR Intelligence Platform - {{agent_name}}
{{description or 'Agent for NIR spectroscopy data processing'}}
"""

import logging
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent, AgentOutput, AgentStatus, ErrorSeverity, AgentError


class {{class_name}}(BaseAgent):
    """Agent for {{class_name.replace('Agent', '')}} functionality"""
    
    def __init__(self, **kwargs):
        super().__init__(name="{{class_name}}", version="1.0.0", **kwargs)
        self.dependencies = {{dependencies}}
        self.logger = logging.getLogger(f"Agent.{self.name}")
        
        # Initialize agent-specific attributes
        self._initialize_attributes()
    
    def _initialize_attributes(self):
        """Initialize agent-specific attributes"""
        # Add agent-specific initialization here
        {% for attr in required_methods if attr.startswith('_') %}
        self.{{attr}} = None
        {% endfor %}
    
    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute the agent's primary function"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting {{class_name}} execution")
            
            # TODO: Implement {{class_name}} logic
            # Example workflow:
            # 1. Load and validate input data
            # 2. Perform agent-specific processing
            # 3. Generate output
            
            result = {
                "status": "completed",
                "message": "{{class_name}} execution completed successfully",
                "data": {}
            }
            
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(result)
            
        except Exception as e:
            return self._handle_error(e)
    
    {% for method in required_methods if not method.startswith('_') and method != 'execute' %}
    def {{method}}(self, context: Dict[str, Any]) -> Any:
        """{{method}} method - TODO: Implement"""
        # TODO: Implement {{method}}
        raise NotImplementedError(f"{{method}} method not implemented")
    
    {% endfor %}
    
    {% for method in required_methods if method.startswith('_') and method != '_initialize_attributes' %}
    def {{method}}(self) -> Any:
        """{{method}} method - TODO: Implement"""
        # TODO: Implement {{method}}
        raise NotImplementedError(f"{{method}} method not implemented")
    
    {% endfor %}
    
    def validate(self) -> List[AgentError]:
        """Validate agent configuration and state"""
        errors = super().validate()
        
        # Add agent-specific validation
        # Example: Check required dependencies
        # for dep in self.dependencies:
        #     try:
        #         __import__(dep)
        #     except ImportError:
        #         self.log_error(
        #             f"Missing dependency: {dep}",
        #             ErrorSeverity.HIGH,
        #             {"dependency": dep},
        #             f"Install with: pip install {dep}"
        #         )
        
        return errors


if __name__ == "__main__":
    # Allow direct execution for testing
    agent = {{class_name}}()
    output = agent.initialize()
    print(f"{output.agent_name} initialized: {output.status.name}")
