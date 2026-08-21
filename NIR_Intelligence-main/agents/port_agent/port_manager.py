"""
Enhanced Port Manager with Thread-Safe Reservation System

This module provides comprehensive port management capabilities including:
- Thread-safe port reservation and release
- Cross-platform port scanning (Windows/Linux/Mac)
- Port availability checking with socket binding
- Port range validation and management
- Comprehensive error handling
"""

import logging
import os
import platform
import random
import re
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .exceptions import (
    PortConflictError,
    PortManagerError,
    PortNotAvailableError,
    PortOutOfRangeError,
    PortReleaseError,
    PortReservationError,
    PortScanError,
)

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class PortInfo:
    """Information about a port"""

    port: int
    host: str = "127.0.0.1"
    is_available: bool = True
    is_reserved: bool = False
    process_info: str = ""
    service_name: str = ""
    reservation_time: float = 0.0
    last_checked: float = 0.0


@dataclass
class PortRange:
    """Port range configuration"""

    start: int = 8000
    end: int = 9000
    host: str = "127.0.0.1"
    description: str = "Default port range"

    def __post_init__(self):
        """Validate port range"""
        if not (1 <= self.start <= 65535):
            raise PortOutOfRangeError(self.start)
        if not (1 <= self.end <= 65535):
            raise PortOutOfRangeError(self.end)
        if self.start > self.end:
            raise PortManagerError(message="Invalid port range", details=f"Start ({self.start}) > End ({self.end})")


