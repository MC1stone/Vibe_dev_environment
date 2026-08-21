# NIR Intelligence Platform - Docker Agent
# Handles containerization and Docker services management with improved error handling

import os
import shutil
import subprocess
import time
from typing import Any, Dict, List

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class DockerAgent(BaseAgent):
    """Agent for managing Docker containers and services with enhanced error handling"""

    def __init__(self, **kwargs):
        super().__init__(name="DockerAgent", version="1.0.1", **kwargs)
        self.dependencies = ["docker", "docker-compose"]
        self.docker_compose_file = kwargs.get("docker_compose_file", "docker-compose.yml")
        self.network_name = kwargs.get("network_name", "nir_network")
        self.services = kwargs.get("services", ["weaviate", "postgresql", "faiss", "mcp_server"])
        self.timeout = kwargs.get("timeout", 300)
        self.skip_if_unavailable = kwargs.get("skip_if_unavailable", False)
        self.debug_mode = kwargs.get("debug", False)

    def _log_debug(self, message: str):
        """Log debug messages if debug mode is enabled"""
        if self.debug_mode:
            self.logger.debug(message)

    def _run_command(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a command with enhanced error handling"""
        try:
            self._log_debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if check and result.returncode != 0:
                error_msg = f"Command failed: {' '.join(cmd)}\n" f"stdout: {result.stdout}\n" f"stderr: {result.stderr}"
                self.logger.error(error_msg)
            return result
        except subprocess.TimeoutExpired:
            self.log_error(f"Command timed out: {' '.join(cmd)}", ErrorSeverity.MEDIUM)
            return subprocess.CompletedProcess(cmd, -1, stdout="", stderr="Timeout")
        except Exception as e:
            self.log_error(f"Command execution error: {str(e)}", ErrorSeverity.HIGH)
            return subprocess.CompletedProcess(cmd, -1, stdout="", stderr=str(e))

    def _check_docker_client(self) -> bool:
        """Check if Docker client is available"""
        result = self._run_command(["docker", "--version"], check=False)
        if result.returncode != 0:
            self.log_error(
                "Docker client not found",
                ErrorSeverity.CRITICAL,
                {"suggested_fix": "Install Docker: sudo apt-get install docker.io", "error_output": result.stderr},
            )
            return False
        return True

    def _check_docker_daemon(self) -> bool:
        """Check if Docker daemon is running"""
        result = self._run_command(["docker", "info"], check=False)
        if result.returncode != 0:
            self.log_error(
                "Docker daemon not running",
                ErrorSeverity.CRITICAL,
                {"suggested_fix": "Start Docker service: sudo systemctl start docker", "error_output": result.stderr},
            )
            return False
        return True

    def _check_docker_permissions(self) -> bool:
        """Check if current user has Docker permissions"""
        result = self._run_command(["docker", "ps"], check=False)
        if result.returncode != 0:
            self.log_error(
                "Docker permission denied",
                ErrorSeverity.HIGH,
                {
                    "suggested_fix": "Add user to docker group: sudo usermod -aG docker $USER && newgrp docker",
                    "error_output": result.stderr,
                },
            )
            return False
        return True

    def _check_docker_compose(self) -> bool:
        """Check if Docker Compose is available"""
        # Try docker-compose plugin first
        result = self._run_command(["docker", "compose", "version"], check=False)
        if result.returncode == 0:
            self.logger.info("Using Docker Compose plugin")
            return True

        # Fall back to standalone docker-compose
        result = self._run_command(["docker-compose", "--version"], check=False)
        if result.returncode != 0:
            self.log_error(
                "Docker Compose not found",
                ErrorSeverity.HIGH,
                {
                    "suggested_fix": "Install Docker Compose: sudo apt-get install docker-compose-plugin",
                    "error_output": result.stderr,
                },
            )
            return False
        return True

    def _check_docker_compose_file(self) -> bool:
        """Check if docker-compose file exists and is valid"""
        if not os.path.exists(self.docker_compose_file):
            self.log_error(
                f"Docker Compose file not found: {self.docker_compose_file}",
                ErrorSeverity.CRITICAL,
                {"suggested_fix": f"Create {self.docker_compose_file} or check path"},
            )
            return False

        # Validate the compose file
        result = self._run_command(["docker", "compose", "-f", self.docker_compose_file, "config"], check=False)
        if result.returncode != 0:
            self.log_error(
                f"Invalid Docker Compose file: {self.docker_compose_file}",
                ErrorSeverity.HIGH,
                {"validation_error": result.stderr, "suggested_fix": "Check YAML syntax in docker-compose.yml"},
            )
            return False

        self.logger.info(f"Docker Compose file validated: {self.docker_compose_file}")
        return True

    def _check_or_create_network(self) -> bool:
        """Check if Docker network exists, create if not"""
        result = self._run_command(["docker", "network", "inspect", self.network_name], check=False)

        if result.returncode == 0:
            self.logger.info(f"Docker network exists: {self.network_name}")
            return True

        # Network doesn't exist, try to create it
        self.logger.info(f"Creating Docker network: {self.network_name}")
        result = self._run_command(["docker", "network", "create", self.network_name], check=False)

        if result.returncode != 0:
            self.log_error(
                f"Failed to create Docker network: {result.stderr}",
                ErrorSeverity.MEDIUM,
                {"suggested_fix": "Check network name or manually create network"},
            )
            return False

        self.logger.info(f"Docker network created: {self.network_name}")
        return True

    def _start_services(self) -> Dict[str, bool]:
        """Start Docker services with enhanced error handling"""
        service_status = {}

        # Check if services are already running
        result = self._run_command(["docker", "compose", "-f", self.docker_compose_file, "ps"], check=False)

        if "running" in result.stdout.lower():
            self.logger.info("Some services are already running")
            return self._check_service_health()

        # Start services
        self.logger.info(f"Starting services: {', '.join(self.services)}")
        result = self._run_command(["docker", "compose", "-f", self.docker_compose_file, "up", "-d"], check=False)

        if result.returncode != 0:
            self.log_error(
                f"Failed to start services: {result.stderr}",
                ErrorSeverity.HIGH,
                {"command": "docker compose up -d", "suggested_fix": "Check service configurations and logs"},
            )
            return self._check_service_health()

        # Wait for services to stabilize
        self.logger.info(f"Waiting for services to initialize (timeout: {self.timeout}s)")
        time.sleep(10)

        return self._check_service_health()

    def _check_service_health(self) -> Dict[str, bool]:
        """Check health status of individual services"""
        health_status = {}

        # Get all service containers
        result = self._run_command(["docker", "compose", "-f", self.docker_compose_file, "ps"], check=False)

        for service in self.services:
            service_line = None
            for line in result.stdout.split("\n"):
                if f"{self.network_name}_{service}" in line or service in line.split():
                    service_line = line
                    break

            if service_line and "running" in service_line.lower():
                health_status[service] = True
                self.logger.info(f"Service {service} is running")
            else:
                health_status[service] = False
                self.log_error(
                    f"Service {service} is not running",
                    ErrorSeverity.MEDIUM,
                    {
                        "service_line": service_line,
                        "suggested_fix": f"Check logs: docker logs {self.network_name}_{service}_1",
                    },
                )

        return health_status

    def _get_service_logs(self, service_name: str) -> str:
        """Get logs for a specific service for debugging"""
        containers = self._run_command(
            ["docker", "ps", "--filter", f"name={service_name}", "--format", "{{.Names}}"], check=False
        )

        if containers.stdout.strip():
            container_name = containers.stdout.strip().split("\n")[0]
            result = self._run_command(["docker", "logs", container_name], check=False)
            return result.stdout
        return "No container found"

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute Docker agent workflow with comprehensive error handling"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting Docker agent execution")

            # Skip entirely if configured to do so
            if self.skip_if_unavailable:
                self.logger.warning("Docker agent configured to skip if unavailable")
                return self._create_success_output({"status": "skipped", "docker_available": False})

            # Step 1: Check Docker client
            if not self._check_docker_client():
                if not self.skip_if_unavailable:
                    return self._handle_error(Exception("Docker client check failed"))
                return self._create_success_output({"status": "skipped"})

            # Step 2: Check Docker daemon
            if not self._check_docker_daemon():
                if not self.skip_if_unavailable:
                    return self._handle_error(Exception("Docker daemon check failed"))
                return self._create_success_output({"status": "skipped"})

            # Step 3: Check Docker permissions
            if not self._check_docker_permissions():
                if not self.skip_if_unavailable:
                    return self._handle_error(Exception("Docker permission check failed"))
                return self._create_success_output({"status": "skipped"})

            # Step 4: Check Docker Compose
            if not self._check_docker_compose():
                if not self.skip_if_unavailable:
                    return self._handle_error(Exception("Docker Compose check failed"))
                return self._create_success_output({"status": "skipped"})

            # Step 5: Check Docker Compose file
            if not self._check_docker_compose_file():
                if not self.skip_if_unavailable:
                    return self._handle_error(Exception("Docker Compose file check failed"))
                return self._create_success_output({"status": "skipped"})

            # Step 6: Check/create network
            if not self._check_or_create_network():
                self.log_error("Network check failed, continuing without network", ErrorSeverity.LOW)

            # Step 7: Start services
            health_status = self._start_services()

            # Check if we should consider this a success
            all_healthy = all(health_status.values())
            if not all_healthy and not self.skip_if_unavailable:
                failed_services = [s for s, h in health_status.items() if not h]
                self.log_error(
                    f"Some services failed: {', '.join(failed_services)}",
                    ErrorSeverity.MEDIUM,
                    {"health_status": health_status},
                )

                # Get logs for failed services
                for service in failed_services:
                    logs = self._get_service_logs(service)
                    self.logger.error(f"Logs for {service}:\n{logs}")

            # Complete execution
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(
                {
                    "docker_client": True,
                    "docker_daemon": True,
                    "docker_permissions": True,
                    "docker_compose": True,
                    "network_created": True,
                    "services_started": all_healthy,
                    "service_health": health_status,
                    "debug_info": {
                        "docker_version": self._run_command(["docker", "--version"], check=False).stdout,
                        "compose_version": self._run_command(["docker", "compose", "version"], check=False).stdout,
                        "networks": self._run_command(["docker", "network", "ls"], check=False).stdout,
                    },
                }
            )

        except Exception as e:
            error_output = self._handle_error(e)

            # Provide additional debugging info
            try:
                error_output.data["debug_info"] = {
                    "docker_ps": self._run_command(["docker", "ps"], check=False).stdout,
                    "docker_networks": self._run_command(["docker", "network", "ls"], check=False).stdout,
                    "current_user": self._run_command(["whoami"], check=False).stdout.strip(),
                    "docker_group": "docker" in self._run_command(["groups"], check=False).stdout,
                }
            except:
                pass

            return error_output
