# Implementationsplan: Ausbau des Federated Learning (NIR-IP)

Branch: `vibe/federated-learning-ausbau-53a9e6`
Status: PLAN (noch keine Implementierung — gemäß AGENTS.md §Nicht verhandelbare
Regeln erfolgt die Umsetzung erst nach Head-of-Development-Freigabe und
Roadmap-Update der einzelnen OP-Schritte)

Version: 1.0 — erstellt gemäß `AGENT_FRAMEWORK_INIT_PROMPT.md`,
`MISSION_STATEMENT.md` (Flower Federated Learning im Technologie-Stack,
Flower Agent: Federated Learning + Modellaggregation),
`REPOSITORY_ALIGNMENT_AND_ROADMAP.md` (S9 erledigt; OP3a offen) und der
Startsequenz (`TASK.md`, `task_definition.yaml`, `system_manifest.json`).

---

## 1. Ist-Stand (aus Steuerdateien + Code)

| Baustein | Datei | Stand |
|---|---|---|
| FL-Kern (transport-agnostisch) | `NIR_Intelligence-main/services/federated_learning_service.py` | FedAvg/FedProx auf numpy, `NonIIDSharder`, `PrivacyAuditor`, Runden-Orchestrierung; Simulation/Standalone |
| Flower-Transport | `NIR_Intelligence-main/services/flower_server.py` | HTTP-Management (5556) + Flower-Server (5555); FedAvg/FedProx; genutzte flwr-API teils veraltet (`ServerApp(server_address=...)`) |
| Flower Agent | `NIR_Intelligence-main/agents/flower_agent.py` | Enum-Strategien (FedAvg/Prox/Adam/Yogi/SGD), Privacy-Level (DP, SecAgg, HE) — aber weitgehend simuliert (`MockStrategy`, Fake-Metriken, Fake-Parameter) |
| Compose-Service | `docker-compose.yml` / `.prod.yml` | `flower_server`-Service vorhanden |
| Tests | `tests/test_s9_federated_learning.py` | 28/28 grün — Kern-Verträge |
| Offen laut Roadmap | OP3a | Echter flwr-Client-Server-Betrieb gegen laufende Container |
| Offen laut Roadmap | S9-Restpunkte | Anbindung an echte Kalibrationsmodelle (S7-Optimierungsprotokoll) |
| Offen laut PRODUCTION_SETUP.md | — | ILIAS-Kommunikation im Födersystem, User-Acceptance-Workflow, föderierte Kalibrationsentwicklung |

**Grundregeln (aus S9/OP15 verbindlich):** Rohdaten (Spektren) verlassen den
Client nie — nur Modellparameter-Updates. Spektren sind non-IID per
Spektrometer-/Probengruppe geshardet. Anti-Code-Creep: kleinste korrekte
Lösung, keine neuen Abhängigkeiten ohne Not (`flwr>=1.4.0` ist bereits
gepinnt in allen requirements-Varianten).

---

## 2. Zielbild

Die NIR-IP kann föderiert Kalibrationen über verteilte Spektrometer-Setups
(Labor, Praktikumsgruppen, externe Partner) trainieren, ohne Rohspektren zu
teilen. Der Ausbau erfolgt in aufeinander aufbauenden OPs (OP-Nummern
gemäß Systematik in TASK.md/Roadmap). Jeder OP: focussierter Commit,
Testmatrix, CI-Zeile, Rückmeldung in Roadmap + TASK.md.

---

## 3. Geplante Schritte (OPs)

### FL1 — Echter flwr-Client-Server-Betrieb ( OP3a)

**Ziel:** Der transport-agnostische FL-Kern läuft über den echten
Flower-Transport statt nur in der Simulation.

- `services/flower_server.py`: Migration auf die aktuelle flwr-1.x-API
  (`ServerApp` + `ServerAppComponents`, `flwr.server.start_server` bzw.
  gRPC-Loopback im Compose-Netz — KEIN öffentlicher Listener über die
  Sandbox/Host-Grenze hinaus; nur `nir_network`-interne Kommunikation).
- `services/flower_client_app.py` (neu): `ClientApp` mit `NumPyClient`,
  der `FederatedLearningService.client_update` (Ridge-Kern) als lokale
  Trainingslogik nutzt — identische Semantik wie die S9-Simulation.
- Compose: `flower_server`-Service + ein beispielhafter Client-Service
  (模拟: ein Container pro Spektrometer-Gruppe, Sharding über Env/Group).
- Testmatrix: `tests/test_fl1_flwr_runtime.py` — Simulation-Engine
  (`flwr.simulation`), Agreement S9-Kern ↔ flwr-Ergebnis.

### FL2 — Echte Kalibrationsmodelle statt nur Ridge-Kern (S9-Restpunkt)

**Ziel:** Föderiertes Training der echten Kalibrationsmodelle.

