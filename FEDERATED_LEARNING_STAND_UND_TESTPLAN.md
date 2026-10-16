# Federated Learning — Stand, Übersicht und Testplan (NIR-IP)

Stand: 2026-10-16 · Baseline: `main` (Merge 551b29e, OP65b) ·
Verfasser: Head of Development (Agent-Framework-Sitzung)

Quellen: `FEDERATED_LEARNING_IMPLEMENTATIONSPLAN.md`,
`FEDERATED_SETUP_AUTH_IMPLEMENTATIONSPLAN.md`, Roadmap S9/OP3a,
`services/federated_learning_service.py`, `services/flower_server.py`,
`agents/flower_agent.py`, `django_project/api/federated_views.py`,
docker-compose (dev/prod), Testmatrizen FL1–FL6, S9, OP58.

---

## 1. Architektur-Übersicht (Ist-Stand)

```
┌─────────────────────────── nir_network (Docker, intern) ───────────────────────────┐
│                                                                                    │
│  ┌──────────────────┐   gRPC 9092/9091   ┌──────────────────┐                    │
│  │ flower_client     │◄──────────────────►│ flower_server     │                    │
│  │ (SuperNode,       │  nur Parameter-    │ (SuperLink +      │                    │
│  │  1 Gruppe =        │  Updates, NIE      │  Management-HTTP  │                    │
│  │  1 Spektrometer-  │  Rohspektren)      │  5555/5556)       │                    │
│  │  Shard)           │                    └─────────┬─────────┘                    │
│  └──────────────────┘                              │ HTTP 5556                    │
│                                                   ▼                              │
│  ┌──────────────────────────────────────────────────────────────┐                │
│  │ django_app                                                    │                │
│  │  · /federated/ (UI-Dashboard, federated.html)                 │                │
│  │  · /api/federated/consent|status|rounds|privacy (FL4)          │                │
│  │  · FL-Kern: services/federated_learning_service.py            │                │
│  │    (FedAvg/FedProx, NonIIDSharder, PrivacyAuditor, Simulation) │                │
│  │  · Flower Agent (agents/flower_agent.py): Strategie-Enums,    │                │
│  │    Privacy-Level, teils simuliert (MockStrategy) — ehrlich     │                │
│  │    als degraded gemeldet                                       │                │
│  └──────────────────────────────────────────────────────────────┘                │
└────────────────────────────────────────────────────────────────────────────────────┘

Sichtbarkeit nach außen: KEINE — Flower-Transport und Management-API sind
Compose-intern (nir_network); Host-Portfreigaben existieren im Dev-Compose
für lokale Diagnose (5555/5556/9091/9092), Prod-Konfiguration prüfen (siehe
Testplan TP-SEC).
```

**Verbindliche Grundregeln (S9/OP15):**
- Rohdaten (Spektren) verlassen den Client **nie** — nur Parameter-Updates.
- Spektren sind non-IID per Spektrometer-/Probengruppe geshardet
  (`NonIIDSharder`, Provenance-Felder der `SpectrumRecord`).
- Föderation ist **Opt-in** (Consent-Gate), Default `local_only`.
- Ehrlichkeitsregel: Nicht echt Laufendes wird `degraded`/`deferred`
  gemeldet, nie simuliert (OP14/OP18).

## 2. Baustein-Übersicht mit Reifegrad

