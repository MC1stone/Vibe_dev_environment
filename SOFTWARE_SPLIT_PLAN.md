# Software-Teilung: Open-Source (Teil 1) vs. Proprietäre Startup-Variante (Teil 2)

> **OP95 — Plan (noch nicht umgesetzt).** Stand 24.10.2026.
> Ausgangspunkt: Artikel-Neuausrichtung Öffentlicher Sektor (PR #242,
> `ARTICLE_UPDATE_PUBLIC_SECTOR.md`). Der Artikel beschreibt ausschließlich
> **Teil 1 (öffentlicher Sektor)**. Dieser Plan beschreibt Arbeitsschritt 2:
> die Teilung der Software.

---

## 1. Zielbild

| | **Teil 1 — Open Source (Community / Öffentlicher Sektor)** | **Teil 2 — Proprietär (Startup)** |
|---|---|---|
| Lizenz | Permissiv (MIT — Vorschlag, finale Lizenzwahl durch den Startup-Gründer) | Proprietär / kommerziell |
| Inhalt | **Grundfunktionalität** (voll funktionsfähige Analyse-Plattform) | **Alles aus Teil 1** + die drei erweiterten Funktionen (voll implementiert, nicht nur Links) |
| Erweiterte Funktionen (Lernplattform, Sensor-Quality-Datenbank, Federated Learning) | **Nur Links zur Startup-Seite** (Upsell-Platzhalter) | **Voll integriert und freigeschaltet** |
| Freischaltung | Keine — alles in Grundfunktionalität enthalten | Selektiv pro Funktion (Feature-Flags / Lizenz) |

**Kernidee (wie vom Nutzer gewünscht):** Die Open-Source-Variante enthält die
Grundfunktionalität. Für die drei weiteren Funktionen (Lernplattform,
Sensor-Quality-Datenbank, Federated Learning) zeigt sie nur **Links zu einer
Startup-Seite**. Diese Funktionen müssen **selektiv freigeschaltet** werden.
Die proprietäre Software enthält diese Funktionen **zusätzlich zum
Open-Source-Content** (voll, nicht als Links).

---

## 2. Die drei teilungspflichtigen Funktionen (selektiv freischaltbar)

