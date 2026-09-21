# Anwender-Testplan NIR Intelligence Platform (NIR-IP)

Version: 1.0 — manueller Abnahmetest für die Plattform nach Stand
OP1–OP3 (main, Merge PR #19). Zielgruppe: Anwender vor Ort (Labor),
kein Programmierwissen erforderlich. Alle Tests laufen im Browser gegen
den laufenden Docker-Stack.

---

## 1. Vorbereitung (einmalig)

| # | Schritt | Erwartung |
|---|---|---|
| V1 | Rechner starten, mindestens 16 GB RAM frei, ~30–50 GB Disk | keine Warnungen |
| V2 | Ports frei: `ss -tlnp \| grep -E ':(8000\|8080\|8081\|8082\|8002\|6333\|6334\|5432\|5555\|5556\|11434\|6379)'` | leere Ausgabe |
| V3 | `git checkout main && git pull origin main && git log --oneline -3` | Merge PR #19 (OP3) an der Spitze |
| V4 | `cd NIR_Intelligence-main && docker compose up -d --build` | alle Container `Up`/`healthy` |
| V5 | `docker compose ps` prüfen | django, postgres, qdrant, ollama, ilias, ilias_db, napari_server, redis, flower_server aktiv |
| V6 | Erstpflege: `docker compose exec ollama ollama pull mistral:latest` und `docker compose exec ollama ollama pull nomic-embed-text:latest` | Modelle geladen (einmalig, je ~4–8 GB) |

**Automatischer Vorab-Check (optional, für Betreuer):**
Testmatrizen auf dem Host laufen lassen (Erwartung: jede Matrix endet mit
`N/N tests passed`, Exit-Code 0):

```bash
python tests/test_s3_format_loaders.py        # 7/7
python tests/test_s4_spectrometer_adapters.py # 26/26
python tests/test_s5_spectrum_similarity.py   # 16/16
python tests/test_s6_chatbot.py               # 17/17
python tests/test_s7_update_monitoring.py     # 27/27
python tests/test_s8_ilias_integration.py     # 26/26
python tests/test_s9_federated_learning.py    # 28/28
python tests/test_op1_embedding_pipeline.py  # 29/29
python tests/test_op2_ilias_token_flow.py     # 31/31
python tests/test_op3_platform_ui.py          # 40/40
```

---

## 2. System-Health (vor jedem Testlauf)

| # | Aktion | Erwartung |
|---|---|---|
| H1 | `http://localhost:8000/health/` öffnen | Status `healthy`, Services qdrant/postgres/ollama erreichbar |
| H2 | `http://localhost:8000/` (Startseite) | Seite lädt, Navigation sichtbar |
| H3 | `http://localhost:6333/dashboard` (Qdrant) | Qdrant-Dashboard erreichbar |
| H4 | `http://localhost:8080` (ILIAS) | ILIAS-Anmeldeseite lädt |

Wenn H1 rot ist: `docker compose logs -f django` prüfen, Stack neu starten, Test erst fortsetzen wenn H1–H4 grün.

---

## 3. Funktionsmodule (Kernabnahme)

### 3.1 Anmeldung & Benutzerverwaltung
| # | Aktion | Erwartung |
|---|---|---|
| A1 | `/register/` — neuen Benutzer anlegen | Bestätigung, automatische Weiterleitung |
| A2 | `/login/` — mit neuem Benutzer anmelden | Dashboard erreichbar, Benutzername sichtbar |
| A3 | Falsches Passwort eingeben | Fehlermeldung, kein Absturz |
| A4 | `/logout/` | Abmeldung, Login-Seite erscheint |

### 3.2 Datei-Upload & Analyse (OP3-Kernabnahme)
| # | Aktion | Erwartung |
|---|---|---|
| F1 | `/files/` öffnen | Statistiken, Galerie und Datei-Tabelle laden |
| F2 | Eine CSV-Spektraldatei hochladen (z. B. `data/raw/T4-T5_ALLE_mit_Brix_2.txt`) | Datei erscheint in der Tabelle, kein Fehler |
| F3 | „Analyze“ auf einer Datei | Analyse startet, Ergebnis erscheint |
| F4 | Mehrere Dateien markieren und analysieren | Sammelanalyse läuft |
| F5 | „Delete“ einer Datei | Datei verschwindet aus Tabelle |
| F6 | „Download“ einer Datei | Datei wird heruntergeladen |
| F7 | Ungültige Datei (z. B. leere .txt) hochladen | Fehlermeldung, kein Serverfehler |

### 3.3 Chatbot mit RAG (S6 + OP1)
| # | Aktion | Erwartung |
|---|---|---|
| C1 | `/chatbot/` öffnen | Chat-UI lädt, Status-Panel zeigt Modell `mistral:latest` |
| C2 | Frage stellen, z. B. „Was sagt die Analyse meiner Spektren aus?“ | Antwort erscheint, Quellen (RAG) angezeigt |
| C3 | Status-Panel prüfen | Qdrant-RAG aktiv, kein `degraded` |
| C4 | Ollama stoppen (`docker compose stop ollama`), Frage stellen | Klarer Degraded-Hinweis, kein Absturz |
| C5 | Ollama wieder starten | Chatbot antwortet wieder normal |

### 3.4 ILIAS-Lernszenarien (S8 + OP2)
| # | Aktion | Erwartung |
|---|---|---|
| I1 | `/ilias/` öffnen | ILIAS-Seite lädt, Status ablesbar |
| I2 | Lernpfad-Sync abschicken | Sync-Ergebnis wird angezeigt |
| I3 | Link zum ILIAS-Container öffnen (`http://localhost:8080`) | ILIAS öffnet sich im neuen Tab |
| I4 | Bei deaktiviertem OAuth2: Sync-Ergebnis zeigt klaren Hinweis | kein Absturz (Stub-Flow funktionsfähig) |

### 3.5 Dashboard, Agents, Spectra, Jobs
| # | Aktion | Erwartung |
|---|---|---|
| D1 | `/dashboard/` | Kennzahlen/Übersicht laden |
| D2 | `/agents/` | Agentenliste sichtbar |
| D3 | `/spectra/` | Spektren-Übersicht lädt (nach F2 mit Inhalten) |
| D4 | `/jobs/` | Analyse-Jobs aus F3/F4 sichtbar |
| D5 | `/api/agents/` im Browser | JSON-Liste der Agenten |

---

## 4. Erweiterte Prüfungen (Betreuer, optional)

| # | Aktion | Erwartung |
|---|---|---|
| E1 | napari-Server: `http://localhost:8002/docs` | FastAPI-Doku lädt |
| E2 | Flower-Server: `docker compose ps flower_server` | Container `Up` (Ports 5555/5556) |
| E3 | Update-Monitor: `python scripts/check_updates.py` | Bericht mit Komponenten-Tabellen, keine unerwarteten Flags |
| E4 | Admin: `/admin/` mit Superuser | Django-Admin erreichbar |

---

## 5. Abnahmekriterien

Der Testlauf gilt als **bestanden**, wenn:

1. H1–H4 grün sind (System-Health).
2. Alle Kernmodule (3.1–3.5) ohne Serverfehler (HTTP 5xx) durchlaufen.
3. Upload → Auto-Analyse → Chatbot-Frage mit Quellenangabe end-to-end funktioniert (F2 → F3 → C2).
4. Degraded-Fälle (C4, I4) mit klarer Meldung statt Absturz reagieren.
5. Testmatrizen aus Abschnitt 1 vollständig grün sind.

**Bei Fehlern:** Screenshot + URL + Uhrzeit notieren, `docker compose logs django` sichern und als GitHub-Issue mit den Notizen erfassen.

---

## 6. Offene Punkte, die dieser Testplan (noch) nicht abdeckt

- OP3a: echter flwr-Client-Server-Betrieb (Federated Learning über Container)
- OP4: Online-Update-Lookups (PyPI/Docker-Hub) + CI-Workflow
- OP5: echter MQTT-Broker-Worker + kommerzielle Spektrometer-Adapter (NIR, UV-Vis, Raman, FTIR)
- OP6 (PR #20, offen): echte CrewAI-Agenten + Background-Crew-Runner
- End-to-End-Pipeline Upload → Eval → Analyse → Quarto-HTML-Bericht (PR #1, Draft)
