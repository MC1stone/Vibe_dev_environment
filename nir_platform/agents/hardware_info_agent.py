"""Hardware Information Agent for the NIR Intelligence Platform.

Collects and consolidates all available information about the hardware
(spectrometer / sensor) that produced a given spectral measurement. The
platform already detects the spectrometer type (SpectralAnalysisAgent) and
holds two small spectrometer knowledge bases (SpectralAnalysisAgent and
CalibrationAgent). This agent is the single, authoritative source that:

  - merges the detected spectrometer_info (from the analysis metadata),
  - merges the matching entry from the spectrometer knowledge bases,
  - derives hardware characteristics from the spectral data itself
    (wavelength range, resolution, channel count, estimated type),
  - merges any hardware-relevant fields carried in the uploaded file's
    header metadata (device name, serial, firmware, integration time,
    scans-to-average, gain, light source, ...),
  - assigns a confidence and a short provenance note per field so the UI
    can show where each value came from.

The result is a HardwareInfo dataclass serialized to a plain dict, stored
on the analysis (analysis_results['hardware_info']) and rendered both on a
dedicated /analysis/<id>/hardware/ page and as a section in the Quarto
report.
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class HardwareField:
    """A single hardware attribute with its provenance and confidence."""
    name: str
    value: Any
    source: str = "unknown"
    confidence: str = "low"  # high / medium / low

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "value": self.value,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass
class HardwareInfo:
    """Consolidated hardware information for one analysis."""
    spectrometer_type: str = "unknown"
    spectrometer_type_confidence: str = "low"
    wavelength_range: List[float] = field(default_factory=list)
    resolution_nm: Optional[float] = None
    num_channels: Optional[int] = None
    num_data_points: Optional[int] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    light_source: Optional[str] = None
    detector: Optional[str] = None
    integration_time: Optional[Any] = None
    scans_to_average: Optional[Any] = None
    gain: Optional[Any] = None
    firmware_version: Optional[str] = None
    serial_number: Optional[str] = None
    features: List[str] = field(default_factory=list)
    calibration_points: List[float] = field(default_factory=list)
    diy_components: List[str] = field(default_factory=list)
    cost: Optional[str] = None
    difficulty: Optional[str] = None
    notes: str = ""
    fields: List[HardwareField] = field(default_factory=list)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["fields"] = [f.to_dict() for f in self.fields]
        return d


# Consolidated knowledge base of known spectrometers, merging the two
# existing in-repo databases (SpectralAnalysisAgent.spectrometer_database
# and CalibrationAgent.spectrometer_database) so the hardware agent has one
# authoritative, human-readable source of hardware specs per known device.
KNOWN_SPECTROMETERS: Dict[str, Dict[str, Any]] = {
    "ocean_optics": {
        "manufacturer": "Ocean Optics (Ocean Insight)",
        "model": "USB / Flame series",
        "light_source": "external (coupled to fibre)",
        "detector": "Hamamatsu NMOS linear array",
        "wavelength_range": [200, 1100],
        "resolution": 0.5,
        "features": ["high_resolution", "uv_vis_nir"],
        "calibration_points": [250, 400, 600, 800, 1000],
        "integration_time": {"default": 100, "min": 1, "max": 10000, "unit": "ms"},
        "scans_to_average": {"default": 10, "min": 1, "max": 100},
    },
    "asd_fieldspec": {
        "manufacturer": "Malvern Panalytical (ASD)",
        "model": "FieldSpec",
        "light_source": "built-in halogen",
        "detector": "Si / InGaAs / SWIR arrays",
        "wavelength_range": [350, 2500],
        "resolution": 1.0,
        "features": ["field_portable", "vis_nir_swir"],
        "calibration_points": [350, 700, 1400, 2100],
    },
    "bruker": {
        "manufacturer": "Bruker",
        "model": "MPA / MATRIX series",
        "light_source": "internal NIR source",
        "detector": "InGaAs / FT interferometer",
        "wavelength_range": [400, 4000],
        "resolution": 2.0,
        "features": ["lab_grade", "ftir"],
        "calibration_points": [400, 1000, 2000, 3500],
    },
    "diy_raspberry": {
        "manufacturer": "DIY (Raspberry Pi)",
        "model": "Raspberry Pi + AS7262",
        "light_source": "White LED",
        "detector": "AS7262 6-channel VIS",
        "wavelength_range": [650, 1100],
        "resolution": 10.0,
        "features": ["low_cost", "visible_nir"],
        "calibration_points": [650, 800, 1000],
        "integration_time": {"default": 50, "min": 1, "max": 100, "unit": "ms"},
        "gain": {"default": 4, "min": 1, "max": 16},
        "diy_components": ["Raspberry Pi", "AS7262 sensor", "White LED"],
        "cost": "~$100",
        "difficulty": "medium",
    },
    "diy_arduino": {
        "manufacturer": "DIY (Arduino)",
        "model": "Arduino + NIR sensor",
        "light_source": "White LED",
        "detector": "TCD1304 / custom grating",
        "wavelength_range": [700, 1000],
        "resolution": 15.0,
        "features": ["low_cost", "nir_only"],
        "calibration_points": [700, 850, 1000],
    },
    "sparkfun_nir_triad": {
        "manufacturer": "SparkFun",
        "model": "Triad AS7263+AS7262 (spectral sensor)",
        "light_source": "White LED",
        "detector": "AS7263 (NIR) + AS7262 (VIS)",
        "wavelength_range": [410, 940],
        "resolution": 30.0,
        "num_channels": 18,
        "wavelengths": [410, 435, 460, 485, 510, 535, 560, 585, 610,
                        645, 680, 705, 730, 760, 810, 860, 900, 940],
        "features": ["diy", "low_cost", "fixed_filter", "vis_nir"],
        "calibration_points": [410, 610, 940],
        "integration_time": {"default": 50, "min": 1, "max": 100, "unit": "ms"},
        "scans_to_average": {"default": 4, "min": 1, "max": 32},
        "diy_components": ["SparkFun Triad (AS7263+AS7262)", "White LED", "MCU"],
        "cost": "~$50",
        "difficulty": "easy",
    },
}

# Metadata header keys (lower-cased) that carry hardware-relevant info.
_HW_HEADER_KEYS = {
    "spectrometer": "spectrometer_type",
    "device": "spectrometer_type",
    "instrument": "spectrometer_type",
    "manufacturer": "manufacturer",
    "vendor": "manufacturer",
    "model": "model",
    "serial": "serial_number",
    "serial_number": "serial_number",
    "firmware": "firmware_version",
    "firmware_version": "firmware_version",
    "integration_time": "integration_time",
    "integration": "integration_time",
    "exposure": "integration_time",
    "scans": "scans_to_average",
    "scans_to_average": "scans_to_average",
    "averages": "scans_to_average",
    "gain": "gain",
    "light_source": "light_source",
    "light": "light_source",
    "source": "light_source",
    "detector": "detector",
    "sensor": "detector",
}


class HardwareInfoAgent:
    """Collect and consolidate all available hardware information about the
    spectrometer / sensor that produced a given spectral analysis."""

    def __init__(self, agent_id: str = "hardware_info_agent"):
        self.agent_id = agent_id

    async def collect_hardware_info(
        self,
        spectrometer_type: Optional[str] = None,
        wavelengths: Optional[List[float]] = None,
        intensities: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        spectrometer_info: Optional[Dict[str, Any]] = None,
    ) -> HardwareInfo:
        """Collect hardware info from every available source.

        Sources, in order of decreasing trust:
          1. the spectrometer_info dict detected by SpectralAnalysisAgent
             (already stored in the analysis metadata),
          2. hardware-relevant fields in the uploaded file header (metadata),
          3. the known-spectrometer knowledge base (matched by type),
          4. characteristics derived from the spectral data itself.
        Each field records its provenance and a confidence rating so the
        UI can show where a value came from.
        """
        metadata = metadata or {}
        spec_info = spectrometer_info or metadata.get("spectrometer_info") or {}
        if not spectrometer_type:
            spectrometer_type = spec_info.get("type") or "unknown"

        info = HardwareInfo(spectrometer_type=spectrometer_type)
        fields: List[HardwareField] = []

        def _add(name: str, value: Any, source: str, confidence: str = "medium"):
            # Only set / record non-empty values.
            if value is None or value == "" or value == [] or value == {}:
                return
            current = getattr(info, name, None)
            if current in (None, "", [], {}, "unknown", 0) or current == [0.0, 0.0]:
                setattr(info, name, value)
                fields.append(HardwareField(name, value, source, confidence))

        # 1. Detected spectrometer_info (high confidence - derived from data).
        if spec_info:
            if spec_info.get("type"):
                _add("spectrometer_type", spec_info["type"], "spectral_detection",
                     "high")
                info.spectrometer_type_confidence = "high"
            if spec_info.get("wavelength_range"):
                _add("wavelength_range", list(spec_info["wavelength_range"]),
                     "spectral_detection", "high")
            if spec_info.get("resolution") is not None:
                _add("resolution_nm", float(spec_info["resolution"]),
                     "spectral_detection", "high")

        # 2. Known-spectrometer knowledge base (medium - reference data).
        kb = KNOWN_SPECTROMETERS.get(spectrometer_type, {})
        if kb:
            _add("manufacturer", kb.get("manufacturer"), "knowledge_base", "high")
            _add("model", kb.get("model"), "knowledge_base", "high")
            _add("light_source", kb.get("light_source"), "knowledge_base", "high")
            _add("detector", kb.get("detector"), "knowledge_base", "high")
            _add("features", kb.get("features"), "knowledge_base", "high")
            _add("calibration_points", kb.get("calibration_points"),
                 "knowledge_base", "high")
            _add("num_channels", kb.get("num_channels"), "knowledge_base", "high")
            if kb.get("wavelength_range") and not info.wavelength_range:
                _add("wavelength_range", kb["wavelength_range"],
                     "knowledge_base", "medium")
            if kb.get("resolution") is not None and info.resolution_nm is None:
                _add("resolution_nm", kb["resolution"], "knowledge_base", "medium")
            params = kb.get("integration_time")
            if params:
                _add("integration_time", params, "knowledge_base", "high")
            params = kb.get("scans_to_average")
            if params:
                _add("scans_to_average", params, "knowledge_base", "high")
            _add("gain", kb.get("gain"), "knowledge_base", "high")
            _add("diy_components", kb.get("diy_components"), "knowledge_base", "high")
            _add("cost", kb.get("cost"), "knowledge_base", "high")
            _add("difficulty", kb.get("difficulty"), "knowledge_base", "high")

        # 3. Hardware-relevant fields from the uploaded file header.
        if metadata:
            for key, value in metadata.items():
                mapped = _HW_HEADER_KEYS.get(str(key).strip().lower())
                if not mapped or value in (None, "", []):
                    continue
                if isinstance(value, list) and len(value) == 1:
                    value = value[0]
                _add(mapped, value, "file_header", "medium")

        # 4. Characteristics derived from the spectral data itself (high -
        #    directly measured from the uploaded spectrum).
        if wavelengths:
            try:
                wl = np.asarray(wavelengths, dtype=float)
                wl = wl[np.isfinite(wl)]
                if wl.size:
                    _add("wavelength_range", [float(wl.min()), float(wl.max())],
                         "spectral_data", "high")
                    _add("num_data_points", int(wl.size), "spectral_data", "high")
                    if wl.size > 1:
                        res = float(np.mean(np.diff(np.sort(wl))))
                        _add("resolution_nm", res, "spectral_data", "high")
                    if info.num_channels is None:
                        _add("num_channels", int(wl.size), "spectral_data", "medium")
            except Exception:
                pass

        info.fields = fields
        info.notes = self._build_notes(info, spectrometer_type)
        logger.info(f"Hardware info collected for type={spectrometer_type}: "
                    f"{len(fields)} fields")
        return info

    @staticmethod
    def _build_notes(info: HardwareInfo, spec_type: str) -> str:
        bits = []
        if spec_type and spec_type != "unknown":
            bits.append(f"Detected spectrometer type: {spec_type}.")
        else:
            bits.append("Spectrometer type could not be determined from the "
                        "data; hardware info is limited to file-header and "
                        "spectral-derived characteristics.")
        if info.manufacturer and info.model:
            bits.append(f"Known device: {info.manufacturer} {info.model}.")
        if info.diy_components:
            bits.append(f"DIY build ({info.cost or 'cost unknown'}, "
                        f"difficulty {info.difficulty or 'unknown'}): "
                        f"{', '.join(info.diy_components)}.")
        if not bits:
            return "No hardware information available."
        return " ".join(bits)


if __name__ == "__main__":
    import asyncio

    async def _demo():
        agent = HardwareInfoAgent()
        info = await agent.collect_hardware_info(
            spectrometer_type="sparkfun_nir_triad",
            wavelengths=[410, 435, 460, 485, 510, 535, 560, 585, 610,
                         645, 680, 705, 730, 760, 810, 860, 900, 940],
            metadata={"Integration_time": 50, "Scans": [4], "Serial": "ABC123"},
        )
        print(info.to_dict())

    asyncio.run(_demo())
