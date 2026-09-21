# NIR Intelligence Platform - DIY Matchbox spectrometer adapter
# Camera-based DIY spectrometer (matchbox style) connected via USB camera.
# Measurement payloads follow the MQTT topic spec from HANDHELD/mqtt/topic-spec.md.

from typing import Any, Dict, Optional

from .base_spectrometer import (
    CalibrationParameters,
    DeviceStatus,
    SpectrometerAdapter,
    SpectrometerCapabilities,
)
from .registry import register_adapter


@register_adapter
class DIYMatchboxAdapter(SpectrometerAdapter):
    """Adapter for the DIY matchbox spectrometer (USB camera based)"""

    MODEL_ID = "diy_matchbox"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.device_path = self.config.get("device_path", "/dev/video0")
        self.serial_number = self.config.get("serial_number", "MBS-000")
        self.resolution = self.config.get("resolution", "1920x1080")
        self._calibration = CalibrationParameters()

    def get_capabilities(self) -> SpectrometerCapabilities:
        return SpectrometerCapabilities(
            wavelength_range_nm=self.config.get("wavelength_range_nm", (380.0, 780.0)),
            resolution_nm=self.config.get("resolution_nm", 2.0),
            detector_type="usb_camera",
            interface_type="usb_camera",
            supports_streaming=True,
            metadata={"resolution": self.resolution, "grating": self.config.get("grating", "1000 lines/mm")},
        )

    def connect(self) -> bool:
        try:
            self.status = DeviceStatus.CONNECTING
            # Camera presence is validated lazily on first capture; here we only
            # accept the configuration as the connection handshake.
            if not self.device_path:
                self.status = DeviceStatus.ERROR
                self.last_error = "No camera device path configured"
                return False
            self.status = DeviceStatus.CONNECTED
            self.last_error = None
            return True
        except Exception as e:
            self.status = DeviceStatus.ERROR
            self.last_error = str(e)
            return False

    def disconnect(self) -> None:
        self.status = DeviceStatus.DISCONNECTED

    def get_calibration(self) -> CalibrationParameters:
        cal = self.config.get("calibration", {})
        return CalibrationParameters(
            wavelength_calibration=cal.get("wavelength", {}),
            intensity_calibration=cal.get("intensity", {}),
            reference_measurement=cal.get("reference_measurement"),
            valid=bool(cal.get("valid", False)),
        )

    def get_device_status(self) -> DeviceStatus:
        return self.status

    def acquire_measurement(self, options: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Acquire one frame from the camera.

        The actual camera capture happens in the acquisition layer (MQTT worker);
        this adapter accepts a raw capture payload (topic spectral/raw/capture)
        and normalizes it into the unified spectral schema.
        """
        options = options or {}
        payload = options.get("capture_payload")
        if payload is None:
            self.last_error = "No capture payload provided"
            return None

        try:
            import numpy as np
            import pandas as pd

            spectral = payload.get("spectral", {})
            wavelengths = spectral.get("wavelength")
            intensities = spectral.get("intensity")
            if wavelengths is None or intensities is None:
                self.last_error = "Capture payload missing wavelength/intensity arrays"
                return None

            df = pd.DataFrame({"wavelength": wavelengths, "intensity": intensities})
            return {
                "data": df,
                "source_file": payload.get("file_path"),
                "format": "camera_frame",
                "wavelength_column": "wavelength",
                "intensity_column": "intensity",
                "metadata": {
                    "device": self.MODEL_ID,
                    "serial_number": self.serial_number,
                    "session_id": payload.get("session_id"),
                    "sample_id": payload.get("sample_id"),
                    "exposure_ms": payload.get("exposure_ms"),
                    "raw_payload": payload.get("raw_payload", {}),
                    **(payload.get("metadata") or {}),
                },
            }
        except Exception as e:
            self.last_error = str(e)
            return None