- `services/federated_calibration.py`: Adapter, der PLS (sklearn) und
  MLP/CNN-Head (tensorflow optional, graceful ohne) in `ModelUpdate`-
  Parameter übersetzt — Anschluss an das S7-Optimierungsprotokoll.
- Kopplung an `spectrum_database.py`: Sharding über `instrument_type` /
  `sample_type` der `SpectrumRecord`-Provenance-Felder (gleiche non-IID-
  Dimensionen wie OP15).
- Testmatrix: föderierte PLS-Kalibration konvergiert gegen gepooltes
  Optimum; non-IID-Shards aus der echten Triad-/ESP32-Datenlage.

### FL3 — Privacy-Ausbau: Differential Privacy + Secure Aggregation

**Ziel:** Die im Flower-Agenten nur simulierten Privacy-Level werden echt.

- DP: client-seitiges Gradient-/Parameter-Clipping + kalibriertes Gauß-/
  Laplace-Rauschen (ε/δ aus `FederatedLearningConfig`), Privacy-Budget-
  Accounting pro Runde.
- SecAgg: serverseitig blinde Aggregation (flwr-eigene SecAgg-Plus-
  Protokolle, sofern in flwr>=1.4 enthalten; sonst dokumentierte,
  ehrliche Degradation — nichts simulieren, was nicht echt läuft).
- `PrivacyAuditor` erweitert: Audit auch für den echten Transport-Payload.
- Testmatrix: ε-Verbrauch nachrechenbar; Utility-Verlust (RMSE-Delta)
  wird ehrlich gemessen und dokumentiert.

### FL4 — Föderierte Kalibrations-Entwicklung + UI (PRODUCTION_SETUP-Restpunkte)

**Ziel:** Nutzer-Sichtbarkeit und Akzeptanz-Workflow.

- Django-API (`api/federated_views.py` + `federated_urls.py`): Start/Stop
  einer föderierten Session, Runden-Historie (aus dem S9-`history`-Vertrag),
  Privacy-/Gruppenstatus, Freigabe (`explicit consent` gemäß
  WORKFLOW_INTEGRATION.md — Föderation ist Opt-in, Default local_only).
- Template `federated.html` + Nav-Eintrag: Runden-Dashboard
  (Teilnehmer-Gruppen, Konvergenzverlauf, Privacy-Ausweis).
- Föderierte Kalibrationsentwicklung: globales Modell als wiederverwendbare
  Kalibration in der Plattform speichern (Modell-Registry, Versionierung).
- Testmatrix: Wiring, Consent-Vertrag, Runden-Darstellung.

### FL5 — ILIAS-Kommunikation im Födersystem (PRODUCTION_SETUP-Restpunkt, S8-Kopplung)

**Ziel:** Föderierte Sessions (Praktikumsgruppen) über ILIAS koordinieren.

- Lernpfad-/Kurs-Anbindung (OP2 `IliasApiClient`): föderierte Gruppen-
  Sessions als ILIAS-Kontext, Status-Sync an die Gruppe.
- Ehrliche Degradation, wenn ILIAS-OAuth2 nicht aktiv ist (OP2-Vertrag).
- Testmatrix: Sync-Payload, Degradationspfad.

**Reihenfolge:** FL1 → FL2 → FL3 → FL4 → FL5 (FL2/FL3 teilweise parallel
möglich; FL4/FL5 bauen auf dem laufenden Transport auf).

---

## 4. Nicht-Ziele / Out of Scope

- Öffentlich erreichbare Föderations-Endpunkte (Sandbox-/Hostgrenze) —
  nur container-/loopback-interne Kommunikation.
- Keine neuen Python-Abhängigkeiten; `flwr`, `numpy`, `scikit-learn`,
  `tensorflow` (optional) sind bereits im Stack.
- Weaviate bleibt out of scope; Qdrant unverändert.
- Keine Änderungen an `nir_platform/`, `HANDHELD/`, `framework/`
  (S1-Konsolidierungsregeln).

---

## 5. Verifikations- und Abnahmeregeln

- Jeder OP erhält eine eigene Testmatrix (`tests/test_fl<N>_*.py`) +
  CI-Zeile in `.github/workflows/ci.yml`; alle bisherigen Matrizen
  (S3–S9, OP1–OP44) bleiben grün (Iterationsregel: ERRORS = 0,
  CRITICAL_WARNINGS = 0, OPEN_CHANGE_REQUESTS = 0).
- Privacy-Vertrag bleibt in jedem Schritt verifizierbar: nur Parameter-
  Updates im Transport-Payload (`PrivacyAuditor`).
- Ehrlichkeits-Regel (OP14/OP18): keine simulierten Metriken — was nicht
  echt läuft, wird als `degraded`/`deferred` gemeldet.
- Nach jedem OP: Roadmap-Update (OP-Eintrag in
  `REPOSITORY_ALIGNMENT_AND_ROADMAP.md`) + TASK.md-Aktualisierung.
