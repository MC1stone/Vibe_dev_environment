# NIR Intelligence Platform - UVX Agent
# Handles Python environment management using UV package manager

import os
import subprocess
import sys
from typing import Any, Dict

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class UVXAgent(BaseAgent):
    """Agent for managing Python environment using UV package manager"""

    def __init__(self, **kwargs):
        super().__init__(name="UVXAgent", version="1.0.0", **kwargs)
        self.dependencies = ["python3.12", "uv"]
        self.python_version = kwargs.get("python_version", "3.12")
        self.virtual_env = kwargs.get("virtual_env", True)
        self.requirements_file = kwargs.get("requirements_file", "requirements.txt")

    def _check_python_version(self) -> bool:
        """Check if required Python version is available"""
        try:
            version_str = sys.version.split()[0]
            major, minor = list(map(int, version_str.split("."))[:2])
            required_major, required_minor = list(map(int, self.python_version.split("."))[:2])

            if (major > required_major) or (major == required_major and minor >= required_minor):
                self.logger.info(f"Python {self.python_version}+ requirement satisfied")
                return True
            else:
                self.log_error(
                    f"Python version {version_str} is insufficient, requires {self.python_version}+",
                    ErrorSeverity.CRITICAL,
                    {"current_version": version_str, "required_version": self.python_version},
                )
                return False
        except Exception as e:
            self.log_error(f"Failed to check Python version: {str(e)}", ErrorSeverity.HIGH)
            return False

    def _check_uv_installed(self) -> bool:
        """Check if UV package manager is installed"""
        try:
            result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info(f"UV package manager found: {result.stdout.strip()}")
                return True
            else:
                self.log_error(
                    "UV package manager not found",
                    ErrorSeverity.CRITICAL,
                    {"suggested_fix": "Install UV using: pip install uv"},
                )
                return False
        except Exception as e:
            self.log_error(f"Failed to check UV installation: {str(e)}", ErrorSeverity.HIGH)
            return False

    def _create_virtual_env(self) -> bool:
        """Create virtual environment if enabled"""
        if not self.virtual_env:
            self.logger.info("Virtual environment disabled")
            return True

        try:
            # Check if venv already exists
            if os.path.exists("venv"):
                self.logger.info("Virtual environment already exists")
                return True

            self.logger.info("Creating virtual environment...")
            result = subprocess.run(["python", "-m", "venv", "venv"], capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info("Virtual environment created successfully")
                return True
            else:
                self.log_error(f"Failed to create virtual environment: {result.stderr}", ErrorSeverity.HIGH)
                return False
        except Exception as e:
            self.log_error(f"Error creating virtual environment: {str(e)}", ErrorSeverity.HIGH)
            return False

    def _install_dependencies(self) -> bool:
        """Install Python dependencies using UV"""
        try:
            if not os.path.exists(self.requirements_file):
                self.log_error(f"Requirements file not found: {self.requirements_file}", ErrorSeverity.CRITICAL)
                return False

            self.logger.info(f"Installing dependencies from {self.requirements_file}")

            # Use UV to install dependencies
            cmd = ["uv", "pip", "install", "-r", self.requirements_file]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info("Dependencies installed successfully")
                return True
            else:
                self.log_error(
                    f"Failed to install dependencies: {result.stderr}", ErrorSeverity.HIGH, {"command": " ".join(cmd)}
                )
                return False
        except Exception as e:
            self.log_error(f"Error installing dependencies: {str(e)}", ErrorSeverity.HIGH)
            return False

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute UVX agent workflow"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting UVX agent execution")

            # Step 1: Check Python version
            if not self._check_python_version():
                return self._handle_error(Exception("Python version check failed"))

            # Step 2: Check UV installation
            if not self._check_uv_installed():
                return self._handle_error(Exception("UV installation check failed"))

            # Step 3: Create virtual environment
            if not self._create_virtual_env():
                return self._handle_error(Exception("Virtual environment creation failed"))

            # Step 4: Install dependencies
            if not self._install_dependencies():
                return self._handle_error(Exception("Dependency installation failed"))

            # All steps completed successfully
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(
                {
                    "python_version": sys.version,
                    "uv_installed": True,
                    "virtual_env": self.virtual_env,
                    "dependencies_installed": True,
                }
            )

        except Exception as e:
            return self._handle_error(e)
