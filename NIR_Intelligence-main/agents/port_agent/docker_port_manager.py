"""
Docker-Specific Port Management

This module provides Docker-specific port management capabilities including:
- Docker container port inspection
- Port mapping management
- Container port conflict detection
- Docker network port management
"""

import json
import logging
import re
import socket
import subprocess
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .exceptions import (
    DockerPortError,
    PortConflictError,
    PortManagerError,
    PortNotAvailableError,
    PortOutOfRangeError,
    PortReleaseError,
    PortReservationError,
    PortScanError,
)
from .port_manager import PortInfo, PortManager

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class DockerContainerInfo:
    """Information about a Docker container"""

    container_id: str
    name: str
    status: str
    ports: Dict[str, List[Dict[str, str]]]  # Port mappings
    image: str
    network: str

    def get_host_ports(self) -> Set[int]:
        """Get all host ports used by this container"""
        host_ports = set()
        if self.ports:
            for container_port, mappings in self.ports.items():
                if container_port.isdigit():
                    for mapping in mappings:
                        if "HostPort" in mapping and mapping["HostPort"].isdigit():
                            host_ports.add(int(mapping["HostPort"]))
        return host_ports

    def get_container_ports(self) -> Set[int]:
        """Get all container ports used by this container"""
        container_ports = set()
        if self.ports:
            for container_port in self.ports.keys():
                if container_port.isdigit():
                    container_ports.add(int(container_port))
        return container_ports


@dataclass
class DockerPortMapping:
    """Information about a Docker port mapping"""

    container_id: str
    container_name: str
    container_port: int
    container_protocol: str
    host_port: Optional[int]
    host_ip: Optional[str]

    def __str__(self) -> str:
        if self.host_port and self.host_ip:
            return f"{self.host_ip}:{self.host_port} -> {self.container_port}/{self.container_protocol}"
        elif self.host_port:
            return f"{self.host_port} -> {self.container_port}/{self.container_protocol}"
        else:
            return f"{self.container_port}/{self.container_protocol}"