| # | Baustein | Ort | Reifegrad | Matrizen |
|---|---|---|---|---|
| 1 | FL-Kern (Simulation) | `services/federated_learning_service.py` | ✅ Produktiv — FedAvg/FedProx, Runden-Orchestrierung, Historie | S9 28/28, FL2 20/20 |
| 2 | Flower-Transport (Compose) | `docker-compose.yml` `flower_server`/`flower_client` + `scripts/flower_*_entry.py` | ✅ FL1 umgesetzt — SuperLink/SuperNode, gRPC intern | FL1 12/12 |
| 3 | Föderierte Kalibration | `services/federated_calibration.py` (PLS-Adapter) | ✅ FL2 umgesetzt — Konvergenz gegen gepooltes Optimum | FL2 20/20 |
| 4 | Privacy | DP-Clipping/Rauschen + `PrivacyAuditor` | ✅ FL3 umgesetzt — ε-Nachweis rechenbar | FL3 25/25 |
| 5 | UI + API (Consent, Runden, Privacy-Ausweis) | `federated.html`, `api/federated_views.py`, `api/federated_urls.py` | ✅ FL4 umgesetzt | FL4 20/20 |
| 6 | ILIAS-Kopplung (Gruppen-Sessions) | `services/ilias_learning_service`-Anbindung | ✅ FL5 umgesetzt, ehrliche Degradation ohne OAuth | FL5 16/16 |
| 7 | Deployment + ILIAS-Agent Health | Compose prod + Healthcheck-Kette | ✅ FL6 | FL6 (Deployment) |
| 8 | FL-Optionen im Projekt-Workflow | OP58 | ✅ | OP58 20/20 |
| 9 | Strategie-Vielfalt (FedAdam/Yogi/SGD) | `agents/flower_agent.py` | ⚠️ Teilweise simuliert (`MockStrategy`) — ehrlich deklariert | S9 deckt Verträge |
| 10 | SecAgg/HE (blinde Aggregation) | Flower-Agent-Enums | ⚠️ Nur als Level deklariert; echte Protokoll-Nutzung offen (FL3 hat DP echt, SecAgg dokumentiert als Degradation) | FL3 dokumentiert |

**Alle 8 Matrizen laufen in CI** (`.github/workflows/ci.yml` Zeilen 53–59, 114)
und sind aktuell grün (lokal verifiziert: S9 28/28, FL1 12/12, FL2 20/20,
FL3 25/25, FL4 20/20, FL5 16/16, OP58 20/20; FL6 deployment-check in CI).

## 3. Offene Punkte / bekannte Grenzen

1. **SecAgg/HE:** Nur DP ist echte Implementierung; SecAgg/HE sind
   deklarierte Level ohne echte Protokoll-Ausführung (dokumentierte
   Degradation). Nachbau nur bei konkretem Bedarf (Anti-Code-Creep).
2. **Strategien FedAdam/Yogi/SGD:** Im Agenten simuliert; echter Nutzen
   erst mit echten TensorFlow-Köpfen und realen Runden (FL2-Adapter
   liefert PLS echt; MLP/CNN optional, graceful ohne TF).
3. **Management-API-Sicherheit:** `_session_status`/Consent laufen
   in-process im Django (FL4); Konsistenz über mehrere Worker-Prozesse
   (gunicorn) noch nicht gefordert — aktuell Dev-Stack runserver.
4. **Prod-Compose:** Port-Freigaben der Flower-Services im Dev-Compose
   dienen lokaler Diagnose; für Prod-Setup prüfen, ob Host-Bindings
   nötig sind (Empfehlung: entfernen, nir_network reicht).

## 4. Testplan

### 4.1 Stufe A — Offline-Matrizen (CI, bei jedem Commit)

Bereits etabliert und grün; Reihenfolge und Erwartung:

| Matrix | Prüft | Soll |
|---|---|---|
| `test_s9_federated_learning.py` | Kern-Verträge: FedAvg/FedProx-Semantik, Sharding, Privacy-Auditor, Historie | 28/28 |
| `test_fl1_flwr_runtime.py` | flwr-Runtime-Simulation, Compose-Services, flwr-Pinning | 12/12 |
| `test_fl2_federated_calibration.py` | Föderierte PLS-Konvergenz gegen gepooltes Optimum | 20/20 |
| `test_fl3_federated_privacy.py` | DP: ε-Budget rechenbar, Clipping, Utility-Verlust ehrlich | 25/25 |
| `test_fl4_federated_ui.py` | API-Routen, Consent-Vertrag, Runden/Privacy-Daten | 20/20 |
| `test_fl5_federated_ilias.py` | ILIAS-Sync-Payload, Degradation ohne OAuth | 16/16 |
| `test_fl6_deployment_ilias_agent.py` | Compose-Wiring, Healthcheck-Kette | grün |
| `test_op58_federated_options.py` | FL-Optionen im Projekt-Workflow | 20/20 |

### 4.2 Stufe B — Container-Integrationstest (auf dem Zielrechner, einmalig je Release)

