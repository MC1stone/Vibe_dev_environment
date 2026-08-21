"""
Custom Exceptions for Port Management Agent

This module defines custom exceptions for comprehensive error handling
in the Port Management Agent. All exceptions inherit from PortManagerError
and provide detailed context for debugging and error reporting.

Exception Hierarchy:
- PortManagerError: Base exception for all port management errors
- PortNotAvailableError: Port is already in use or unavailable
- PortOutOfRangeError: Port number is outside valid range (1-65535)
- PortReservationError: Failed to reserve a port
- PortReleaseError: Failed to release a port
- DockerPortError: Docker-specific port management errors
- PortScanError: Port scanning operation failures
- PortConflictError: Port conflicts detected
"""

from typing import List, Optional


class PortManagerError(Exception):
    """Base exception for all port management errors"""

    def __init__(
        self,
        message: str = "Port management error occurred",
        port: Optional[int] = None,
        host: Optional[str] = None,
        details: Optional[str] = None,
    ):
        self.message = message
        self.port = port
        self.host = host
        self.details = details
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with available information"""
        parts = [self.message]
        if self.port is not None:
            parts.append(f"Port: {self.port}")
        if self.host is not None:
            parts.append(f"Host: {self.host}")
        if self.details is not None:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)

    def __str__(self) -> str:
        """String representation of the exception"""
        return str(self.args[0]) if self.args else self.message

    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"port={self.port!r}, "
            f"host={self.host!r}, "
            f"details={self.details!r})"
        )


class PortNotAvailableError(PortManagerError):
    """Exception raised when a requested port is not available"""

    def __init__(self, port: int, host: str = "127.0.0.1", reason: str = "Port is already in use"):
        super().__init__(message=f"Port {port} is not available", port=port, host=host, details=reason)
        self.reason = reason


class PortOutOfRangeError(PortManagerError):
    """Exception raised when a port number is out of valid range"""

    def __init__(self, port: int, min_port: int = 1, max_port: int = 65535):
        super().__init__(
            message=f"Port {port} is out of valid range", port=port, details=f"Valid range: {min_port}-{max_port}"
        )
        self.min_port = min_port
        self.max_port = max_port


class PortReservationError(PortManagerError):
    """Exception raised when port reservation fails"""

    def __init__(self, port: int, host: str = "127.0.0.1", reason: str = "Port reservation failed"):
        super().__init__(message=f"Failed to reserve port {port}", port=port, host=host, details=reason)
        self.reason = reason


class PortReleaseError(PortManagerError):
    """Exception raised when port release fails"""

    def __init__(self, port: int, host: str = "127.0.0.1", reason: str = "Port release failed"):
        super().__init__(message=f"Failed to release port {port}", port=port, host=host, details=reason)
        self.reason = reason


class DockerPortError(PortManagerError):
    """Exception raised for Docker-specific port management errors"""

    def __init__(
        self,
        message: str = "Docker port error",
        container_name: Optional[str] = None,
        host_port: Optional[int] = None,
        container_port: Optional[int] = None,
        details: Optional[str] = None,
    ):
        self.container_name = container_name
        self.host_port = host_port
        self.container_port = container_port
        super().__init__(message, details=details)

    def _format_message(self) -> str:
        """Format Docker-specific error message"""
        parts = [self.message]
        if self.container_name is not None:
            parts.append(f"Container: {self.container_name}")
        if self.host_port is not None:
            parts.append(f"Host Port: {self.host_port}")
        if self.container_port is not None:
            parts.append(f"Container Port: {self.container_port}")
        if self.details is not None:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)

    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"container_name={self.container_name!r}, "
            f"host_port={self.host_port!r}, "
            f"container_port={self.container_port!r}, "
            f"details={self.details!r})"
        )


class PortScanError(PortManagerError):
    """Exception raised when port scanning fails"""

    def __init__(
        self, message: str = "Port scanning failed", command: Optional[str] = None, details: Optional[str] = None
    ):
        self.command = command
        super().__init__(message, details=details)

    def _format_message(self) -> str:
        """Format port scan error message"""
        parts = [self.message]
        if self.command is not None:
            parts.append(f"Command: {self.command}")
        if self.details is not None:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)

    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"command={self.command!r}, "
            f"details={self.details!r})"
        )


class PortConflictError(PortManagerError):
    """Exception raised when port conflicts are detected"""

    def __init__(self, port: int, conflicting_services: Optional[List[str]] = None, host: str = "127.0.0.1"):
        self.conflicting_services = conflicting_services or []
        conflict_details = (
            f"Conflicting services: {', '.join(self.conflicting_services)}"
            if self.conflicting_services
            else "Multiple services conflict"
        )
        super().__init__(
            message=f"Port conflict detected on port {port}", port=port, host=host, details=conflict_details
        )