class DockerPortScanner:
    """Docker-specific port scanner"""

    _cache: Dict[str, Any] = {}
    _cache_lock: threading.Lock = threading.Lock()
    _cache_timeout: float = 30.0  # seconds

    @classmethod
    def clear_cache(cls):
        """Clear the Docker cache"""
        with cls._cache_lock:
            cls._cache.clear()

    @classmethod
    def _run_docker_command(cls, command: List[str], timeout: int = 10) -> Tuple[int, str, str]:
        """Run a Docker command and return (returncode, stdout, stderr)"""
        try:
            result = subprocess.run(["docker"] + command, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except FileNotFoundError:
            return -1, "", "Docker not found. Is Docker installed and running?"
        except Exception as e:
            return -1, "", str(e)

    @classmethod
    def is_docker_available(cls) -> bool:
        """Check if Docker is available on the system"""
        returncode, _, stderr = cls._run_docker_command(["--version"])
        return returncode == 0

    @classmethod
    def get_docker_version(cls) -> Optional[str]:
        """Get Docker version"""
        returncode, stdout, stderr = cls._run_docker_command(["--version"])
        if returncode == 0:
            return stdout.strip()
        return None

    @classmethod
    def get_running_containers(cls) -> List[DockerContainerInfo]:
        """Get list of running Docker containers"""
        cache_key = "running_containers"
        current_time = __import__("time").time()

        # Check cache
        with cls._cache_lock:
            if cache_key in cls._cache:
                cached_time, cached_data = cls._cache[cache_key]
                if current_time - cached_time < cls._cache_timeout:
                    return cached_data

        containers = []
        returncode, stdout, stderr = cls._run_docker_command(["ps", "--format", "{{json .}}"])

        if returncode == 0 and stdout.strip():
            try:
                for line in stdout.strip().split("\n"):
                    if line.strip():
                        data = json.loads(line)
                        container = DockerContainerInfo(
                            container_id=data.get("ID", ""),
                            name=data.get("Names", ""),
                            status=data.get("Status", ""),
                            ports={},  # Will be populated separately
                            image=data.get("Image", ""),
                            network=data.get("Networks", ""),
                        )
                        containers.append(container)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse Docker container info: {stdout}")

        # Get port mappings for each container
        for container in containers:
            container.ports = cls._get_container_ports(container.container_id)

        # Update cache
        with cls._cache_lock:
            cls._cache[cache_key] = (current_time, containers)

        return containers

    @classmethod
    def _get_container_ports(cls, container_id: str) -> Dict[str, List[Dict[str, str]]]:
        """Get port mappings for a specific container"""
        returncode, stdout, stderr = cls._run_docker_command(["port", container_id])

        ports = {}
        if returncode == 0 and stdout.strip():
            for line in stdout.strip().split("\n"):
                if line.strip():
                    # Parse port mapping like: 8000/tcp -> 0.0.0.0:8000
                    if "->" in line:
                        container_side, host_side = line.split("->", 1)
                        container_side = container_side.strip()
                        host_side = host_side.strip()

                        # Parse container side
                        if "/" in container_side:
                            container_port, protocol = container_side.split("/", 1)
                        else:
                            container_port, protocol = container_side, "tcp"

                        # Parse host side
                        if ":" in host_side:
                            host_ip, host_port = host_side.rsplit(":", 1)
                            if host_port.isdigit():
                                if container_port not in ports:
                                    ports[container_port] = []
                                ports[container_port].append({"HostIp": host_ip, "HostPort": host_port})

        return ports

    @classmethod
    def get_container_by_name(cls, name: str) -> Optional[DockerContainerInfo]:
        """Get container information by name"""
        containers = cls.get_running_containers()
        for container in containers:
            if name in [container.name, container.container_id[:12]]:
                return container
        return None

    @classmethod
    def get_used_host_ports(cls) -> Set[int]:
        """Get all host ports used by Docker containers"""
        containers = cls.get_running_containers()
        used_ports = set()

        for container in containers:
            used_ports.update(container.get_host_ports())

        return used_ports

    @classmethod
    def get_container_port_mappings(cls) -> List[DockerPortMapping]:
        """Get all Docker port mappings"""
        containers = cls.get_running_containers()
        mappings = []

        for container in containers:
            for container_port, port_mappings in container.ports.items():
                if container_port.isdigit():
                    for mapping in port_mappings:
                        docker_mapping = DockerPortMapping(
                            container_id=container.container_id,
                            container_name=container.name,
                            container_port=int(container_port),
                            container_protocol=mapping.get("HostPort", "tcp"),
                            host_port=int(mapping["HostPort"]) if mapping["HostPort"].isdigit() else None,
                            host_ip=mapping.get("HostIp"),
                        )
                        mappings.append(docker_mapping)

        return mappings

    @classmethod
    def find_available_host_port(
        cls, container_port: int, start: int = 8000, end: int = 9000, host: str = "127.0.0.1"
    ) -> Optional[int]:
        """Find an available host port for a container port"""
        used_ports = cls.get_used_host_ports()

        # Also check system ports
        port_scanner = __import__("platform").system()
        if port_scanner == "Windows":
            system_ports = set()
        else:
            from .port_manager import PortScanner

            system_ports = PortScanner.get_system_used_ports(host)

        all_used = used_ports.union(system_ports)

        # Find available port
        for port in range(start, end + 1):
            if port not in all_used:
                # Verify with socket binding
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1)
                        s.bind((host, port))
                        return port
                except (OSError, socket.error):
                    continue

        return None


