# NIR Intelligence Platform - ESP32-S3 camera spectrometer adapter
# Edge-AI camera module (DFRobot ESP32-S3) publishing over MQTT following
# the topic spec from HANDHELD/mqtt/topic-spec.md.

from typing import Any, Dict, Optional

from .base_spectrometer import (
    CalibrationParameters,
    DeviceStatus,
    SpectrometerAdapter,
    SpectrometerCapabilities,
)
from .registry import register_adapter


@register_adapter
class ESP32S3CameraAdapter(SpectrometerAdapter):
    """Adapter for the ESP32-S3 AI camera module spectrometer (MQTT based)"""

    MODEL_ID = "esp32_s3_camera"

    # MQTT topics from HANDHELD/mqtt/topic-spec.md
    TOPIC_REGISTER = "spectral/sensor/register"
    TOPIC_SESSION_CREATE = "spectral/session/create"
    TOPIC_RAW_CAPTURE = "spectral/raw/capture"
    TOPIC_SESSION_STATUS = "spectral/session/status"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.mqtt_host = self.config.get("mqtt_host", "localhost")
        self.mqtt_port = int(self.config.get("mqtt_port", 1883))
        self.serial_number = self.config.get("serial_number", "ESP32S3-000")
        self.sensor_id = self.config.get("sensor_id")

    def get_capabilities(self) -> SpectrometerCapabilities:
        return SpectrometerCapabilities(
            wavelength_range_nm=self.config.get("wavelength_range_nm", (380.0, 1000.0)),
            resolution_nm=self.config.get("resolution_nm", 5.0),
            detector_type="esp32_s3_camera",
            interface_type="mqtt",
            supports_streaming=True,
            supports_external_trigger=True,
            metadata={
                "mqtt_host": self.mqtt_host,
                "mqtt_port": self.mqtt_port,
                "topics": [self.TOPIC_REGISTER, self.TOPIC_SESSION_CREATE,
                           self.TOPIC_RAW_CAPTURE, self.TOPIC_SESSION_STATUS],
            },
        )

    def connect(self) -> bool:
        """The MQTT broker connection is owned by the acquisition layer;
        the adapter validates its configuration as the handshake."""
        self.status = DeviceStatus.CONNECTING
        if not self.mqtt_host:
            self.status = DeviceStatus.ERROR
            self.last_error = "No MQTT host configured"
            return False
        self.status = DeviceStatus.CONNECTED
        self.last_error = None
        return True

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

    @staticmethod
    def parse_register_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a spectral/sensor/register payload (topic spec section 1)"""
        return {
            "name": payload.get("name"),
            "interface_type": payload.get("interface_type"),
            "device_path": payload.get("device_path"),
            "serial_number": payload.get("serial_number"),
            "connection_settings": payload.get("connection_settings", {}),
            "metadata": payload.get("metadata", {}),
        }

    @staticmethod
    def parse_capture_payload(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a spectral/raw/capture payload (topic spec section 3) and
        normalize it into the unified spectral data schema."""
        spectral = payload.get("spectral", {})
        wavelengths = spectral.get("wavelength")
        intensities = spectral.get("intensity")
        if wavelengths is None or intensities is None:
            return None

        return {
            "data": {"wavelength": wavelengths, "intensity": intensities},
            "source_file": payload.get("file_path"),
            "format": "camera_frame",
            "wavelength_column": "wavelength",
            "intensity_column": "intensity",
            "metadata": {
                "session_id": payload.get("session_id"),
                "sample_id": payload.get("sample_id"),
                "exposure_ms": payload.get("exposure_ms"),
                "raw_payload": payload.get("raw_payload", {}),
                **(payload.get("metadata") or {}),
            },
        }

    def acquire_measurement(self, options: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Acquire one measurement from a raw capture payload.

        options["capture_payload"]: payload dict received on TOPIC_RAW_CAPTURE.
        """
        options = options or {}
        payload = options.get("capture_payload")
        if payload is None:
            self.last_error = "No capture payload provided"
            return None

        if self.status not in (DeviceStatus.CONNECTED, DeviceStatus.MEASURING):
            self.last_error = f"Device not connected (status: {self.status.value})"
            return None

        self.status = DeviceStatus.MEASURING
        result = self.parse_capture_payload(payload)
        if result is None:
            self.last_error = "Capture payload missing wavelength/intensity arrays"
            self.status = DeviceStatus.ERROR
            return None

        self.status = DeviceStatus.CONNECTED
        result["metadata"]["device"] = self.MODEL_ID
        result["metadata"]["serial_number"] = self.serial_number
        return result