class PortScanner:
    """Cross-platform port scanner"""

    # Cache for system ports to avoid frequent scanning
    _system_ports_cache: Dict[str, Set[int]] = {}
    _cache_timeout: float = 30.0  # seconds
    _cache_lock: threading.Lock = threading.Lock()

    @classmethod
    def clear_cache(cls):
        """Clear the port cache"""
        with cls._cache_lock:
            cls._system_ports_cache.clear()

    @classmethod
    def _get_system_command(cls) -> List[str]:
        """Get the appropriate system command for port scanning"""
        system = platform.system()

        if system == "Windows":
            return ["netstat", "-ano"]
        elif system == "Linux":
            # Try ss first, fallback to netstat, then /proc/net/tcp
            try:
                result = subprocess.run(["which", "ss"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    return ["ss", "-tuln"]
            except:
                pass
            try:
                result = subprocess.run(["which", "netstat"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    return ["netstat", "-tuln"]
            except:
                pass
            # Use /proc/net/tcp as fallback
            return ["proc"]
        elif system == "Darwin":  # macOS
            try:
                result = subprocess.run(["which", "lsof"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    return ["lsof", "-i", "-P", "-n"]
            except:
                pass
            try:
                result = subprocess.run(["which", "netstat"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    return ["netstat", "-tuln"]
            except:
                pass
            return ["netstat", "-tuln"]
        else:
            # Fallback for unknown systems
            return ["netstat", "-tuln"]

    @classmethod
    def _parse_ss_output(cls, output: str) -> Set[int]:
        """Parse ss command output"""
        ports = set()
        for line in output.splitlines():
            # Look for patterns like "0.0.0.0:8000" or "*:8000"
            matches = re.findall(r":(\d+)", line)
            for match in matches:
                port = int(match)
                if 1 <= port <= 65535:
                    ports.add(port)
        return ports

    @classmethod
    def _parse_netstat_output(cls, output: str) -> Set[int]:
        """Parse netstat command output"""
        ports = set()
        for line in output.splitlines():
            # Look for patterns like "0.0.0.0:8000" or "*:8000"
            matches = re.findall(r":(\d+)", line)
            for match in matches:
                port = int(match)
                if 1 <= port <= 65535:
                    ports.add(port)
        return ports

    @classmethod
    def _parse_lsof_output(cls, output: str) -> Set[int]:
        """Parse lsof command output (macOS)"""
        ports = set()
        for line in output.splitlines()[1:]:  # Skip header
            parts = line.split()
            for part in parts:
                if part.isdigit() and 1 <= int(part) <= 65535:
                    ports.add(int(part))
        return ports

    @classmethod
    def _parse_netstat_windows_output(cls, output: str) -> Set[int]:
        """Parse Windows netstat output"""
        ports = set()
        for line in output.splitlines()[2:]:  # Skip headers
            parts = line.split()
            if len(parts) >= 2:
                # Look for patterns like "0.0.0.0:8000" or "[::]:8000"
                for part in parts:
                    if ":" in part:
                        port_str = part.split(":")[-1]
                        if port_str.isdigit():
                            port = int(port_str)
                            if 1 <= port <= 65535:
                                ports.add(port)
        return ports

    @classmethod
    def _parse_proc_net_tcp(cls) -> Set[int]:
        """Parse /proc/net/tcp to get used ports (Linux fallback)"""
        ports = set()

        try:
            # Read /proc/net/tcp for TCP ports
            tcp_path = "/proc/net/tcp"
            if os.path.exists(tcp_path):
                with open(tcp_path, "r") as f:
                    lines = f.readlines()
                    # Skip header line
                    for line in lines[1:]:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            # Local address is in hex format: IP:PORT
                            local_addr = parts[1]
                            if ":" in local_addr:
                                port_hex = local_addr.split(":")[1]
                                try:
                                    port = int(port_hex, 16)
                                    if 1 <= port <= 65535:
                                        ports.add(port)
                                except ValueError:
                                    continue

            # Read /proc/net/tcp6 for TCP6 (IPv6) ports
            tcp6_path = "/proc/net/tcp6"
            if os.path.exists(tcp6_path):
                with open(tcp6_path, "r") as f:
                    lines = f.readlines()
                    # Skip header line
                    for line in lines[1:]:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            # Local address is in hex format: IP:PORT
                            local_addr = parts[1]
                            if ":" in local_addr:
                                port_hex = local_addr.split(":")[1]
                                try:
                                    port = int(port_hex, 16)
                                    if 1 <= port <= 65535:
                                        ports.add(port)
                                except ValueError:
                                    continue
        except Exception as e:
            logger.warning(f"Error parsing /proc/net/tcp: {str(e)}")

        return ports

    @classmethod
    def get_system_used_ports(cls, host: str = "127.0.0.1") -> Set[int]:
        """
        Get all TCP ports currently in use by the system

        Args:
            host: Host address to check (default: 127.0.0.1)

        Returns:
            Set of port numbers that are in use
        """
        cache_key = f"{host}:system_ports"
        current_time = time.time()

        # Check cache first
        with cls._cache_lock:
            if cache_key in cls._system_ports_cache:
                cached_time, cached_ports = cls._system_ports_cache[cache_key]
                if current_time - cached_time < cls._cache_timeout:
                    return cached_ports.copy()

        # Get system command
        cmd = cls._get_system_command()

        # Check if we're using /proc/net/tcp fallback
        if cmd == ["proc"]:
            ports = cls._parse_proc_net_tcp()
            # Update cache
            with cls._cache_lock:
                cls._system_ports_cache[cache_key] = (current_time, ports.copy())
            return ports

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                logger.warning(f"Port scanning command failed: {' '.join(cmd)}")
                logger.warning(f"Error: {result.stderr}")
                # Try /proc/net/tcp as fallback on Linux
                if platform.system() == "Linux":
                    logger.info("Falling back to /proc/net/tcp for port scanning")
                    ports = cls._parse_proc_net_tcp()
                    # Update cache
                    with cls._cache_lock:
                        cls._system_ports_cache[cache_key] = (current_time, ports.copy())
                    return ports
                return set()

            # Parse output based on command
            system = platform.system()
            if system == "Windows":
                ports = cls._parse_netstat_windows_output(result.stdout)
            elif system == "Darwin":
                if "lsof" in cmd[0]:
                    ports = cls._parse_lsof_output(result.stdout)
                else:
                    ports = cls._parse_netstat_output(result.stdout)
            else:  # Linux and others
                if "ss" in cmd[0]:
                    ports = cls._parse_ss_output(result.stdout)
                else:
                    ports = cls._parse_netstat_output(result.stdout)

            # Update cache
            with cls._cache_lock:
                cls._system_ports_cache[cache_key] = (current_time, ports.copy())

            return ports

        except subprocess.TimeoutExpired:
            logger.error(f"Port scanning command timed out: {' '.join(cmd)}")
            return set()
        except Exception as e:
            logger.error(f"Error during port scanning: {str(e)}")
            return set()


class PortManager:
    """
    Enhanced Port Manager with Thread-Safe Reservation System

    This class provides comprehensive port management capabilities including:
    - Thread-safe port reservation and release
    - Port availability checking with socket binding
    - Port range validation and management
    - Cross-platform support
    - Comprehensive error handling
    """

    def __init__(self, default_host: str = "127.0.0.1"):
        """
        Initialize the Port Manager

        Args:
            default_host: Default host address for port operations
        """
        self.default_host = default_host
        self._reserved_ports: Set[int] = set()
        self._port_info: Dict[int, PortInfo] = {}
        self._lock = threading.RLock()  # Reentrant lock for nested operations
        self._scanner = PortScanner()

        # Default port ranges
        self._default_ranges = [
            PortRange(start=8000, end=8050, description="Django/Development"),
            PortRange(start=8080, end=8090, description="Weaviate/HTTP Services"),
            PortRange(start=9000, end=9100, description="General Services"),
            PortRange(start=10000, end=11000, description="Extended Range"),
        ]

    def validate_port(self, port: int, host: str = None) -> bool:
        """
        Validate that a port number is within valid range

        Args:
            port: Port number to validate
            host: Host address (optional)

        Returns:
            True if port is valid, False otherwise

        Raises:
            PortOutOfRangeError: If port is out of valid range
        """
        if not isinstance(port, int):
            raise PortManagerError(message="Port must be an integer", details=f"Got: {type(port)}")

        if not (1 <= port <= 65535):
            raise PortOutOfRangeError(port)

        return True

    def validate_host(self, host: str) -> bool:
        """
        Validate a host address

        Args:
            host: Host address to validate

        Returns:
            True if host is valid, False otherwise
        """
        if not host or not isinstance(host, str):
            return False

        # Basic validation - could be enhanced
        if host in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]:
            return True

        # Check for IP address pattern
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host):
            return True

        # Check for hostname pattern
        if re.match(r"^[a-zA-Z0-9\-\.]+$", host):
            return True

        return False

    def check_port_available(self, port: int, host: str = None) -> bool:
        """
        Check if a port is available for use

        Args:
            port: Port number to check
            host: Host address to check (default: self.default_host)

        Returns:
            True if port is available, False otherwise

        Raises:
            PortOutOfRangeError: If port is out of valid range
            PortManagerError: If host is invalid
        """
        host = host or self.default_host

        # Validate inputs
        self.validate_port(port)
        if not self.validate_host(host):
            raise PortManagerError(message="Invalid host address", host=host)

        # Check if port is reserved
        with self._lock:
            if port in self._reserved_ports:
                return False

        # Try to bind to the port
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                try:
                    s.bind((host, port))
                    return True
                except (OSError, socket.error):
                    return False
        except Exception as e:
            logger.error(f"Error checking port {port} on {host}: {str(e)}")
            return False

    def reserve_port(self, port: int, host: str = None, service_name: str = None) -> bool:
        """
        Reserve a specific port

        Args:
            port: Port number to reserve
            host: Host address (default: self.default_host)
            service_name: Name of service reserving the port

        Returns:
            True if port was successfully reserved, False otherwise

        Raises:
            PortOutOfRangeError: If port is out of valid range
            PortReservationError: If port cannot be reserved
            PortNotAvailableError: If port is not available
        """
        host = host or self.default_host

        # Validate inputs
        self.validate_port(port)
        if not self.validate_host(host):
            raise PortManagerError(message="Invalid host address", host=host)

        # Check if port is reserved by someone else first
        with self._lock:
            if port in self._reserved_ports:
                raise PortReservationError(port=port, host=host, reason="Port is already reserved")

        # Check if port is available (system-level)
        if not self.check_port_available(port, host):
            raise PortNotAvailableError(port, host)

        # Reserve the port
        with self._lock:

            # Create port info
            port_info = PortInfo(
                port=port,
                host=host,
                is_available=False,
                is_reserved=True,
                service_name=service_name or "unknown",
                reservation_time=time.time(),
            )

            self._reserved_ports.add(port)
            self._port_info[port] = port_info

            logger.info(f"Port {port} reserved for {service_name or 'unknown'} on {host}")
            return True

    def release_port(self, port: int, host: str = None) -> bool:
        """
        Release a previously reserved port

        Args:
            port: Port number to release
            host: Host address (default: self.default_host)

        Returns:
            True if port was successfully released, False otherwise

        Raises:
            PortOutOfRangeError: If port is out of valid range
        """
        host = host or self.default_host

        # Validate inputs
        self.validate_port(port)

        with self._lock:
            if port not in self._reserved_ports:
                logger.warning(f"Port {port} was not reserved, cannot release")
                return False

            # Remove from reserved ports
            self._reserved_ports.discard(port)

            # Update port info
            if port in self._port_info:
                port_info = self._port_info[port]
                port_info.is_reserved = False
                port_info.is_available = True
                port_info.last_checked = time.time()

            logger.info(f"Port {port} released on {host}")
            return True

    def find_and_reserve_port(
        self,
        start: int = 8000,
        end: int = 9000,
        host: str = None,
        service_name: str = None,
        max_attempts: int = 100,
        random_search: bool = True,
    ) -> int:
        """
        Find and reserve a free port in the specified range

        Args:
            start: Start of port range (default: 8000)
            end: End of port range (default: 9000)
            host: Host address (default: self.default_host)
            service_name: Name of service for logging
            max_attempts: Maximum number of ports to try (default: 100)
            random_search: Whether to search randomly (default: True)

        Returns:
            Reserved port number

        Raises:
            PortOutOfRangeError: If start or end are out of valid range
            PortReservationError: If no port can be found and reserved
        """
        host = host or self.default_host

        # Validate range
        self.validate_port(start)
        self.validate_port(end)

        if start > end:
            raise PortManagerError(message="Invalid port range", details=f"Start ({start}) > End ({end})")

        # Get system used ports
        system_ports = self._scanner.get_system_used_ports(host)

        attempts = 0
        tried_ports = set()

        while attempts < max_attempts:
            if random_search:
                # Random search to avoid clustering
                port = random.randint(start, end)
            else:
                # Sequential search
                port = start + (attempts % (end - start + 1))

            attempts += 1

            # Skip already tried ports
            if port in tried_ports:
                continue
            tried_ports.add(port)

            # Skip system ports
            if port in system_ports:
                continue

            # Try to reserve the port
            try:
                if self.reserve_port(port, host, service_name):
                    logger.info(f"Found and reserved port {port} for {service_name or 'unknown'}")
                    return port
            except (PortNotAvailableError, PortReservationError):
                continue

        # No port found
        raise PortReservationError(
            port=None, host=host, reason=f"No available port found in range {start}-{end} after {attempts} attempts"
        )

    def find_free_port(self, start: int = 8000, end: int = 9000, host: str = None) -> Optional[int]:
        """
        Find a free port without reserving it

        Args:
            start: Start of port range (default: 8000)
            end: End of port range (default: 9000)
            host: Host address (default: self.default_host)

        Returns:
            Free port number or None if not found
        """
        host = host or self.default_host

        # Validate range
        try:
            self.validate_port(start)
            self.validate_port(end)
        except PortOutOfRangeError:
            return None

        if start > end:
            return None

        # Get system used ports
        system_ports = self._scanner.get_system_used_ports(host)

        # Check reserved ports
        with self._lock:
            reserved_ports = self._reserved_ports.copy()

        # Find first available port
        for port in range(start, end + 1):
            if port not in system_ports and port not in reserved_ports:
                if self.check_port_available(port, host):
                    return port

        return None

    def get_reserved_ports(self) -> Dict[int, PortInfo]:
        """
        Get information about all reserved ports

        Returns:
            Dictionary of port numbers to PortInfo objects
        """
        with self._lock:
            return self._port_info.copy()

    def get_port_info(self, port: int) -> Optional[PortInfo]:
        """
        Get information about a specific port

        Args:
            port: Port number to get info for

        Returns:
            PortInfo object or None if port is not tracked
        """
        with self._lock:
            return self._port_info.get(port)

    def release_all_ports(self) -> int:
        """
        Release all reserved ports

        Returns:
            Number of ports released
        """
        with self._lock:
            count = len(self._reserved_ports)
            self._reserved_ports.clear()

            # Update all port info
            for port, port_info in self._port_info.items():
                port_info.is_reserved = False
                port_info.is_available = True

            logger.info(f"Released {count} reserved ports")
            return count

    def scan_ports(self, start: int = 1, end: int = 65535, host: str = None) -> Dict[int, bool]:
        """
        Scan a range of ports and return their availability

        Args:
            start: Start of port range (default: 1)
            end: End of port range (default: 65535)
            host: Host address (default: self.default_host)

        Returns:
            Dictionary mapping port numbers to availability (True = available)
        """
        host = host or self.default_host

        # Validate range
        try:
            self.validate_port(start)
            self.validate_port(end)
        except PortOutOfRangeError:
            return {}

        if start > end:
            return {}

        # Get system used ports
        system_ports = self._scanner.get_system_used_ports(host)

        # Get reserved ports
        with self._lock:
            reserved_ports = self._reserved_ports.copy()

        # Build result
        result = {}
        for port in range(start, end + 1):
            is_available = (
                port not in system_ports and port not in reserved_ports and self.check_port_available(port, host)
            )
            result[port] = is_available

        return result

    def get_port_conflicts(self, port: int, host: str = None) -> List[str]:
        """
        Get information about what's using a port

        Args:
            port: Port number to check
            host: Host address (default: self.default_host)

        Returns:
            List of strings describing what's using the port
        """
        host = host or self.default_host
        conflicts = []

        # Check if port is reserved
        with self._lock:
            if port in self._reserved_ports and port in self._port_info:
                port_info = self._port_info[port]
                conflicts.append(f"Reserved by: {port_info.service_name}")

        # Check system processes
        try:
            system = platform.system()
            if system == "Windows":
                cmd = ["netstat", "-ano"]
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        for line in result.stdout.splitlines()[2:]:
                            if f":{port}" in line or f" {port} " in line:
                                conflicts.append(f"System process: {line.strip()}")
                except:
                    pass
            else:
                # Try lsof first
                cmd = ["lsof", "-i", f":{port}"]
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        for line in result.stdout.splitlines()[1:]:
                            conflicts.append(f"Process: {line.strip()}")
                except:
                    # Fallback to ss/netstat
                    cmd = ["ss", "-tulnp"]
                    try:
                        if subprocess.run(["which", "ss"], capture_output=True).returncode == 0:
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                            if result.returncode == 0:
                                for line in result.stdout.splitlines():
                                    if f":{port}" in line:
                                        conflicts.append(f"System: {line.strip()}")
                    except:
                        cmd = ["netstat", "-tulnp"]
                        try:
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                            if result.returncode == 0:
                                for line in result.stdout.splitlines():
                                    if f":{port}" in line:
                                        conflicts.append(f"System: {line.strip()}")
                        except:
                            # Try /proc/net/tcp as last fallback
                            try:
                                if os.path.exists("/proc/net/tcp"):
                                    with open("/proc/net/tcp", "r") as f:
                                        for line in f.readlines()[1:]:  # Skip header
                                            parts = line.strip().split()
                                            if len(parts) >= 2:
                                                local_addr = parts[1]
                                                if ":" in local_addr:
                                                    port_hex = local_addr.split(":")[1]
                                                    try:
                                                        line_port = int(port_hex, 16)
                                                        if line_port == port:
                                                            conflicts.append(
                                                                f"System process using /proc/net/tcp: port {port}"
                                                            )
                                                    except ValueError:
                                                        continue
                            except:
                                pass
        except Exception as e:
            logger.warning(f"Error checking port conflicts: {str(e)}")

        return conflicts


class PortManagementAgent:
    """
    High-level Port Management Agent for integration with CrewAI and other frameworks

    This class provides a user-friendly interface to the PortManager
    and can be integrated with agent frameworks like CrewAI.
    """

    def __init__(self, port_manager: PortManager = None):
        """
        Initialize the Port Management Agent

        Args:
            port_manager: PortManager instance to use (default: new instance)
        """
        self.port_manager = port_manager or PortManager()
        self._action_handlers = {
            "scan": self._handle_scan,
            "check": self._handle_check,
            "assign": self._handle_assign,
            "release": self._handle_release,
            "status": self._handle_status,
            "reserve": self._handle_reserve,
            "find": self._handle_find,
            "conflicts": self._handle_conflicts,
            "info": self._handle_info,
        }

    def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a port management action

        Args:
            action: Action to perform (scan, check, assign, release, status, etc.)
            **kwargs: Additional parameters for the action

        Returns:
            Dictionary with result information

        Raises:
            PortManagerError: If action fails
        """
        if action not in self._action_handlers:
            available = ", ".join(self._action_handlers.keys())
            raise PortManagerError(message=f"Unknown action: {action}", details=f"Available actions: {available}")

        try:
            return self._action_handlers[action](**kwargs)
        except Exception as e:
            # Convert known exceptions to dictionary format
            if isinstance(e, PortManagerError):
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "port": getattr(e, "port", None),
                    "host": getattr(e, "host", None),
                    "details": getattr(e, "details", None),
                }
            else:
                return {"success": False, "error": str(e), "error_type": type(e).__name__}

    def _handle_scan(self, host: str = None, start: int = 1, end: int = 65535) -> Dict[str, Any]:
        """Handle port scan action"""
        host = host or self.port_manager.default_host

        try:
            result = self.port_manager.scan_ports(start, end, host)
            used_ports = [p for p, available in result.items() if not available]
            available_ports = [p for p, available in result.items() if available]

            return {
                "success": True,
                "action": "scan",
                "host": host,
                "range": {"start": start, "end": end},
                "total_ports": len(result),
                "used_ports": used_ports,
                "available_ports": available_ports[:100],  # Limit to first 100
                "used_count": len(used_ports),
                "available_count": len(available_ports),
            }
        except Exception as e:
            raise PortScanError(
                message=f"Port scan failed for range {start}-{end}", command=f"scan {start}-{end}", details=str(e)
            )

    def _handle_check(self, port: int, host: str = None) -> Dict[str, Any]:
        """Handle port check action"""
        host = host or self.port_manager.default_host

        try:
            available = self.port_manager.check_port_available(port, host)
            conflicts = []

            if not available:
                conflicts = self.port_manager.get_port_conflicts(port, host)

            return {
                "success": True,
                "action": "check",
                "port": port,
                "host": host,
                "available": available,
                "conflicts": conflicts,
            }
        except Exception as e:
            raise PortManagerError(message=f"Port check failed for port {port}", port=port, host=host, details=str(e))

    def _handle_assign(
        self, start: int = 8000, end: int = 9000, host: str = None, service_name: str = None, max_attempts: int = 100
    ) -> Dict[str, Any]:
        """Handle port assignment action"""
        host = host or self.port_manager.default_host

        try:
            port = self.port_manager.find_and_reserve_port(start, end, host, service_name, max_attempts)

            return {
                "success": True,
                "action": "assign",
                "port": port,
                "host": host,
                "service_name": service_name,
                "message": f"Port {port} assigned and reserved",
            }
        except Exception as e:
            raise PortReservationError(port=None, host=host, reason=str(e))

    def _handle_release(self, port: int, host: str = None) -> Dict[str, Any]:
        """Handle port release action"""
        host = host or self.port_manager.default_host

        try:
            success = self.port_manager.release_port(port, host)

            return {
                "success": success,
                "action": "release",
                "port": port,
                "host": host,
                "message": f"Port {port} released" if success else f"Port {port} was not reserved",
            }
        except Exception as e:
            raise PortReleaseError(port=port, host=host, reason=str(e))

    def _handle_reserve(self, port: int, host: str = None, service_name: str = None) -> Dict[str, Any]:
        """Handle port reservation action"""
        host = host or self.port_manager.default_host

        try:
            success = self.port_manager.reserve_port(port, host, service_name)

            return {
                "success": success,
                "action": "reserve",
                "port": port,
                "host": host,
                "service_name": service_name,
                "message": f"Port {port} reserved" if success else f"Port {port} not available",
            }
        except Exception as e:
            raise PortReservationError(port=port, host=host, reason=str(e))

    def _handle_find(self, start: int = 8000, end: int = 9000, host: str = None) -> Dict[str, Any]:
        """Handle find free port action"""
        host = host or self.port_manager.default_host

        try:
            port = self.port_manager.find_free_port(start, end, host)

            if port is None:
                return {
                    "success": False,
                    "action": "find",
                    "host": host,
                    "range": {"start": start, "end": end},
                    "message": f"No free port found in range {start}-{end}",
                }

            return {
                "success": True,
                "action": "find",
                "port": port,
                "host": host,
                "range": {"start": start, "end": end},
                "message": f"Found free port {port}",
            }
        except Exception as e:
            raise PortManagerError(message=f"Find port failed for range {start}-{end}", details=str(e))

    def _handle_status(self) -> Dict[str, Any]:
        """Handle status action"""
        try:
            reserved_ports = self.port_manager.get_reserved_ports()

            port_list = []
            for port, info in reserved_ports.items():
                port_list.append(
                    {
                        "port": port,
                        "host": info.host,
                        "service_name": info.service_name,
                        "reserved_at": info.reservation_time,
                        "is_available": info.is_available,
                    }
                )

            return {"success": True, "action": "status", "reserved_ports": port_list, "count": len(port_list)}
        except Exception as e:
            raise PortManagerError(message="Failed to get port status", details=str(e))

    def _handle_conflicts(self, port: int, host: str = None) -> Dict[str, Any]:
        """Handle conflicts action"""
        host = host or self.port_manager.default_host

        try:
            conflicts = self.port_manager.get_port_conflicts(port, host)

            return {
                "success": True,
                "action": "conflicts",
                "port": port,
                "host": host,
                "conflicts": conflicts,
                "has_conflicts": len(conflicts) > 0,
            }
        except Exception as e:
            raise PortManagerError(
                message=f"Failed to check conflicts for port {port}", port=port, host=host, details=str(e)
            )

    def _handle_info(self, port: int, host: str = None) -> Dict[str, Any]:
        """Handle info action"""
        host = host or self.port_manager.default_host

        try:
            info = self.port_manager.get_port_info(port)

            if info is None:
                # Get basic info
                available = self.port_manager.check_port_available(port, host)
                conflicts = self.port_manager.get_port_conflicts(port, host)

                info = PortInfo(
                    port=port,
                    host=host,
                    is_available=available,
                    is_reserved=False,
                    process_info="; ".join(conflicts) if conflicts else "None",
                )

            return {
                "success": True,
                "action": "info",
                "port": port,
                "host": host,
                "is_available": info.is_available,
                "is_reserved": info.is_reserved,
                "service_name": info.service_name,
                "process_info": info.process_info,
            }
        except Exception as e:
            raise PortManagerError(message=f"Failed to get info for port {port}", port=port, host=host, details=str(e))
