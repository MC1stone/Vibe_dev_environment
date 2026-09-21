# NIR Intelligence Platform - SparkFun Triad spectrometer adapter
# Qwiic multispectral sensor board: AS7262 (visible), AS7263 (NIR) and
# ML8511 (UV). 18 fixed channels from 410 to 940 nm, matching the laboratory
# setup recorded in data/raw/T4-T5_ALLE_mit_Brix_2.txt (columns A_410..L_940).

from typing import Any, Dict, List, Optional

from .base_spectrometer import (
    CalibrationParameters,
    DeviceStatus,
    SpectrometerAdapter,
    SpectrometerCapabilities,
)
from .registry import register_adapter

# 18 channels as recorded in the tomato ripeness experiment (data/raw)
TRIAD_WAVELENGTHS: List[float] = [410.0, 435.0, 460.0, 485.0, 510.0, 535.0,
                                  560.0, 585.0, 610.0, 645.0, 680.0, 705.0,
                                  730.0, 760.0, 810.0, 860.0, 900.0, 940.0]

# Column labels used by the raw lab data (A_410 .. L_940)
TRIAD_COLUMN_PREFIXES: List[str] = ["A", "B", "C", "D", "E", "F",
                                    "G", "H", "R", "I", "S", "J",
                                    "T", "U", "V", "W", "K", "L"]


@register_adapter
class SparkFunTriadAdapter(SpectrometerAdapter):
    """Adapter for the SparkFun Triad multispectral sensor (Qwiic / I2C)

    The physical I2C transport is owned by the acquisition layer; this adapter
    normalizes Triad channel payloads (as stored in the lab data files) into
    the unified spectral data schema.
    """

    MODEL_ID = "sparkfun_triad"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.i2c_bus = int(self.config.get("i2c_bus", 1))
        self.i2c_address = self.config.get("i2c_address", 0x49)
        self.serial_number = self.config.get("serial_number", "TRIAD-000")
        self.wavelengths: List[float] = self.config.get("wavelengths", list(TRIAD_WAVELENGTHS))

    def get_capabilities(self) -> SpectrometerCapabilities:
        return SpectrometerCapabilities(
            wavelength_range_nm=(min(self.wavelengths), max(self.wavelengths)),
            resolution_nm=None,
            detector_type="as7262+as7263+ml8511",
            interface_type="qwiic_i2c",
            supports_streaming=False,
            supports_external_trigger=False,
            metadata={
                "sensors": ["AS7262 (visible)", "AS7263 (NIR)", "ML8511 (UV)"],
                "num_channels": len(self.wavelengths),
                "i2c_bus": self.i2c_bus,
                "i2c_address": self.i2c_address,
                "fixed_channels": True,
            },
        )

    def connect(self) -> bool:
        self.status = DeviceStatus.CONNECTING
        if not self.wavelengths:
            self.status = DeviceStatus.ERROR
            self.last_error = "No wavelength configuration"
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
    def parse_channel_payload(payload: Dict[str, Any],
                              wavelengths: List[float]) -> Optional[Dict[str, Any]]:
        """Normalize a Triad channel payload into the unified spectral schema.

        Accepted payload shapes:
        - {"channels": {"A_410": 630.23, ..., "L_940": 1095.82}}  (lab data style)
        - {"channels": {"410": 630.23, ...}}                       (nm keys)
        - {"intensities": [...]}                                   (aligned to wavelengths)
        """
        channels = payload.get("channels")
        intensities = payload.get("intensities")

        if isinstance(channels, dict) and channels:
            values: List[Optional[float]] = [None] * len(wavelengths)
            for idx, wl in enumerate(wavelengths):
                label = f"{TRIAD_COLUMN_PREFIXES[idx]}_{wl:g}" if idx < len(TRIAD_COLUMN_PREFIXES) else None
                value = channels.get(label) if label else None
                if value is None:
                    value = channels.get(f"{wl:g}") if channels.get(f"{wl:g}") is not None else channels.get(str(wl))
                if value is None:
                    return None
                values[idx] = float(value)
            parsed_intensities: List[float] = [v for v in values if v is not None]
            if len(parsed_intensities) != len(wavelengths):
                return None
        elif isinstance(intensities, (list, tuple)):
            if len(intensities) != len(wavelengths):
                return None
            parsed_intensities = [float(v) for v in intensities]
        else:
            return None

        import pandas as pd

        return {
            "data": pd.DataFrame({"wavelength": wavelengths, "intensity": parsed_intensities}),
            "source_file": payload.get("source_file"),
            "format": "triad_channels",
            "wavelength_column": "wavelength",
            "intensity_column": "intensity",
            "metadata": {
                "session_id": payload.get("session_id"),
                "sample_id": payload.get("sample_id"),
                "integration_time_ms": payload.get("integration_time_ms"),
                "gain": payload.get("gain"),
                **(payload.get("metadata") or {}),
            },
        }

    def acquire_measurement(self, options: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        options = options or {}
        payload = options.get("channel_payload")
        if payload is None:
            self.last_error = "No channel payload provided"
            return None

        if self.status not in (DeviceStatus.CONNECTED, DeviceStatus.MEASURING):
            self.last_error = f"Device not connected (status: {self.status.value})"
            return None

        self.status = DeviceStatus.MEASURING
        result = self.parse_channel_payload(payload, self.wavelengths)
        if result is None:
            self.last_error = "Channel payload incomplete or malformed"
            self.status = DeviceStatus.ERROR
            return None

        self.status = DeviceStatus.CONNECTED
        result["metadata"]["device"] = self.MODEL_ID
        result["metadata"]["serial_number"] = self.serial_number
        return result
