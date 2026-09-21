# NIR Intelligence Platform - Base spectrometer adapter interface
# Abstract device-driver contract: measurement data, metadata, calibration
# parameters and device status (roadmap S4).

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DeviceStatus(Enum):
    """Lifecycle status of a spectrometer device connection"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    MEASURING = "measuring"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class SpectrometerCapabilities:
    """Static device capabilities reported by each adapter"""

    wavelength_range_nm: Optional[tuple] = None
    resolution_nm: Optional[float] = None
    detector_type: Optional[str] = None
    interface_type: Optional[str] = None
    supports_streaming: bool = False
    supports_external_trigger: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CalibrationParameters:
    """Device calibration as reported by the adapter"""

    wavelength_calibration: Dict[str, Any] = field(default_factory=dict)
    intensity_calibration: Dict[str, Any] = field(default_factory=dict)
    reference_measurement: Optional[str] = None
    last_calibrated: Optional[datetime] = None
    valid: bool = False


class SpectrometerAdapter(ABC):
    """Abstract adapter contract for all spectrometer devices.

    Any spectrometer (DIY camera-based, commercial NIR/UV-Vis/Raman/FTIR) is
    integrated by implementing this interface and registering the adapter in
    the SpectrometerRegistry - the platform core stays untouched.
    """

    # Unique device model identifier used for registry lookup
    MODEL_ID: str = "unknown"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.status = DeviceStatus.DISCONNECTED
        self.last_error: Optional[str] = None

    @abstractmethod
    def get_capabilities(self) -> SpectrometerCapabilities:
        """Return the static capabilities of this device model."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish the device connection. Returns True on success."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the device connection and set status to DISCONNECTED."""

    @abstractmethod
    def get_calibration(self) -> CalibrationParameters:
        """Return the current calibration parameters of the device."""

    @abstractmethod
    def get_device_status(self) -> DeviceStatus:
        """Return the current device status."""

    @abstractmethod
    def acquire_measurement(self, options: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Acquire a single measurement.

        Returns the unified spectral data schema used by the platform
        (data/metadata/format/wavelength_column/intensity_column) or None on failure.
        """

    def get_metadata(self) -> Dict[str, Any]:
        """Return descriptive device metadata (serial, location, firmware...)."""
        return {
            "model_id": self.MODEL_ID,
            "interface_type": self.get_capabilities().interface_type,
            "config": dict(self.config),
        }

    def describe(self) -> Dict[str, Any]:
        """Human-readable summary of the adapter and its device state."""
        return {
            "model_id": self.MODEL_ID,
            "status": self.status.value,
            "capabilities": self.get_capabilities().__dict__,
            "metadata": self.get_metadata(),
            "last_error": self.last_error,
        }
