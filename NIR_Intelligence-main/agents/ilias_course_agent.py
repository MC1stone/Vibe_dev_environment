#!/usr/bin/env python3
"""NIR Intelligence Platform - ILIAS Course Development Agent.

Owns continuous course development for the platform: derives NIR
curricula (learning paths with modules and objectives) from the
platform's real capabilities and analysis templates, and syncs them to
the ILIAS container via the OP2 authenticated API client. Runs as its
own container (docker-compose service `ilias_course_agent`) alongside
the ILIAS container, so course development keeps running independently
of the Django web app.

Truthfulness rules (OP14/OP18): the agent builds curricula only from
the platform's actual feature inventory - never invents platform
capabilities; ILIAS failures degrade honestly (degraded status) and
never produce simulated sync results.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity

logger = logging.getLogger(__name__)


# --- platform capability inventory (single source: roadmap + templates) ---

PLATFORM_TOPICS: Dict[str, Dict[str, Any]] = {
    "datenimport": {
        "title": "Dateiimporte und Formate",
        "description": "Rohdatenimport unabh\u00e4ngig vom Dateiformat "
                       "(CSV, TXT, JSON, SPC, MAT, HDF5, XLSX, Parquet, Archive).",
        "objectives": [
            ("Wide-Format-Matrizen erkennen", "Kanal-Spaltenmuster identifizieren", "apply"),
            ("Metadaten aus Dateik\u00f6pfen extrahieren", "Kommentar-/Key-Value-Header lesen", "apply"),
        ],
    },
    "metadaten": {
        "title": "Metadaten und Standards",
        "description": "KI-gest\u00fctzte Metadaten-Extraktion, Relevanz-"
                       "Bewertung und Standards (ASTM E1655, ISO 12099).",
        "objectives": [
            ("Metadaten-Vollst\u00e4ndigkeit bewerten", "Pflichtfelder pr\u00fcfen", "analyze"),
            ("Standards-Konformit\u00e4t einordnen", "present/missing je Norm benennen", "analyze"),
        ],
    },
    "sensorik": {
        "title": "Sensorik und Datenqualit\u00e4t",
        "description": "Spektrometer-Adapter (SparkFun Triad, ESP32-S3, "
                       "DIY Matchbox), Sensor-Drift, Rauschen, Ausrei\u00dfer.",
        "objectives": [
            ("Spektrometer-Katalog nutzen", "F\u00e4higkeiten und Settings vergleichen", "understand"),
            ("Ausrei\u00dfer-Analyse durchf\u00fchren", "SNV + robuster z-Score interpretieren", "analyze"),
        ],
    },
    "chemometrie": {
        "title": "Chemometrie",
        "description": "PCA, PLS/PCR-Kalibration, neuronale Netze (CNN/MLP), "
                       "XAI-Visualisierungen und Kalibrationsgleichungen.",
        "objectives": [
            ("PCA-Plots interpretieren", "Scores, Loadings, Scree erkl\u00e4ren", "analyze"),
            ("Kalibration bewerten", "R\u00b2, RMSE, RMSECV, RMSEP unterscheiden", "evaluate"),
        ],
    },
    "federated": {
        "title": "Federated Learning",
        "description": "F\u00f6derierte Kalibration \u00fcber verteilte "
                       "Spektrometer-Gruppen; Privacy (nur Parameter-Updates, "
                       "Differential Privacy, Secure Aggregation).",
        "objectives": [
            ("F\u00f6derierte Runden erkl\u00e4ren", "FedAvg: lokal trainieren, aggregieren", "understand"),
            ("Privacy-Mechanismen einordnen", "Clipping, Gau\u00df-Rauschen, Budget", "analyze"),
        ],
    },
}

CURRICULUM_SEQUENCE = ["datenimport", "metadaten", "sensorik", "chemometrie", "federated"]


@dataclass
class CurriculumCatalogEntry:
    """One curriculum derived from the platform capabilities."""
    topic_key: str
    title: str
    description: str
    objectives: List[Dict[str, str]] = field(default_factory=list)

    def to_learning_path_payload(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "target_group": "students",
            "modules": [{
                "title": self.title,
                "objectives": self.objectives,
            }],
        }


class IliasCourseAgent(BaseAgent):
    """Develops and syncs NIR courses to the ILIAS container.

    The agent derives a curriculum catalog from the real platform
    feature inventory and pushes each curriculum as a learning path to
    ILIAS (reusing existing courses instead of duplicating them). It
    runs continuously in its own container (scripts/
    ilias_course_agent_runner.py) and can also be triggered via execute().
    """

    def __init__(self, **kwargs):
        super().__init__(name="IliasCourseAgent", version="1.0.0", **kwargs)
        self.config = {
            "ilias_url": kwargs.get("ilias_url", "http://ilias:80"),
            "client_id": kwargs.get("client_id", ""),
            "client_secret": kwargs.get("client_secret", ""),
            "poll_interval": int(kwargs.get("poll_interval", 300)),
        }
        self._catalog: List[CurriculumCatalogEntry] = []

    # --- curriculum development -------------------------------------------

    def build_curriculum_catalog(self) -> List[CurriculumCatalogEntry]:
        """Derive the curriculum catalog from the platform capabilities.

        Only real, implemented platform topics enter the catalog - the
        inventory is the source of truth, nothing is invented.
        """
        catalog: List[CurriculumCatalogEntry] = []
        for topic_key in CURRICULUM_SEQUENCE:
            topic = PLATFORM_TOPICS.get(topic_key)
            if not topic:
                continue
            objectives = [
                {"title": t, "description": d, "target_level": lvl}
                for (t, d, lvl) in topic.get("objectives", [])
            ]
            catalog.append(CurriculumCatalogEntry(
                topic_key=topic_key,
                title=topic["title"],
                description=topic["description"],
                objectives=objectives,
            ))
        self._catalog = catalog
        return catalog

    def catalog_status(self) -> Dict[str, Any]:
        if not self._catalog:
            self.build_curriculum_catalog()
        return {
            "curricula": len(self._catalog),
            "topics": [e.topic_key for e in self._catalog],
            "objectives": sum(len(e.objectives) for e in self._catalog),
        }

    # --- ILIAS sync -------------------------------------------------------

    def _learning_service(self):
        from services.ilias_learning_service import (
            LearningModule,
            LearningObjective,
            LearningPath,
            create_ilias_learning_service,
        )
        return create_ilias_learning_service(config={
            "ilias_url": self.config["ilias_url"],
            "client_id": self.config["client_id"],
        }), LearningPath, LearningModule, LearningObjective

    def _api_client(self):
        from services.ilias_api_service import IliasApiClient, IliasTokenClient
        config = {
            "ilias_url": self.config["ilias_url"],
            "client_id": self.config["client_id"],
            "client_secret": self.config["client_secret"],
        }
        return IliasApiClient(config=config, token_client=IliasTokenClient(config=config))

    def sync_curriculum(self, entry: CurriculumCatalogEntry) -> Dict[str, Any]:
        """Sync one curriculum to ILIAS; reuse existing courses (OP2 lookup)."""
        service, LearningPath, LearningModule, LearningObjective = \
            self._learning_service()
        course_ref_id = None
        try:
            api_client = self._api_client()
            course_ref_id = api_client.find_course_ref_id_by_title(entry.title)
        except Exception as exc:
            logger.warning("ILIAS course lookup failed (degraded): %s", exc)
        modules = [LearningModule(
            title=entry.title,
            objectives=[LearningObjective(**o) for o in entry.objectives],
        )]
        path = LearningPath(title=entry.title, description=entry.description,
                            target_group="students", modules=modules)
        outcome = service.sync_learning_path(path, course_ref_id=course_ref_id)
        return {
            "topic": entry.topic_key,
            "title": entry.title,
            "success": outcome.success,
            "course_ref_id": getattr(outcome, "course_ref_id", None),
            "errors": list(getattr(outcome, "errors", []) or []),
            "reused_existing_course": course_ref_id is not None,
        }

    def develop_and_sync(self) -> Dict[str, Any]:
        """Full cycle: (re)build the catalog and sync every curriculum."""
        catalog = self.build_curriculum_catalog()
        results = [self.sync_curriculum(entry) for entry in catalog]
        synced = sum(1 for r in results if r["success"])
        degraded = all(not r["success"] for r in results)
        return {
            "curricula": len(catalog),
            "synced": synced,
            "results": results,
            "status": "degraded" if degraded else "completed",
        }

    # --- agent contract ---------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent": "ilias_course_agent",
            "version": self.version,
            "config": {"ilias_url": self.config["ilias_url"],
                       "poll_interval": self.config["poll_interval"]},
            "catalog": self.catalog_status(),
        }

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Operations: develop (catalog only) | sync (full cycle) | status."""
        try:
            self.status = AgentStatus.PROCESSING
            operation = (context or {}).get("operation", "status")
            if operation == "develop":
                catalog = self.build_curriculum_catalog()
                result = {"operation": "develop",
                          "catalog": self.catalog_status(),
                          "entries": [e.to_learning_path_payload() for e in catalog]}
            elif operation == "sync":
                result = {"operation": "sync", **self.develop_and_sync()}
            else:
                result = {"operation": "status", **self.get_status()}
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(result)
        except Exception as exc:
            return self._handle_error(exc)
