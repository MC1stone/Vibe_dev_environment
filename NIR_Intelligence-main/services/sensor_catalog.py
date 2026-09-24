# NIR Intelligence Platform - Sensor catalog service (OP29)
# Collects everything the platform knows about the spectrometers used in
# analyses: adapter profiles from the device registry (capabilities,
# calibration contract) plus the actual usage recorded in the EXISTING
# database (SpectrumRecord.instrument_type, AnalysisProject preparation
# reports and crew results) - no new tables, the user-facing constraint for
# this OP. Setting options are derived from the ParameterRecommenderAgent
# parameter catalogue and the OP28 canonical metadata fields.

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Service.SensorCatalog")

_ADAPTERS_LOADED = False

# Canonical measurement/setting fields the platform extracts (OP28) and
# their parameter semantics for the catalog. Values are honest descriptions,
# not invented device ranges.
CANONICAL_SETTING_PARAMETERS = [
    {
        "name": "integration_time",
        "description": ("Belichtungs-/Integrationszeit pro Messung. Bestimmt "
                        "das Signal-Rausch-Verhältnis; zu hohe Werte führen "
                        "zur Sättigung des Detektors."),
        "unit": "ms",
        "parameter_type": "continuous",
        "recommendation_sources": ["parameter_recommender", "data_preparation"],
    },
    {
        "name": "scan_count",
        "description": ("Anzahl der Messungen, die pro Spektrum gemittelt "
                        "werden. Höhere Werte reduzieren Rauschen, "
                        "verlängern aber die Messzeit."),
        "unit": "",
        "parameter_type": "discrete",
        "recommendation_sources": ["parameter_recommender", "data_preparation"],
    },
    {
        "name": "gain",
        "description": ("Verstärkung des Detektorsignals. Höhere Verstärkung "
                        "erhöht die Empfindlichkeit, aber auch das Rauschen."),
        "unit": "",
        "parameter_type": "continuous",
        "recommendation_sources": ["parameter_recommender"],
    },
    {
        "name": "spectral_resolution",
        "description": ("Spektrale Auflösung (Abstand benachbarter "
                        "Wellenlängenkanäle). Feinere Auflösung trennt "
                        "Spektralmerkmale besser."),
        "unit": "nm",
        "parameter_type": "continuous",
        "recommendation_sources": ["data_preparation"],
    },
    {
        "name": "wavelength_range",
        "description": ("Abgedeckter Wellenlängenbereich. Für NIR-Analysen "
                        "wird typischerweise 700-2500 nm empfohlen."),
        "unit": "nm",
        "parameter_type": "continuous",
        "recommendation_sources": ["data_preparation", "parameter_recommender"],
    },
    {
        "name": "dark_correction",
        "description": ("Dunkelstrom-Korrektur (Dark Current). Für genaue NIR-"
                        "Messungen essentiell und standardmäßig aktiviert."),
        "unit": "",
        "parameter_type": "boolean",
        "recommendation_sources": ["parameter_recommender"],
    },
    {
        "name": "temperature_compensation",
        "description": ("Temperaturkompensation des Detektors. Stabilisiert "
                        "Messungen bei wechselnden Umgebungsbedingungen."),
        "unit": "",
        "parameter_type": "boolean",
        "recommendation_sources": ["parameter_recommender"],
    },
    {
        "name": "temperature",
        "description": ("Umgebungstemperatur während der Messung. Der "
                        "optimale Bereich liegt bei 15-30 °C."),
        "unit": "°C",
        "parameter_type": "continuous",
        "recommendation_sources": ["data_preparation"],
    },
    {
        "name": "humidity",
        "description": ("Relative Luftfeuchte während der Messung. Der "
                        "optimale Bereich liegt bei 30-70 %."),
        "unit": "%",
        "parameter_type": "continuous",
        "recommendation_sources": ["data_preparation"],
    },
]

# Instrument metadata aliases (OP28) used to attribute database records to
# registered adapters when the stored name is not the exact MODEL_ID.
_INSTRUMENT_ALIASES: List[Dict[str, Any]] = [
    {"model_id": "sparkfun_triad", "keywords": ["sparkfun", "triad", "as7262", "as7263"]},
    {"model_id": "diy_matchbox", "keywords": ["matchbox"]},
    {"model_id": "esp32_s3_camera", "keywords": ["esp32", "esp32-s3", "esp32s3"]},
]