class DockerPortManager:
    """
    Docker-Specific Port Manager

    This class provides comprehensive Docker port management capabilities including:
    - Docker container port inspection
    - Port mapping management
    - Container port conflict detection
    - Integration with PortManager for unified port management
    """

    def __init__(self, port_manager: PortManager = None):
        """
        Initialize the Docker Port Manager

        Args:
            port_manager: PortManager instance for integration
        """
        self.port_manager = port_manager or PortManager()
        self.scanner = DockerPortScanner()
        self._lock = threading.RLock()

    def is_docker_available(self) -> bool:
        """Check if Docker is available"""
        return self.scanner.is_docker_available()

    def get_docker_version(self) -> Optional[str]:
        """Get Docker version"""
        return self.scanner.get_docker_version()

    def get_running_containers(self) -> List[DockerContainerInfo]:
        """Get list of running Docker containers"""
        if not self.is_docker_available():
            raise DockerPortError(message="Docker is not available", details="Is Docker installed and running?")
        return self.scanner.get_running_containers()

    def get_container_info(self, container_name: str) -> Optional[DockerContainerInfo]:
        """Get information about a specific container"""
        if not self.is_docker_available():
            raise DockerPortError(message="Docker is not available", details="Is Docker installed and running?")
        return self.scanner.get_container_by_name(container_name)

    def get_container_port_mappings(self) -> List[DockerPortMapping]:
        """Get all Docker port mappings"""
        if not self.is_docker_available():
            raise DockerPortError(message="Docker is not available", details="Is Docker installed and running?")
        return self.scanner.get_container_port_mappings()

    def get_used_docker_ports(self) -> Set[int]:
        """Get all host ports used by Docker containers"""
        if not self.is_docker_available():
            return set()
        return self.scanner.get_used_host_ports()

    def find_available_host_port(
        self, container_port: int, start: int = 8000, end: int = 9000, host: str = "127.0.0.1"
    ) -> Optional[int]:
        """
        Find an available host port for a container port

        Args:
            container_port: The container port to map
            start: Start of host port range
            end: End of host port range
            host: Host address for binding

        Returns:
            Available host port or None
        """
        if not self.is_docker_available():
            # Fallback to regular port finding
            return self.port_manager.find_free_port(start, end, host)

        return self.scanner.find_available_host_port(container_port, start, end, host)

    def reserve_docker_port(
        self,
        container_port: int,
        host_port: Optional[int] = None,
        start: int = 8000,
        end: int = 9000,
        host: str = "127.0.0.1",
        service_name: str = None,
    ) -> Dict[str, Any]:
        """
        Reserve a port for Docker container mapping

        Args:
            container_port: The container port to map
            host_port: Specific host port to reserve (optional)
            start: Start of host port range if host_port not specified
            end: End of host port range if host_port not specified
            host: Host address for binding
            service_name: Name of service for logging

        Returns:
            Dictionary with reservation information
        """
        if host_port is None:
            # Find available host port
            host_port = self.find_available_host_port(container_port, start, end, host)
            if host_port is None:
                raise DockerPortError(
                    message="No available host port found",
                    container_port=container_port,
                    details=f"Range: {start}-{end}",
                )

        # Reserve the host port
        self.port_manager.reserve_port(host_port, host, service_name or f"docker:{container_port}")

        return {
            "success": True,
            "container_port": container_port,
            "host_port": host_port,
            "host": host,
            "service_name": service_name,
            "mapping": f"{host}:{host_port} -> {container_port}",
        }

    def release_docker_port(self, host_port: int, host: str = "127.0.0.1") -> bool:
        """
        Release a previously reserved Docker host port

        Args:
            host_port: The host port to release
            host: Host address

        Returns:
            True if port was released, False otherwise
        """
        return self.port_manager.release_port(host_port, host)

    def check_docker_port_conflicts(self, host_port: int, host: str = "127.0.0.1") -> List[str]:
        """
        Check for Docker port conflicts

        Args:
            host_port: The host port to check
            host: Host address

        Returns:
            List of conflict descriptions
        """
        conflicts = []

        # Check if port is used by Docker
        docker_ports = self.get_used_docker_ports()
        if host_port in docker_ports:
            # Find which container is using it
            containers = self.get_running_containers()
            for container in containers:
                if host_port in container.get_host_ports():
                    conflicts.append(f"Docker container: {container.name} ({container.container_id[:12]})")

        # Check system ports
        system_conflicts = self.port_manager.get_port_conflicts(host_port, host)
        conflicts.extend(system_conflicts)

        # Check reserved ports
        with self.port_manager._lock:
            if host_port in self.port_manager._reserved_ports:
                port_info = self.port_manager._port_info.get(host_port)
                if port_info:
                    conflicts.append(f"Reserved by: {port_info.service_name}")

        return conflicts

    def get_docker_port_status(self, host_port: int, host: str = "127.0.0.1") -> Dict[str, Any]:
        """
        Get comprehensive status for a Docker port

        Args:
            host_port: The host port to check
            host: Host address

        Returns:
            Dictionary with port status information
        """
        docker_ports = self.get_used_docker_ports()
        system_available = self.port_manager.check_port_available(host_port, host)
        conflicts = self.check_docker_port_conflicts(host_port, host)

        with self.port_manager._lock:
            is_reserved = host_port in self.port_manager._reserved_ports

        return {
            "port": host_port,
            "host": host,
            "used_by_docker": host_port in docker_ports,
            "system_available": system_available,
            "is_reserved": is_reserved,
            "available": system_available and host_port not in docker_ports and not is_reserved,
            "conflicts": conflicts,
        }

    def start_container_with_port(
        self,
        image: str,
        container_name: str,
        container_port: int,
        host_port: Optional[int] = None,
        host: str = "127.0.0.1",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Start a Docker container with automatic port assignment

        Args:
            image: Docker image to run
            container_name: Name for the container
            container_port: Container port to expose
            host_port: Specific host port (optional, will auto-assign)
            host: Host address for binding
            **kwargs: Additional docker run arguments

        Returns:
            Dictionary with container start information
        """
        if not self.is_docker_available():
            raise DockerPortError(message="Docker is not available", details="Cannot start container without Docker")

        # Find or use host port
        if host_port is None:
            host_port = self.find_available_host_port(container_port, 8000, 9000, host)
            if host_port is None:
                raise DockerPortError(
                    message="No available host port found", container_port=container_port, details="Range: 8000-9000"
                )

        # Reserve the port
        service_name = f"docker:{container_name}:{container_port}"
        self.port_manager.reserve_port(host_port, host, service_name)

        # Build docker command
        cmd = ["docker", "run", "-d", "--name", container_name]
        cmd.extend(["-p", f"{host}:{host_port}:{container_port}"])

        # Add additional arguments
        for key, value in kwargs.items():
            if value is True:
                cmd.append(f"--{key}")
            elif value is not None:
                cmd.extend([f"--{key}", str(value)])

        # Add image
        cmd.append(image)

        # Execute command
        returncode, stdout, stderr = self.scanner._run_docker_command(cmd)

        if returncode != 0:
            # Release the port since container failed to start
            self.port_manager.release_port(host_port, host)
            raise DockerPortError(
                message=f"Failed to start container {container_name}",
                container_name=container_name,
                details=f"Error: {stderr}",
            )

        # Get container ID from output
        container_id = stdout.strip()

        return {
            "success": True,
            "container_id": container_id,
            "container_name": container_name,
            "image": image,
            "host_port": host_port,
            "container_port": container_port,
            "host": host,
            "mapping": f"{host}:{host_port} -> {container_port}",
            "message": f"Container {container_name} started with port mapping {host}:{host_port} -> {container_port}",
        }

    def stop_container(self, container_name: str) -> Dict[str, Any]:
        """
        Stop a Docker container and release its ports

        Args:
            container_name: Name of container to stop

        Returns:
            Dictionary with stop information
        """
        if not self.is_docker_available():
            raise DockerPortError(message="Docker is not available", details="Cannot stop container without Docker")

        # Get container info before stopping
        container = self.get_container_info(container_name)
        if container is None:
            raise DockerPortError(message=f"Container not found: {container_name}", container_name=container_name)

        # Get host ports used by container
        host_ports = container.get_host_ports()

        # Stop the container
        returncode, stdout, stderr = self.scanner._run_docker_command(["stop", container_name])

        if returncode != 0:
            raise DockerPortError(
                message=f"Failed to stop container {container_name}",
                container_name=container_name,
                details=f"Error: {stderr}",
            )

        # Release the ports
        released_count = 0
        for port in host_ports:
            if self.port_manager.release_port(port):
                released_count += 1

        return {
            "success": True,
            "container_name": container_name,
            "container_id": container.container_id,
            "host_ports_released": list(host_ports),
            "released_count": released_count,
            "message": f"Container {container_name} stopped and {released_count} ports released",
        }

    def get_port_mapping_suggestions(
        self, services: List[Dict[str, Any]], start_port: int = 8000, end_port: int = 9000
    ) -> Dict[str, Any]:
        """
        Get port mapping suggestions for multiple services

        Args:
            services: List of service definitions with required ports
            start_port: Start of port range
            end_port: End of port range

        Returns:
            Dictionary with port mapping suggestions
        """
        suggestions = {}
        used_ports = set()

        # Get currently used Docker ports
        if self.is_docker_available():
            used_ports.update(self.get_used_docker_ports())

        # Get system used ports
        system_ports = self.port_manager._scanner.get_system_used_ports()
        used_ports.update(system_ports)

        # Get reserved ports
        with self.port_manager._lock:
            used_ports.update(self.port_manager._reserved_ports)

        # Find ports for each service
        current_port = start_port

        for service in services:
            service_name = service.get("name", "unknown")
            required_ports = service.get("ports", [])

            service_mappings = {}

            for container_port in required_ports:
                # Find available host port
                while current_port <= end_port:
                    if current_port not in used_ports:
                        # Verify with socket binding
                        try:
                            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                                s.settimeout(1)
                                s.bind(("127.0.0.1", current_port))
                                service_mappings[str(container_port)] = current_port
                                used_ports.add(current_port)
                                current_port += 1
                                break
                        except (OSError, socket.error):
                            current_port += 1
                            continue
                    current_port += 1
                else:
                    # No port found in range
                    raise DockerPortError(
                        message=f"No available port for service {service_name}",
                        container_port=container_port,
                        details=f"Range: {start_port}-{end_port}",
                    )

            suggestions[service_name] = service_mappings

        return {"success": True, "suggestions": suggestions, "used_port_range": f"{start_port}-{current_port - 1}"}