| # | Funktion | Status quo im Code | Open-Source-Variante (Teil 1) | Proprietär (Teil 2) |
|---|---|---|---|---|
| F1 | **Lernplattform** (ILIAS-Integration, Intro-Seite) | `services/ilias_*.py`, `agents/ilias_*.py`, `api/ilias_views.py`, `api/ilias_urls.py`, `templates/ilias.html`, `intro_spectroscopy.html`, `IntroSpectroscopyView`, Nav-Punkt „Lernen", Docker-Services `ilias` + `ilias_db` | **Link zur Startup-Seite** (statt Funktion) | Voll funktionsfähig |
| F2 | **Sensor-Quality-Datenbank** (Sensor-Katalog, Sensor-Seiten, Dokumente, Referenz-Check) | `services/sensor_catalog.py`, `sensor_documents.py`, `sensor_summary.py`, `agents/sensor_agent.py`, `agents/sensor_quality_agent.py`, `api/project_views.py` (SensorList/Detail/Summary/Document), `api/project_urls.py` (sensors/*), `templates/sensor_list.html`, `sensor_detail.html`, `core/models.py` (`SensorDocument`), Nav-Punkt „Sensoren" | **Link zur Startup-Seite** (statt Funktion) | Voll funktionsfähig |
| F3 | **Federated Learning** (Flower-Server/Client, Consent-UI, DP, FedAvg) | `services/federated_*.py`, `services/flower_*.py`, `agents/flower_agent.py`, `api/federated_views.py`, `api/federated_urls.py`, `templates/federated.html`, `FederatedLearningView`, Nav-Punkt „Federated Learning", `FLOWERAI_ENABLED` in settings, Docker-Services `flower_server` + `flower_client` | **Link zur Startup-Seite** (statt Funktion) | Voll funktionsfähig |

**Wichtig — Präzisierung zum Artikel (PR #242):** Der Artikel beschreibt die
**Sensor-Datenbank (§3.2)** und die **standardisierte Testeinheit (§6.7)** als
Bestandteil der Plattform. Der **Referenz-Protokoll-Vertrag** (dark/white,
≥ 50 Wiederholungen, Metadaten-Schema, `(raw − dark)/(white − dark)`) ist
**kein** F2-Feature — er ist Teil der **Grundfunktionalität** (Fusion-/Qualitäts-
Grundlage, `services/fusion_sensor_analysis.py`) und bleibt in Teil 1
**vollständig enthalten**. In Teil 1 erscheint lediglich der **Sensor-Katalog**
(die Datenbank-Oberfläche mit Adapter-Registry, Nutzungsstatistiken,
Dokumenten, KI-Zusammenfassung) als Link zur Startup-Seite. Diese
Unterscheidung muss im Artikel konsistent bleiben (siehe §6 „Artikel-Konsistenz").

---

## 3. Was in Teil 1 (Open Source) verbleibt — Grundfunktionalität

Alles, was **keiner** der drei Funktionen F1–F3 ist:

- **Datenimport & Aufbereitung:** format-agnostischer Ingest (CSV/JSON/HDF5/JCAMP/OPUS),
  Metadaten-Erkennung (deterministisch + optional LLM), Bereinigung, Replikat-Handling
- **Qualitäts-Gates:** Noise/Drift/SNR/ADC-Saturation/Autoencoder-Anomalie
  (`services/outlier_analysis.py`, Sensor-Quality-Checks auf Datensatz-Ebene)
- **Statistische Analyse:** PCA, PLS, PCR, ANOVA, Clustering
- **Neuronale Analyse:** MLP, 1D-CNN, Autoencoder (mit sklearn-Fallback)
- **Kalibration:** PLS/PCR/SVM/RF/XGBoost/CNN, Kreuzvalidierung,
  Kalibrierungsgleichung, Kalibrierungs-Management
- **Fusion (Basis):** Zwei-Quellen-Fusion, Vergleichskalibration,
  Signifikanztests, Korrektur-Loop (SNV/MSC) — **inkl. Referenz-Protokoll-Vertrag**
  (dark/white, ≥ 50 Wiederholungen) und Gain-Kurve als Korrektur-Variante
  (`services/fusion_sensor_analysis.py`, `fusion_calibration.py`)
- **Ähnlichkeitssuche:** Qdrant/FAISS-Embeddings, Nearest-Neighbour
- **Reporting:** Quarto-Berichte, Chatbot zur Bericht-Diskussion, XAI-Suite
- **Visualisierung:** Spektren, SPC-Dashboard, napari-Integration
- **Plattform-Kern:** Django-Web-App, Auth, i18n (24 EU-Sprachen), PostgreSQL,
  Docker-Stack (ohne ilias/flower-Container), Geräte-Adapter (`devices/`)
- **Agenten:** alle Agenten **außer** `ilias_*`, `flower_agent` (F3),
  `sensor_agent`/`sensor_quality_agent` (F2 — siehe Ausnahme unten)

**Ausnahmen / Graubereich (Entscheidungsbedarf, siehe §7):**
- `agents/sensor_quality_agent.py` — Sensor-Quality-Analysen auf
  **Datensatz-Ebene** (Drift/Noise/SNR — Teil der Grundfunktionalität,
  bleibt in Teil 1) vs. **Sensor-Datenbank** (Katalog-Oberfläche — F2,
  Link in Teil 1). **Vorschlag:** Datensatz-Level-QA bleibt in Teil 1;
  nur die Sensor-Katalog-Seiten (`/projects/sensors/…`) werden zu Links.
- `devices/` (Adapter-Registry) — bleibt in Teil 1 (Grundfunktionalität,
  keine Datenbank-Oberfläche). Die **Sensor-Informationsseiten**, die die
  Registry auslesen, sind F2.

---

## 4. Architektur der Umsetzung

### 4.1 Feature-Flag-System (zentral, minimaler Eingriff)

Ein neues, kleines Modul `django_project/core/edition.py` (oder
`path_config.py`-Erweiterung) stellt die Edition und die Feature-Flags bereit:

```python
# NIR_IP_EDITION=open|pro   (Default: open)
# NIR_IP_STARTUP_URL=https://…  (Default: Platzhalter, im .env konfigurierbar)
EDITION = os.getenv('NIR_IP_EDITION', 'open')
FEATURES = {
    'learning_platform':  os.getenv('NIR_IP_FEATURE_LEARNING',  ...),
    'sensor_database':    os.getenv('NIR_IP_FEATURE_SENSORS',   ...),
    'federated_learning': os.getenv('NIR_IP_FEATURE_FEDERATED', ...),
}
# Default open:  alle drei = False (nur Links)
# Default pro:   alle drei = True  (voll freigeschaltet)
# Selektiv pro:  NIR_IP_FEATURE_SENSORS=true etc.
```

**Regel:** In der **Open-Source-Variante** sind die drei Flags per Default
`False` → die Funktionen werden durch **Links zur Startup-Seite** ersetzt.
Die **proprietäre Variante** setzt `NIR_IP_EDITION=pro` → alle drei Flags
`True` → Voll-Funktionalität. Selektive Freischaltung (z. B. nur F2) ist
über die Einzelflags möglich.

### 4.2 Drei Enforcement-Ebenen (Defense in Depth)

| Ebene | Wo | Was |
|---|---|---|
| **1. UI / Navigation** | `templates/base.html` (+ Footer) | Nav-Punkte „Lernen" (F1), „Sensoren" (F2), „Federated Learning" (F3) werden bei `False` zu **Link zur Startup-Seite** (neues Template-Snippet `feature_teaser.html`) |
| **2. Views / URLs** | `api/project_views.py`, `api/dashboard_views.py`, `api/views.py`, `nir_web/urls.py`, `api/project_urls.py`, `api/ilias_urls.py`, `api/federated_urls.py` | Bei `False`: Route antwortet mit **Redirect/410 + Teaser-Seite** (kein Datenzugriff); bei `True`: normaler Betrieb |
| **3. Services / Agenten** | `services/ilias_*.py`, `services/sensor_catalog.py`, `services/federated_*.py`, `agents/ilias_*.py`, `agents/sensor_agent.py`, `agents/flower_agent.py` | Guard am Service-Einstieg: `if not feature_enabled('…'): return honest „not available in this edition"` — kein stilles Auslassen |

### 4.3 Teaser-Template (Open-Source-Platzhalter)

Neues Template `templates/feature_teaser.html`: Einheitliche Karte pro
Funktion — „Diese Funktion ist in der proprietären Startup-Variante
verfügbar" + **Link zur Startup-Seite** (`NIR_IP_STARTUP_URL`) + kurze
Beschreibung, was die Funktion leistet. **Ehrlichkeitsregel:** keine
Simulation, kein toter Button — ein klarer, beschrifteter externer Link.

### 4.4 Docker-Stack

- `docker-compose.yml` (Teil 1): Services `ilias`, `ilias_db`,
  `flower_server`, `flower_client` werden **nicht gestartet**
  (`profiles: ["pro"]` — erst in Teil 2 aktiv). Die `django_app` bekommt
  `NIR_IP_EDITION=open` (Default) und `NIR_IP_STARTUP_URL` aus `.env`.
- Teil 2 (proprietär): eigenes Compose-Overlay (z. B.
  `docker-compose.pro.yml`) aktiviert die Profile + setzt
  `NIR_IP_EDITION=pro`.

### 4.5 Lizenz & Repository-Struktur

| Variante | Lizenz | Ablage |
|---|---|---|
| Teil 1 (Open Source) | MIT (Vorschlag — finale Wahl durch Gründer) | Öffentliches Repository (bestehendes Repo, Branch `main`) |
| Teil 2 (Proprietär) | Proprietär | **Privates** Repository (Startup); enthält Teil-1-Code als Git-Submodule/Subtree + proprietäre Erweiterungen |

**AGENTS.md-Lizenz-Compliance:** Die proprietäre Variante baut auf
permissiv lizenziertem Code (MIT) auf — das ist zulässig. Es wird **kein**
copyleft-lizenzierter Code (GPL/AGPL/LGPL/EPL) in Teil 2 übernommen
(siehe `THIRD_PARTY_LICENSES.md`). Die im Stack verwendeten Komponenten
(Django BSD, DRF BSD, Flower Apache-2.0, scikit-learn BSD, Qdrant
Apache-2.0, FAISS MIT, PostgreSQL PostgreSQL-Lizenz, ILIAS GPL-3.0 —
**Achtung:** ILIAS ist GPL; als **externer Docker-Container** (Dienst)
betrieben, nicht eingebunden, daher unkritisch, aber in Teil 2 separat
prüfen) sind zu dokumentieren.

---

## 5. Umsetzungs-Schritte (Reihenfolge)

| Schritt | Inhalt | Dateien (ungefähr) | Aufwand |
|---|---|---|---|
| **S1** | `core/edition.py` (oder `path_config.py`-Erweiterung): Edition + Feature-Flags + `feature_enabled()` + `startup_url()` | `django_project/core/edition.py` (neu), `settings.py` (Env-Defaults) | klein |
| **S2** | Teaser-Template + Template-Tag/Snippet | `templates/feature_teaser.html` (neu), `base.html` (Nav-Umbau) | klein |
| **S3** | View/URL-Guards für F1 (Lernplattform) | `nir_web/urls.py`, `api/ilias_urls.py`, `api/ilias_views.py`, `api/dashboard_views.py` (`IntroSpectroscopyView`), `api/views.py` (`ILIASAuthView`) | mittel |
| **S4** | View/URL-Guards für F2 (Sensor-Datenbank) | `api/project_urls.py` (sensors/*), `api/project_views.py` (SensorList/Detail/Summary/Document), `templates/sensor_list.html`, `sensor_detail.html` | mittel |
| **S5** | View/URL-Guards für F3 (Federated Learning) | `api/federated_urls.py`, `api/federated_views.py`, `nir_web/urls.py` (`FederatedLearningView`), `templates/federated.html`, `settings.py` (`FLOWERAI_ENABLED` koppeln) | mittel |
| **S6** | Service/Agenten-Guards (Defense in Depth) | `services/ilias_*.py`, `services/sensor_catalog.py`, `services/sensor_documents.py`, `services/federated_*.py`, `agents/ilias_*.py`, `agents/sensor_agent.py`, `agents/flower_agent.py` | mittel |
| **S7** | Docker: Profile für ilias/flower + Env in `django_app` | `docker-compose.yml`, `.env.example` | klein |
| **S8** | Tests: neue Test-Matrix OP95 (Flags, Guards, Teaser, Edition open vs. pro) | `tests/test_op95_edition_split.py` (neu) | mittel |
| **S9** | Doku: README/Open-Source-Hinweis, `.env.example`, Lizenz-Hinweis (MIT), Update `TASK.md`/`REPOSITORY_ALIGNMENT_AND_ROADMAP.md` | `README.md`, `NIR_Intelligence-main/README.md`, `.env.example`, `TASK.md`, Roadmap | klein |
| **S10** | Artikel-Konsistenz prüfen (siehe §6) | `ARTICLE_UPDATE_PUBLIC_SECTOR.md`, `ARTICLE_FINAL_VERSION_MARKED.md` | klein |

**Gesamtaufwand:** ca. 1–2 Arbeitstage (Fokus S1–S8; Doku parallel).

---

## 6. Artikel-Konsistenz (PR #242 ↔ Software-Teilung)

Der Artikel (PR #242) beschreibt:

- **Sensor-Datenbank (§3.2)** als Plattform-Bestandteil
- **Standardisierte Testeinheit (§6.7)** als Plattform-Bestandteil

**Konflikt:** F2 (Sensor-Datenbank-Oberfläche) soll in Teil 1 nur ein Link
sein — der Artikel beschreibt sie aber als Bestandteil.

**Lösung (Vorschlag):**
1. **Referenz-Protokoll-Vertrag / standardisierte Testeinheit** bleibt
   vollständig in Teil 1 (Grundfunktionalität) — kein Konflikt.
2. **Sensor-Datenbank:** Der Artikel beschreibt die *Fähigkeit* der
   Plattform (Adapter-Registry, Nutzungsstatistiken, Informationsseiten).
   In Teil 1 ist die **Oberfläche** (Sensor-Seiten) ein Teaser-Link.
   **Artikel-Formulierung anpassen (kleiner Zusatz in §3.2):** „In der
   Open-Source-Edition ist die Sensor-Datenbank-Oberfläche als Vorschau
   verfügbar; die vollständige Datenbank mit Dokumentenverwaltung und
   KI-Zusammenfassung ist Bestandteil der proprietären Variante." —
   ehrlich, kein Widerspruch.
3. **Lernplattform & Federated Learning:** Der Artikel erwähnt F1/F3 in
   §6.7 (Föderation) und §3 (Intro-Seite optional). Ebenfalls kurzer
   Edition-Hinweis nötig.

---

## 7. Offene Entscheidungen (für den Gründer)

1. **Startup-URL:** Welche URL soll die Teaser-Links in Teil 1 verwenden?
   (Platzhalter `NIR_IP_STARTUP_URL`, konfigurierbar via `.env`)
2. **Lizenz Teil 1:** MIT vorgeschlagen — finale Wahl?
3. **Selektive Freischaltung:** Sollen die drei Funktionen in Teil 2
   einzeln lizenzierbar sein (z. B. Sensor-DB als eigenes Modul), oder nur
   als Paket? (Plan unterstützt beides über Einzelflags)
4. **Graubereich Sensor-Quality-Agent:** Datensatz-Level-QA (Teil 1) vs.
   Sensor-Katalog (Teil 2) — Zustimmung zum Vorschlag in §3?
5. **Repository:** Teil 2 als privates Repo (Submodule/Subtree) — OK?
6. **Name/Branding:** Wie heißen die beiden Varianten offiziell?

---

## 8. Risiken & Gegenmaßnahmen

| Risiko | Gegenmaßnahme |
|---|---|
| „Nur Links" wird als gebrochene Funktion wahrgenommen | Teaser-Template klar beschriftet („verfügbar in der Startup-Variante"), honest by design |
| Feature-Flag vergessen an einer Stelle → Funktion doch erreichbar | Defense in Depth (3 Ebenen) + Test-Matrix OP95 prüft **jede** Route |
| GPL-Komponente (ILIAS) in proprietärer Variante | ILIAS bleibt externer Docker-Dienst (kein Code-Einbinden); Lizenz-Prüfung in Teil 2 dokumentieren |
| Artikel widerspricht Software | §6 — Artikel-Konsistenz als eigener Schritt S10 |
| Open-Source-Community baut Funktionen nach | Akzeptiert (permissive Lizenz); proprietäre Variante differenziert durch Integration, Support, selektive Freischaltung |

---

## 9. Nächster Schritt nach Freigabe

1. Offene Entscheidungen (§7) klären
2. Umsetzung S1–S10 auf neuem Branch `vibe/op95-software-split-f7b35d`
3. Test-Matrix OP95 grün + Regression (OP29/OP49/OP53/OP68 + FL/S8-Testreihen)
4. Draft-PR + Artikel-Konsistenz-Update