def _ensure_adapters_registered() -> None:
    """Import every module of the devices package once so the adapters
    self-register via @register_adapter. Generic scan (pkgutil) - new
    spectrometer modules are picked up without touching this file."""
    global _ADAPTERS_LOADED
    if _ADAPTERS_LOADED:
        return
    _ADAPTERS_LOADED = True
    try:
        import importlib
        import pkgutil
        import devices
        for module_info in pkgutil.iter_modules(devices.__path__):
            if module_info.name in ("registry", "base_spectrometer", "__init__"):
                continue
            try:
                importlib.import_module(f"devices.{module_info.name}")
            except Exception:
                logger.exception(
                    "Adapter module %s failed to import (non-fatal)",
                    module_info.name)
    except Exception:
        logger.exception("Device package scan unavailable (non-fatal)")


def _registry_profiles() -> List[Dict[str, Any]]:
    """Adapter profiles from the device registry (offline, no DB needed)."""
    profiles: List[Dict[str, Any]] = []
    try:
        _ensure_adapters_registered()
        from devices import get_registry
        registry = get_registry()
        for model_id in registry.list_models():
            entry: Dict[str, Any] = {"model_id": model_id}
            adapter_cls = registry.get(model_id)
            entry["adapter_class"] = getattr(adapter_cls, "__name__", "") if adapter_cls else ""
            try:
                adapter = registry.create(model_id)
                described = adapter.describe()
                caps = described.get("capabilities") or {}
                entry["status"] = described.get("status")
                entry["capabilities"] = caps
                entry["device_metadata"] = described.get("metadata") or {}
                entry["last_error"] = described.get("last_error")
            except Exception as exc:  # adapter instantiation failure is honest data
                entry["status"] = "error"
                entry["error"] = str(exc)
            profiles.append(entry)
    except Exception:
        logger.exception("Device registry unavailable (non-fatal)")
    return profiles


def match_model_id(instrument_type: str) -> Optional[str]:
    """Attribute an instrument_type string to a registered adapter MODEL_ID.

    Exact match first, then keyword-based matching (lab notes often use the
    human-readable name, e.g. 'SparkFun NIR Triad' instead of
    'sparkfun_triad'). Returns None when no adapter matches - the sensor
    stays listed with its recorded name (honest, no invented mapping).
    """
    if not instrument_type:
        return None
    normalized = (instrument_type or "").strip().lower()
    _ensure_adapters_registered()
    try:
        from devices import get_registry
        models = get_registry().list_models()
    except Exception:
        models = []
    for model_id in models:
        if normalized == model_id.lower():
            return model_id
    for alias in _INSTRUMENT_ALIASES:
        if any(keyword in normalized for keyword in alias["keywords"]):
            return alias["model_id"]
    return None


