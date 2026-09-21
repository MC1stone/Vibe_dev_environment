# NIR Intelligence Platform - Spectrometer device abstraction layer
# Unified adapter pattern so any spectrometer can be integrated without
# changing the platform core (roadmap S4, project ground rule: support all spectrometers).

from .base_spectrometer import (
    CalibrationParameters,
    DeviceStatus,
    SpectrometerAdapter,
    SpectrometerCapabilities,
)
from .registry import SpectrometerRegistry, get_registry, register_adapter

__all__ = [
    "CalibrationParameters",
    "DeviceStatus",
    "SpectrometerAdapter",
    "SpectrometerCapabilities",
    "SpectrometerRegistry",
    "get_registry",
    "register_adapter",
]
