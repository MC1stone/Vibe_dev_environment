#!/usr/bin/env python3
"""NIR Intelligence Platform - Sensor document database service (OP53).

The sensor database extension: uploaded documents per sensor plus the
reference check used at project creation time (does the sensor used in
the new project have a reference entry in the sensor database?).
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Service.SensorDatabase")

DOC_TYPES = [
    ("datasheet", "Datenblatt"),
    ("manual", "Handbuch / Anleitung"),
    ("calibration", "Kalibrierung / Zertifikat"),
    ("photo", "Foto"),
    ("software", "Software / Treiber / Skript"),
    ("publication", "Publikation / Referenz"),
    ("other", "Sonstiges"),
]


def sensor_documents(sensor_key: str, user: Optional[Any] = None) -> List[Any]:
    """All documents for one sensor visible to the user (lab_shared or own).

    Returns a queryset of SensorDocument, newest first. Never raises.
    """
    from core.models import SensorDocument
    if not sensor_key:
        return SensorDocument.objects.none()
    qs = SensorDocument.objects.filter(sensor_key=sensor_key)
    if user is not None and getattr(user, "is_authenticated", False):
        from django.db.models import Q
        qs = qs.filter(Q(visibility="lab_shared") | Q(user=user))
    else:
        qs = qs.filter(visibility="lab_shared")
    return qs.order_by("-created_at")


def document_stats(documents: List[Any]) -> Dict[str, Any]:
    """Aggregated document facts for a sensor page / summary prompt."""
    by_type: Dict[str, int] = {}
    for doc in documents:
        by_type[doc.doc_type] = by_type.get(doc.doc_type, 0) + 1
    return {"count": len(documents), "by_type": by_type}


def sensors_with_documents() -> List[str]:
    """All sensor keys that have at least one lab-shared document."""
    from core.models import SensorDocument
    return list(SensorDocument.objects.filter(visibility="lab_shared")
                .values_list("sensor_key", flat=True).distinct())


def _suggested_settings(name: str) -> Optional[Dict[str, Any]]:
    """OP56: one-click suggestions for missing metadata fields of a sensor.

    Recorded settings from the database (values actually measured with
    this sensor on the platform) win over generic catalogue defaults.
    None when nothing is known - the report then shows no suggestion
    buttons. Never raises.
    """
    try:
        from services.sensor_catalog import (get_setting_options,
                                              match_model_id)
        model_id = match_model_id(name)
        if not model_id:
            return None
        suggested: Dict[str, Any] = {}
        for opt in get_setting_options():
            value = opt.get("default_value")
            if value is not None:
                suggested[opt["name"]] = value
        try:
            from services.sensor_catalog import _usage_from_database
            for bucket in _usage_from_database():
                if bucket.get("model_id") != model_id:
                    continue
                for key, values in (bucket.get("recorded_settings")
                                    or {}).items():
                    if values:
                        suggested[key] = values[0]
                break
        except Exception:
            pass
        return suggested or None
    except Exception:
        return None


def check_sensor_reference(instrument_types: List[str],
                           user: Optional[Any] = None) -> Dict[str, Any]:
    """Reference check at project creation (OP53).

    For every instrument type used in the new project: is there a
    reference entry in the sensor database (documents, registered
    adapter or recorded usage)? Honest result for the preparation
    report, with links so the user can act on it.
    """
    result: Dict[str, Any] = {"checked": [], "unknown": []}
    seen = set()
    for raw in instrument_types or []:
        name = str(raw or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        docs = list(sensor_documents(name, user))
        entry: Dict[str, Any] = {
            "sensor": name,
            "document_count": len(docs),
            "sensor_url": f"/projects/sensors/{name}/",
        }
        # OP56: known settings for this sensor are offered as one-click
        # suggestions for missing metadata fields (e.g. SparkFun Triad).
        # Recorded values from the database win over generic defaults -
        # they are the values actually measured with this sensor on the
        # platform. Never raises; without a match no suggestions appear.
        entry["suggested_settings"] = _suggested_settings(name)
        if docs:
            entry["documents"] = [d.get_summary() for d in docs[:10]]
            result["checked"].append(entry)
        else:
            result["unknown"].append(entry)
    return result


def instrument_types_from_report(project) -> List[str]:
    """The instrument types recorded in a project's preparation report."""
    types: List[str] = []
    report = getattr(project, "preparation_report", None) or {}
    for dataset in report.get("datasets", []) or []:
        metadata = dataset.get("metadata") or {}
        value = metadata.get("instrument_type") or metadata.get("instrument")
        if value:
            types.append(str(value))
    return types