**TP-1 Stack-Hochfahrt**
```bash
docker compose up -d flower_server flower_client
docker compose ps          # beide Services Running/Healthy
docker compose logs --since 2m flower_server | tail -20   # SuperLink lauscht auf 9092, kein Fehler
docker compose logs --since 2m flower_client | tail -20  # SuperNode verbindet sich, keine Retry-Schleife
```
Akzeptanz: Client registriert sich beim SuperLink; keine Crash-Loop
(Beachten: erster Start installiert flwr im Container, dauert ~1–2 min).

**TP-2 Privacy-Vertrag im echten Transport**
```bash
docker compose logs flower_client 2>&1 | grep -i "spectra\|wavelength\|raw"
```
Akzeptanz: **keine** Treffer — im Transport-Payload dürfen nur
Parameter-Updates auftreten (Kernregel). Falls Treffer: kritischer Bug.

**TP-3 Django-Integration (Consent-Gate)**
```bash
# ohne Consent: Status muss local_only melden
curl -s http://localhost:8000/api/federated/status/ | python3 -m json.tool
# Consent geben (als angemeldeter User im Browser oder mit Session):
#   POST /api/federated/consent/ {"consent": true}
# danach: privacy_level == "federated"
```
Akzeptanz: Status folgt dem Consent (Opt-in-Vertrag), niemals still.

**TP-4 Runden-Lauf mit echten Daten**
1. Im UI `/federated/`: Session starten (Consent vorher erteilen).
2. Mindestens 2 Client-Gruppen (Shards) beteiligen — im Dev-Stack der
   eine `flower_client` plus Simulation als zweite Gruppe.
3. Runden-Verlauf im Dashboard beobachten: Konvergenz-Kurve muss fallen
   (Loss/RMSE), Runden zählen hoch.
4. Nach Abschluss: globales Modell als Kalibration speicherbar
   (Modell-Registry, FL4-Vertrag).

Akzeptanz: Runden-Historie wächst, Konvergenz plausibel, kein 500er,
Privacy-Ausweis zeigt ε-Verbrauch.

**TP-5 ILIAS-Kopplung (wenn OAuth aktiv)**
- Föderierte Gruppen-Session in ILIAS-Kurs anlegen → Status-Sync in der
  Gruppe sichtbar.
- Ohne OAuth: UI zeigt ehrliche Degradation (FL5-Vertrag), kein Fake.

### 4.3 Stufe C — Regressionen (nach jeder FL-Änderung)

```bash
# Offline-Matrizen (CI entspricht)
python tests/test_s9_federated_learning.py
python tests/test_fl1_flwr_runtime.py
python tests/test_fl2_federated_calibration.py
python tests/test_fl3_federated_privacy.py
python tests/test_fl4_federated_ui.py
python tests/test_fl5_federated_ilias.py
# keine FL-Änderung ohne grüne Kern-Regressionen (Iterationsregel)
```

### 4.4 Abnahme-Kriterien (Definition of Done für FL-Änderungen)

- Alle Matrizen Stufe A grün; TP-1 bis TP-4 auf dem Zielrechner bestanden.
- Privacy-Vertrag (TP-2) nachweisbar erfüllt.
- Consent-Gate (TP-3) schaltet `local_only` ↔ `federated` korrekt.
- Ehrlichkeitsregel: jede nicht echte Funktion ist als `degraded`
  sichtbar (keine simulierten Metriken in Reports).
- Roadmap/TASK.md aktualisiert (Iterationsregel, ERRORS = 0).

## 5. Empfohlene nächste Schritte (Priorität, Anti-Creep-geprüft)

1. **TP-1 bis TP-4 einmalig auf dem Zielrechner durchlaufen** — die
   Offline-Matrizen sind grün, der echte Container-Lauf ist aber noch
   nicht systematisch dokumentiert (OP3a-Charakter).
2. **Prod-Compose-Prüfung (TP-SEC):** Flower-Host-Ports im Prod entfernen,
   falls nicht benötigt (nir_network-intern reicht).
3. **Bei Artikel-Bedarf:** Föderierte Session mit deinen zwei Tomaten-
   Datensätzen als zwei Shards (Operator A / Operator B) — direkte
   Fortsetzung des Fusion-Themas: „zentrales Training ohne Daten teilen".
   (Wäre zugleich ein schöner FL2-Live-Nachweis.)
4. SecAgg/HE und weitere Strategien: **bewusst zurückgestellt**, bis ein
   konkreter Anwendungsfall sie fordert (Anti-Code-Creep).