def _canonicalize_parameters(parameters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Serialize recommender SpectrometerParameter dataclasses into plain
    dicts with the catalog field names."""
    canonical = []
    for parameter in parameters or []:
        if isinstance(parameter, dict):
            canonical.append(dict(parameter))
            continue
        canonical.append({
            "name": getattr(parameter, "name", ""),
            "description": getattr(parameter, "description", ""),
            "unit": getattr(parameter, "unit", ""),
            "min_value": getattr(parameter, "min_value", None),
            "max_value": getattr(parameter, "max_value", None),
            "default_value": getattr(parameter, "default_value", None),
            "parameter_type": getattr(parameter, "parameter_type", "continuous"),
            "possible_values": list(getattr(parameter, "possible_values", []) or []),
        })
    return canonical


def get_setting_options() -> List[Dict[str, Any]]:
    """Setting options the platform can assess and recommend for a sensor.

    Merges the ParameterRecommenderAgent parameter catalogue (analytical
    ranges per parameter) with the canonical OP28 setting fields recorded
    in metadata. Both sources describe the same parameters; the recommender
    contributes value ranges, the canonical list contributes the fields the
    platform actually extracts from measurement files.
    """
    options: Dict[str, Dict[str, Any]] = {}
    for field in CANONICAL_SETTING_PARAMETERS:
        options[field["name"]] = dict(field)
    # Recommender parameter keys that describe the same canonical setting
    _RECOMMENDER_KEY_ALIASES = {
        "scans_to_average": "scan_count",
        "integration_time": "integration_time",
        "wavelength_range": "wavelength_range",
        "spectral_resolution": "spectral_resolution",
        "gain": "gain",
        "temperature_compensation": "temperature_compensation",
        "dark_correction": "dark_correction",
        "laser_power": "laser_power",
    }
    try:
        from agents.parameter_recommender_agent import ParameterRecommenderAgent
        recommender = ParameterRecommenderAgent()
        parameters = (getattr(recommender, "spectrometer_types", {})
                      .get("generic", {}).get("parameters", {}))
        for key, parameter in dict(parameters or {}).items():
            name = _RECOMMENDER_KEY_ALIASES.get(str(key))
            if not name:
                continue
            parsed = _canonicalize_parameters([parameter])[0]
            merged = options.setdefault(name, {
                "name": name,
                "description": parsed.get("description", ""),
                "unit": parsed.get("unit", ""),
                "parameter_type": parsed.get("parameter_type", "continuous"),
                "recommendation_sources": ["parameter_recommender"],
            })
            for source_key, target_key in (
                    ("min_value", "min_value"),
                    ("max_value", "max_value"),
                    ("default_value", "default_value"),
                    ("possible_values", "possible_values")):
                value = parsed.get(source_key)
                if value not in (None, []):
                    merged[target_key] = value
            if "parameter_recommender" not in merged["recommendation_sources"]:
                merged["recommendation_sources"].append("parameter_recommender")
    except Exception:
        logger.exception("Parameter catalogue unavailable (non-fatal)")
    return sorted(options.values(), key=lambda option: option["name"])


def _usage_from_database(user_id: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Usage statistics per instrument from the EXISTING database tables
    (SpectrumRecord.instrument_type + project preparation/crew reports).
    No new table is read or written."""
    usage: Dict[str, Dict[str, Any]] = {}

    def _bucket(name: str) -> Dict[str, Any]:
        key = name or "unbekannt"
        if key not in usage:
            usage[key] = {
                "instrument_type": key,
                "model_id": match_model_id(key),
                "spectrum_count": 0,
                "project_count": 0,
                "last_used": None,
                "recorded_settings": {},
                "samples": [],
            }
        return usage[key]

    def _track_last_used(bucket: Dict[str, Any], created_at) -> None:
        if created_at is None:
            return
        current = bucket.get("_last_used_dt")
        if current is None or created_at > current:
            bucket["_last_used_dt"] = created_at
            bucket["last_used"] = created_at.isoformat()

    try:
        from core.models import AnalysisProject, SpectrumRecord
        spectra = SpectrumRecord.objects.all()
        projects = AnalysisProject.objects.all()
        if user_id is not None:
            spectra = spectra.filter(user_id=user_id)
            projects = projects.filter(user_id=user_id)
        for record in spectra:
            if not record.instrument_type:
                continue
            bucket = _bucket(record.instrument_type)
            bucket["spectrum_count"] += 1
            _track_last_used(bucket, getattr(record, "created_at", None))
            for key, value in (record.metadata or {}).items():
                if key in {field["name"] for field in CANONICAL_SETTING_PARAMETERS}:
                    bucket["recorded_settings"].setdefault(key, set()).add(str(value))
            if record.sample_type and record.sample_type not in bucket["samples"]:
                bucket["samples"].append(record.sample_type)
        for project in projects:
            names: set = set()
            for dataset in (project.preparation_report or {}).get("datasets", []):
                name = (dataset.get("metadata") or {}).get("instrument_type") or ""
                if name:
                    names.add(name)
            for name in names:
                _bucket(name)["project_count"] += 1
    except Exception:
        logger.exception("Database usage scan unavailable (non-fatal, offline mode)")
    for bucket in usage.values():
        bucket["recorded_settings"] = {
            key: sorted(values) for key, values in bucket["recorded_settings"].items()
        }
        bucket.pop("_last_used_dt", None)
    return sorted(usage.values(), key=lambda entry: -entry["spectrum_count"])


def get_sensor_profiles(user_id: Optional[Any] = None) -> Dict[str, Any]:
    """Full sensor catalog: registered adapters (static profiles), setting
    options and the usage actually recorded in the existing database."""
    profiles = _registry_profiles()
    usage = _usage_from_database(user_id=user_id)
    used_models = {entry["model_id"] for entry in usage if entry["model_id"]}
    for profile in profiles:
        model_id = profile["model_id"]
        profile["in_use"] = model_id in used_models
        profile["usage"] = next(
            (entry for entry in usage if entry["model_id"] == model_id), None)
    unmatched = [entry for entry in usage if not entry["model_id"]]
    return {
        "registered_sensors": profiles,
        "setting_options": get_setting_options(),
        "usage": usage,
        "unmatched_usage": unmatched,
    }


def assess_settings(metadata: Dict[str, Any],
                    setting_options: Optional[List[Dict[str, Any]]] = None
                    ) -> Dict[str, Any]:
    """Assess the recorded setting values of one measurement against the
    known plausibility rules. Honest result: unknown parameters are
    reported as missing, never invented."""
    metadata = metadata or {}
    known = {option["name"]: option for option in
             (setting_options or get_setting_options())}
    recorded = {}
    missing = []
    implausible = []
    for name in sorted(known):
        value = metadata.get(name)
        if value is None or value == "":
            missing.append(name)
            continue
        entry = {"value": value, "plausible": True}
        try:
            numeric = float(value)
            minimum = known[name].get("min_value")
            maximum = known[name].get("max_value")
            if minimum is not None and numeric < float(minimum):
                entry.update(plausible=False,
                             reason=f"Wert unter dem bekannten Minimum ({minimum})")
                implausible.append(name)
            elif maximum is not None and numeric > float(maximum):
                entry.update(plausible=False,
                             reason=f"Wert über dem bekannten Maximum ({maximum})")
                implausible.append(name)
        except (TypeError, ValueError):
            pass
        recorded[name] = entry
    completeness = 0.0
    if known:
        completeness = len(recorded) / len(known)
    return {
        "recorded_settings": recorded,
        "missing_settings": missing,
        "implausible_settings": implausible,
        "completeness": round(completeness, 3),
        "num_known_settings": len(known),
    }


def merge_recommendations(recommendation_sources: Dict[str, List[Any]]
                          ) -> List[Dict[str, Any]]:
    """Deduplicate the three existing recommendation sources into one list
    per parameter. Priority: analytical (ParameterRecommenderAgent) over
    heuristic (data-preparation) over generic (sensor dashboard). Conflicts
    are kept with both rationales (truthfulness, no silent overwrite)."""
    priority = {"analytical": 0, "heuristic": 1, "generic": 2}
    by_parameter: Dict[str, List[Dict[str, Any]]] = {}
    for source_name, recommendations in (recommendation_sources or {}).items():
        rank = priority.get(source_name, 3)
        for recommendation in recommendations or []:
            if isinstance(recommendation, dict):
                item = dict(recommendation)
            else:
                item = {
                    "parameter": getattr(recommendation, "parameter",
                                         getattr(recommendation, "parameter_name", "")),
                    "current_value": getattr(recommendation, "current_value", None),
                    "recommended_value": getattr(recommendation, "recommended_value", None),
                    "reason": getattr(recommendation, "reason",
                                       getattr(recommendation, "reasoning", "")),
                    "impact": getattr(recommendation, "impact",
                                       getattr(recommendation, "priority", "")),
                    "confidence": getattr(recommendation, "confidence", None),
                }
            parameter = item.get("parameter") or ""
            if not parameter:
                continue
            item["source"] = source_name
            item["source_rank"] = rank
            by_parameter.setdefault(parameter, []).append(item)
    merged: List[Dict[str, Any]] = []
    for parameter, items in sorted(by_parameter.items()):
        items.sort(key=lambda item: item["source_rank"])
        primary = dict(items[0])
        values = {str(item.get("recommended_value")) for item in items}
        if len(values) > 1:
            primary["conflict"] = True
            primary["alternatives"] = [
                {"source": item["source"],
                 "recommended_value": item.get("recommended_value"),
                 "reason": item.get("reason", "")}
                for item in items[1:]
            ]
        else:
            primary["conflict"] = False
            if len(items) > 1:
                primary["agreeing_sources"] = [item["source"] for item in items]
        merged.append(primary)
    return merged


def get_optimization_suggestions(sensor_results: Optional[Dict[str, Any]],
                                 parameter_recommendations: Optional[List[Any]],
                                 crew_recommendations: Optional[List[str]]
                                 ) -> List[Dict[str, Any]]:
    """One deduplicated, prioritized list of optimization suggestions per
    sensor: analytical parameter recommendations (recommender agent /
    data-preparation heuristics) merged with the generic sensor-quality
    recommendations from the OP21 dashboard logic."""
    heuristic = []
    for recommendation in parameter_recommendations or []:
        if isinstance(recommendation, dict):
            heuristic.append(recommendation)
        else:
            heuristic.append({
                "parameter": getattr(recommendation, "parameter_name",
                                     getattr(recommendation, "parameter", "")),
                "recommended_value": getattr(recommendation, "recommended_value", None),
                "reason": getattr(recommendation, "reasoning",
                                  getattr(recommendation, "reason", "")),
                "impact": getattr(recommendation, "priority", "medium"),
            })
    generic = []
    try:
        if sensor_results:
            from services.sensor_charts import sensor_recommendations
            generic = [{"parameter": "sensor_quality",
                        "recommended_value": text,
                        "reason": "Sensorqualitätsanalyse (OP21)",
                        "impact": "medium"} for text in
                       sensor_recommendations(sensor_results)]
    except Exception:
        logger.exception("Sensor quality recommendations unavailable (non-fatal)")
    for text in crew_recommendations or []:
        generic.append({"parameter": "sensor_quality",
                        "recommended_value": text,
                        "reason": "Crew-Analyse",
                        "impact": "medium"})
    merged = merge_recommendations({
        "analytical": [],
        "heuristic": heuristic,
        "generic": generic,
    })
    return merged
