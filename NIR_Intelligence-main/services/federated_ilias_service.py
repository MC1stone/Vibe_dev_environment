#!/usr/bin/env python3
# NIR Intelligence Platform - Federated ILIAS coordination service (FL5)
# Coordinates federated learning group sessions (practicum groups, each
# running one NIR client) through ILIAS: a federated session becomes an
# ILIAS course context and per-round status is synced to the group so
# students can follow the federated training in their e-learning course.
#
# Built on the OP2 authenticated API client (services/ilias_api_service.py)
# with an injectable transport; degrades honestly when ILIAS or its OAuth2
# API is not reachable - the federated session itself is unaffected
# (FL1-FL4 stay local-only capable).

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Service.FederatedIlias")

try:
    from .ilias_api_service import IliasApiClient, IliasTokenClient
    ILIAS_API_AVAILABLE = True
except ImportError:
    ILIAS_API_AVAILABLE = False


@dataclass
class FederatedGroupSession:
    """One federated session coordinated via an ILIAS course context.

    Privacy: the synced ILIAS payload carries ONLY session metadata
    (group names, round numbers, aggregate quality metrics) - never
    spectra or per-client parameter updates (FL privacy contract).
    """

    session_id: str
    title: str
    group_names: List[str] = field(default_factory=list)
    rounds_completed: int = 0
    strategy: str = "fedavg"
    status: str = "drafted"

    def to_ilias_description(self) -> str:
        groups = ", ".join(self.group_names) if self.group_names else "keine"
        return (f"Föderierte NIR-Kalibration (Strategie {self.strategy}), "
                f"Gruppen: {groups}, Runden: {self.rounds_completed}. "
                f"Nur Modellparameter werden geteilt - Rohspektren bleiben lokal.")


@dataclass
class SyncOutcome:
    success: bool
    message: str
    course_ref_id: Optional[str] = None
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"success": self.success, "message": self.message,
                "course_ref_id": self.course_ref_id, "detail": self.detail}


class FederatedIliasService:
    """Syncs federated group sessions to ILIAS via the OP2 API client.

    The transport is injectable (offline tests); every ILIAS failure is
    reported honestly (degraded status) instead of simulated.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None,
                 client: Optional[Any] = None,
                 transport: Optional[Any] = None):
        if not ILIAS_API_AVAILABLE:
            raise RuntimeError("ilias_api_service is not available")
        self.config = config or {}
        if client is not None:
            self.client = client
        else:
            self.client = IliasApiClient(
                config=self.config, token_client=IliasTokenClient(config=self.config),
                transport=transport)

    def create_session_context(self, session: FederatedGroupSession) -> SyncOutcome:
        """Create (or reuse) the ILIAS course context for a federated session."""
        try:
            existing = self.client.find_course_ref_id_by_title(session.title)
        except Exception as exc:
            return SyncOutcome(False, f"ILIAS nicht erreichbar: {exc}")
        if existing is not None:
            session.status = "synced"
            return SyncOutcome(True, "ILIAS-Kurs-Kontext bereits vorhanden",
                               course_ref_id=existing)
        try:
            response = self.client.post("/courses", json={
                "title": session.title,
                "description": session.to_ilias_description(),
            })
        except Exception as exc:
            return SyncOutcome(False, f"ILIAS nicht erreichbar: {exc}")
        status_code = getattr(response, "status_code", None)
        if status_code not in (200, 201):
            return SyncOutcome(False,
                               f"ILIAS-API lehnte den Kurs ab (HTTP {status_code})")
        course_ref_id = None
        try:
            body = response.json() if hasattr(response, "json") else {}
            course_ref_id = str(body.get("ref_id") or body.get("id") or "") or None
        except Exception:
            course_ref_id = None
        session.status = "synced"
        return SyncOutcome(True, "ILIAS-Kurs-Kontext angelegt",
                           course_ref_id=course_ref_id)

    def sync_round_status(self, session: FederatedGroupSession,
                          round_summary: Dict[str, Any],
                          course_ref_id: Optional[str] = None) -> SyncOutcome:
        """Publish a per-round status entry to the session's ILIAS context.

        The payload is metadata-only (privacy contract): round id, groups,
        aggregate RMSE - never client parameters or spectra.
        """
        if any(key in round_summary for key in ("params", "coefficients",
                                                "parameters", "spectra", "x", "y")):
            raise ValueError("round summary carries raw payload data - "
                             "privacy contract violated")
        if course_ref_id is None:
            try:
                course_ref_id = self.client.find_course_ref_id_by_title(session.title)
            except Exception as exc:
                return SyncOutcome(False, f"ILIAS nicht erreichbar: {exc}")
        if course_ref_id is None:
            return SyncOutcome(False, "kein ILIAS-Kurs-Kontext für die Session")
        try:
            response = self.client.post(
                f"/courses/{course_ref_id}/federated-rounds",
                json={"session_id": session.session_id,
                      "round": session.rounds_completed,
                      "strategy": session.strategy,
                      "groups": session.group_names,
                      "summary": round_summary},
            )
        except Exception as exc:
            return SyncOutcome(False, f"ILIAS nicht erreichbar: {exc}")
        status_code = getattr(response, "status_code", None)
        if status_code not in (200, 201):
            return SyncOutcome(False,
                               f"ILIAS-API lehnte den Runden-Status ab (HTTP {status_code})")
        return SyncOutcome(True, "Runden-Status synchronisiert",
                           course_ref_id=course_ref_id,
                           detail={"round": session.rounds_completed})

    def status(self) -> Dict[str, Any]:
        try:
            token_status = self.client.token_client.status()
        except Exception as exc:
            token_status = {"error": str(exc)}
        return {
            "service": "federated_ilias",
            "ilias_api_available": ILIAS_API_AVAILABLE,
            "token": token_status,
            "privacy_contract": "metadata-only sync - no spectra, no client parameters",
        }
