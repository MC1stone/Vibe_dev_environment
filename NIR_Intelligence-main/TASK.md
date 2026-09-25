# NIR Intelligence Platform - Task Definition

## Overview
This document defines the current task for the NIR Intelligence Platform development.

## Current Task: OP37 - Dokumentierte Ausreisser-Analyse + KI-first Chatbot

### Objective
Zwei Befunde aus dem aktuellen Oel-Projekt-Report: (1) Die Spektren-
Darstellung zeigt keine Ausreisser-Analyse - Abweichler werden weder
erkannt noch dokumentiert. (2) Der Chatbot ist sehr eingeschraenkt: er
matcht nur statische Stichwoerter gegen ~10 Eintraege statt die lokale
KI (Ollama/Mistral) zu nutzen, die laut Vorgabe immer mit Prioritaet
laufen soll.

### Scope
- `services/outlier_analysis.py` (NEU): robuste, deterministische
  Ausreisser-Erkennung ueber alle Messungen (SNV-Normalisierung +
  robuster z-Score/MAD gegen das Median-Spektrum, Schwelle |z| = 3.5),
  ehrliches 'nicht bewertbar'-Verdict bei < 5 Messungen; zwei Charts
  (Abstands-Plot mit Schwelle, Spektrum-Overlay mit rot markierten
  Ausreissern) + deutsche Befundtexte - nichts wird erfunden
- `services/project_crew.py`: `_outlier_section()` - eigene Berichts-
  Sektion 'Ausreisser-Analyse' mit Charts, Zahlen und Befunden
- `services/project_report.py`: Chart-Titel + 'Befunde'-Absatz in der
  Agenten-Sektion (Charts + Textdokumentation)
- `services/student_report.py`: Ausreisser-Befunde in der Diskussion
  (Fehlerquellen) dokumentiert
- `agents/chatbot_agent.py`: KB-Kategorie 'Ausreisser' mit konkreten
  Zahlen + Abbildungs-Links
- `services/report_chatbot.py`: KI-first - jede Frage geht zuerst an
  /api/chatbot/message/ (Ollama/Mistral, RAG-Kontext aus den echten
  Berichtsfakten, bis zu 6 Turns History, 'KI denkt'-Zustand);
  Keyword-KB nur noch klar gekennzeichneter Offline-Fallback
  (jetzt Top-2-Treffer statt Einzelmatch)
- `tests/test_op37_outlier_chatbot.py` (24 Checks) + CI-Zeile;
  OP24-Matrix an das neue KI-first-Vertrag angepasst (lokaler Endpoint
  erlaubt, externe URLs weiterhin verboten)

### Success Criteria
- Ausreisser werden statistisch erkannt (SNV + MAD), visualisiert
  (2 Charts) und im Report, in der Diskussion und im Chatbot
  dokumentiert
- Zu wenige Messungen -> ehrliches 'nicht bewertbar', keine Erfindung
- Chatbot nutzt die lokale KI mit Berichts-Kontext und History;
  offline faellt er auf die KB zurueck (gekennzeichnet)
- Alle Matrizen bleiben gruen

## Completed Task: OP36 - Zielwert-Agnostizismus ueber die gesamte Kette

### Objective
Nicht jede Kalibration misst Brix - Oel-Projekte kalibrieren z. B. auf
Fett- oder Wassergehalt. Die Plattform muss zielwert-agnostisch sein:
Der Zielwert (Kalibrationsziel) wird aus den Daten/Metadaten abgeleitet
und nur angefragt, wenn kein Rueckschluss moeglich ist (nie Brix
hartkodiert, nichts geraten - Anti-Halluzination).

### Scope
- `services/project_ingest.py`:
  - Wide-Ingest zeichnet die gewaehlte Referenzspalte als
    `target_name` in den Dataset-Metadaten auf
  - `_ki_forward_questions()`: neues Thema 'zielwert' - fragt genau
    dann, wenn weder `target_name` noch `reference_values` vorliegen
    (eindeutige Eskalation, thematische Dedup, Editor-Feld genannt)
- `services/calibration_charts.py`: `calibration_chart_data_urls(...,
  target_name)` - Ref-vs-Pred- und RMSECV-Labels tragen den Zielwert
- `services/xai_charts.py`: `xai_chart_data_urls(..., target_name)` -
  Prediction-vs-Actual-Labels tragen den Zielwert
- `services/project_crew.py`: reicht `target_name` aus den
  Dataset-Metadaten an beide Chart-Builder durch
- `services/student_report.py`: `_dataset_target_name()` - Analyt und
  RMSE-Einheiten kommen aus `target_name` (neutraler Fallback
  'Zieleinheit'/'Zielwert'), Brix-Formulierungen entfernt
- `agents/chatbot_agent.py`: RMSE-Antworten nutzen den Zielwert aus dem
  Dataset-Kontext (Fallback 'Zieleinheit'), PLS-Glossar neutral
- `tests/test_op36_target_agnostic.py` (25 Checks) + CI-Zeile;
  OP23/OP33-Matrizen an das zielwert-agnostische Verhalten angepasst

### Success Criteria
- Beliebige Referenzspalte (nicht nur Brix) wird als Zielwert
  aufgezeichnet und in Charts/Berichten/Chatbot benutzt
- Keine Zielwert-Frage, wenn die Daten den Zielwert hergeben
- Zielwert-Frage mit klarer Eskalation, wenn nichts ableitbar ist
- Keine Brix-Hardcodes mehr im Plattform-Quellcode
- Alle Matrizen bleiben gruen

## Completed Task: OP35 - KI-Felder im Editor bereitstellen + Metadaten-Uebersicht im Abschlussbericht

### Objective
Nach OP34 zwei Restpunkte: (1) Die von der KI angefragten Felder
(instrument_model, serial_number, integration_time) sollen bereitstehen,
sobald der Editiermodus geoeffnet wird - die Antwort direkt ins angebotene
Feld tippen statt Feldnamen zu suchen. (2) Eine Metadaten-Uebersicht
gehoert in den Abschlussbericht, damit dokumentiert ist, worauf die
Analyse beruht.

### Scope
- `django_project/api/project_views.py` `_metadata_editor_fields`:
  KI-angefragte Felder werden aus den open_questions geparsest
  ('Fehlende Felder: ...') und als leere Eingaben angeboten; Alias-Felder
  greifen auf den kanonischen Zwilling zurueck (operator zeigt
  operator_name-Wert, wenn nur dieser existiert)
- `services/project_report.py` `_metadata_overview_html` (NEU):
  Abschlussbericht-Sektion 'Metadaten-Uebersicht' - je Datensatz
  Feld/Wert/Quelle mit Badges (ki berechnet / projekt-kontext / Datei),
  Standards-Konformitaet, offene KI-Fragen, KI-Gesamteinschaetzung
- `tests/test_op35_metadata_editor_report.py` (13 Checks) + CI-Zeile

### Success Criteria
- Editiermodus zeigt alle KI-angefragten Felder als leere Inputs
- Bestehende Werte bleiben prefilled (auch Alias-Rueckgriff)
- Abschlussbericht dokumentiert Metadaten, Quellen, Standards, offene Fragen
- Leere Daten -> keine Sektion (ehrlich, nichts erfunden)
- Alle Matrizen bleiben gruen



### Objective
Der OP32-Report listete wavelength_range, resolution, integration_time und
instrument_model als fehlend - aber ausser der Integrationszeit kann alles
aus den geladenen Daten berechnet werden. Der Nutzer erwartet: Die KI
analysiert die Daten, leitet die Werte ab (predict/suggest), exposes sie
im Report und fragt nur fuer Nicht-Ableitbares explizit nach.

### Scope
- `services/project_ingest.py`:
  - `_derived_metadata_pass()`: wavelength_range + resolution aus der
    eigenen Wellenlaengenachse (num_points/Spanne), scan_count aus der
    Messanzahl des Wide-Exports - Quelle 'ki (aus Daten berechnet)';
    nie ueberschreibend, nur fuellend; nur fuer usable Datasets
  - `_ki_forward_questions()`: fuer nicht ableitbare Standard-Felder
    (integration_time, instrument_model) fragt die KI den Nutzer
    explizit (Ollama-Formulierung, offline deterministische
    Template-Frage), mit Standard-Bezug und Dedup
  - Integration in alle Ingest-Pfade + build_preparation_report
    (Assessment laeuft nach den Forward-Fragen erneut)
- `django_project/templates/project_report.html`: Badge fuer
  berechnete Quellen ('ki (aus Daten berechnet)')
- `tests/test_op33_derived_metadata.py` (17 Checks) + CI-Erweiterung

### Out of Scope
- Formatspezifische Header-Extraktion fuer binaere Formate (HDF5 attrs,
  SPC/MAT-Header, JDX, EXIF) - folgt
- Quarto-Report-Sektion 'metadata_evaluation' - folgt

### Success Criteria
- wavelength_range/resolution/scan_count werden aus den Daten berechnet
  und mit Quellen-Badge im Report angezeigt (nicht mehr 'fehlend')
- OP34-Nacharbeit: KI-Fragen werden THEMATISCH konsolidiert (eine Frage
  pro Thema: Sensor = Name/Typ + Modell + Seriennummer zusammen,
  Messparameter = Integrationszeit), bekannte Werte werden in der Frage
  genannt; Metadaten-Accordion im Report standardmaessig aufgeklappt
  (Werte sichtbar, nicht nur Bewertung); Beschreibungs-Metadaten
  propagieren als Projekt-Kontext auf die Mess-Datensaetze
  (Quelle 'projekt-kontext', nie ueberschreibend)
- ASTM_E1655-Konformitaet steigt durch die abgeleiteten Felder
- Nicht ableitbare Felder werden ueber KI-Fragen eskaliert (nie geraten)
- Vorhandene Werte werden nie ueberschrieben
- Offline: Template-Frage bleibt, nichts wird erfunden
- Alle existierenden Matrizen bleiben gruen

## Completed Task: OP32 - Standards-Based Metadata Display and KI Relevance Recommendations

### Objective
Der OP31-Report zeigte zwei vom Nutzer bestaetigte Schwaechen: (1) Die
vorhandenen Metadaten wurden im Report nicht brauchbar angezeigt - Alias-
Spiegel (operator/operator_name) erschienen doppelt, und (2) die
Empfehlungen waren wertloser High-Level-Prozentsatz statt konkreter,
standardsbezogener Aussagen. Der Nutzer erwartet: Die KI filtert, WELCHE
Metadaten in den Standards (ASTM E1655, ISO 12099, EURACHEM,
NIR_PUBLIC_DATABASE) stecken und welche dafuer - und vor allem fuer die
NIR-Spektroskopie - interessant sind.

### Scope
- `services/metadata_llm.py`: `MetadataRelevanceService` (NEU) - KI-first
  NIR-Relevanz-Bewertung mit Guard: nur Feldnamen aus den tatsaechlichen
  present/missing-Listen, nur bekannte Standards; erfundene Felder/Normen
  werden verworfen (nie angezeigt)
- `services/project_ingest.py`:
  - `_metadata_standards()` + `_standards_compliance()`: per-Standard
    present/missing/satisfied-Verdict (deterministisch, single source of
    truth = loader METADATA_STANDARDS)
  - `_ki_relevance_pass()`: Mistral bewertet Relevanz + priorisiert
    fehlende Felder mit Begruendung und Standard-Bezug
  - `_assess_metadata()`: Alias-Spiegel raus aus dem Rating (Information
    einmal anzeigen, unter dem kanonischen Namen)
  - `_recommendations()`: konkrete Empfehlungen mit Standard-Bezug und
    KI-Begruendung statt prozentualer High-Level-Aussage
- `django_project/templates/project_report.html`: Standards-Konformitaets-
  Tabelle (Standard/Vorhanden/Fehlt/Status) + KI-Einschaetzungs-Alert
- `tests/test_op32_metadata_relevance.py` (19 Checks) + CI-Erweiterung

### Out of Scope
- Formatspezifische Header-Extraktion fuer binaere Formate (HDF5 attrs,
  SPC/MAT-Header, JDX, EXIF) - folgt
- Quarto-Report-Sektion 'metadata_evaluation' - folgt

### Success Criteria
- Metadaten werden dedupliziert im Report angezeigt (keine Alias-Doppel)
- Standards-Konformitaet je Norm sichtbar (was fehlt fuer welchen Standard)
- Empfehlungen nennen das Feld, den Standard und die KI-Begruendung
- KI-Guard: erfundene Felder/Normen erscheinen nie im Report
- Offline: deterministische Standards-Bewertung bleibt, nichts erfunden
- Alle existierenden Matrizen bleiben gruen

## Completed Task: OP31 - KI-First Metadata Extraction (Ollama/Mistral, Anti-Halluzination, Nutzer-Eskalation)

### Objective
Die Metadaten-Erhebung war rein regelbasiert (regex) und die KI lieferte
keinen Beitrag, obwohl Ollama mit Mistral lokal immer verfuegbar ist.
Zusaetzlich gab es zwei uneinheitliche Rating-Systeme und die Metadaten
fehlten im Projektbericht. Der Nutzer erwartet: KI liest Metadaten aus
allen Dateiformaten (auch aus Headern/Prosa), mit Prioritaet, ein Rating
ueber die Qualitaet, Anzeige im Reporting nach der Struktur, die die KI
nutzt - und strikt ohne Halluzination: Bei Fragen oder Konflikten muss
die KI ueber den Chatbot auf das Problem hinweisen und explizit nach
einer Loesung fragen, statt stillschweigend zu entscheiden.

### Scope
- `services/metadata_llm.py` (NEU): `OllamaMetadataClient` (Ollama
  /api/chat, format=json, is_available()), `MetadataLLMService` mit
  injizierbarem Client, `_verbatim()`-Guard + `_canonical_field_name()`
- Anti-Halluzination IN CODE, nicht per Prompt-Vertrauen: jeder LLM-Wert
  muss wortwoertlich im Quelltext stehen, sonst Verwerfung; unbekannte
  Feldnamen werden verworfen (nur CANONICAL_FIELDS + Alias-Folding)
- `services/project_ingest.py`: `_ki_metadata_pass` (KI-first auf allen
  drei Ingest-Pfaden), `_file_text_for_llm`, `_make_loader`,
  feldgenaues Rating (`metadata_rating` mit Quelle/Bewertung je Feld,
  `konflikte`-Liste), Empfehlungen fuer offene Fragen
- `agents/chatbot_agent.py`: Kategorie 'KI-Metadaten' - jede offene Frage
  wird zum KB-Eintrag mit expliziter Aufforderung an den Nutzer
- `django_project/templates/project_report.html`: Warning-Alert fuer
  offene KI-Fragen + Accordion 'Erhobene Metadaten je Datensatz'
  (Feld/Wert/Quelle/Bewertung, KI-Badge, Konflikt-Badge)
- `tests/test_op31_metadata_llm.py` (25 Checks) + CI-Matrix-Erweiterung

### Out of Scope
- Formatspezifische Header-Extraktion fuer binaere Formate (HDF5 attrs,
  SPC/MAT-Header, JDX-'##', EXIF) - Folge-Schritt
- Die Quarto-Report-Sektion 'metadata_evaluation' (task_definition.yaml)
- Messwerte-Loading bleibt deterministisch (nur Metadaten sind KI-first)

### Success Criteria
- Mistral ist der PRIMAERE Metadaten-Extraktor (KI-first), deterministisch
  nur noch Validierung/Absicherung; Messwerte-Loading unveraendert
- Kein Halluzinieren: Verbatim-Guard im Code, erfundene Werte/Felder
  werden verworfen und dokumentiert (llm_rejected_values)
- Konflikte werden NIE still aufgeloest: Hard fact gewinnt, Konflikt
  landet in open_questions -> Empfehlung + Chatbot + Report-Alert
- Offline-Resilienz: ohne Ollama ueberlebt die deterministische
  Extraktion, nichts wird erfunden, nichts geht verloren
- Metadaten-Rating je Feld im Projektbericht sichtbar (Struktur der KI)
- Alle existierenden Test-Matrizen bleiben gruen (keine Regressionen)

## Completed Task: OP30 - Archive Ingest (ZIP as Container, not Spectrum File)

### Objective
The user's oil experiment arrived as one ZIP bundling a prose description
(Oel_Meta.txt) and two wide-format measurement matrices (OEL-MK_Train(1).csv,
OEL_MK_Test.csv). The project ingest treated the archive as a single
spectrum file: the content-driven loader picked ONE inner file (the test
matrix) and garbled its 'Probe'/'Brix' columns into a fake wavelength axis,
so the preparation report ended with 'No finite wavelength/intensity rows',
the description was lost and every other inner file was silently dropped.

### Scope
- `services/project_ingest.py`:
  - `_ingest_single_file`: shared ingest path (wide format -> two-column
    loader -> metadata source) for direct files and archive members; the
    OP28 alias sync now runs on the actual metadata dict (was a no-op
    before the entry's metadata was set)
  - `_archive_entries` + `_extract_archive_members`: an archive yields one
    dataset per inner file, extracted into a fresh unique directory (the
    loader's shared scan directory would mix same-named uploads); inner
    datasets carry the id '<archive-file-id>:<inner-name>' and their
    archive origin, size guard and candidate cap follow the loader contract
  - `build_preparation_report` flattens the entries and applies the OP13
    metadata overrides per inner dataset id
- `django_project/api/project_views.py`: ProjectMetadataView accepts inner
  archive dataset ids (validated against the stored preparation report)
- `tests/test_op30_archive_ingest.py` (19 checks) + CI matrix extension

### Out of Scope
- The S3 loader's archive scan (used for single-file spectral loads)
- Upload/storage layer changes (the ZIP stays one stored project file)
- The crew analysis of multiple datasets (unchanged: one run per dataset)

### Success Criteria
- The oil ZIP ingests as 3 usable datasets: train + test wide-format
  measurements with the real channel axis and the description as a
  metadata source (operator=Yvonne, instrument=Triadsensor)
- No inner file is lost and no fake wavelength axis is produced
- Metadata overrides work for inner datasets in the online editor
- Broken inner files are reported honestly, not fatal
- All existing test matrices stay green (no regressions)

## Completed Task: OP29 - Sensor Agent (Sensor Knowledge, Settings, Optimization)


### Objective

The platform knows its spectrometers only implicitly - adapter registry,
parameter recommender and scattered metadata - but there is no single place
that collects all sensor information used in the analyses. OP29 adds a
sensor agent and catalog: registered adapters with capabilities, setting
options and their ranges, usage statistics from the EXISTING database
(SpectrumRecord.instrument_type + project preparation reports; no new
tables), an informative /sensors/ sub-area of the web app, an assessment of
the settings recorded in measurements (completeness + plausibility, honest
about missing values) and deduplicated optimization suggestions from the
platform's three existing recommendation sources.

### Scope

- `services/sensor_catalog.py`: sensor catalog service
  - adapter profiles from the device registry (generic pkgutil scan - new
    adapter modules are picked up automatically, no hardcoded list)
  - instrument attribution: exact MODEL_ID match plus keyword aliases
    ('SparkFun NIR Triad' -> sparkfun_triad); unknown instruments stay
    unmatched (honest, no invented mapping)
  - setting options: canonical OP28 setting fields merged with the
    ParameterRecommenderAgent parameter catalogue (ranges, defaults);
    'scans_to_average' mapped onto the canonical 'scan_count'
  - usage statistics from the existing tables only (no new model/migration):
    spectra count, projects, last use, recorded setting values, samples
  - `assess_settings`: completeness + plausibility of recorded values
    (min/max checks); missing parameters reported, never invented
  - `merge_recommendations` / `get_optimization_suggestions`: the three
    existing sources (analytical parameter recommendations, data-preparation
    heuristics, generic OP21 sensor-quality texts) deduplicated per
    parameter with priority analytical > heuristic > generic; conflicting
    values are kept with both rationales (truthfulness), agreeing sources
    are recorded
- `agents/sensor_agent.py`: SensorAgent (operations 'collect' and 'usage')
- `services/project_crew.py`: the sensor-quality report section now embeds
  the deduplicated optimization suggestions and the setting assessment of
  the dataset metadata; `agents/nir_analysis_crew.py` carries the spectral
  agent's parameter_recommendations on the AnalysisResult so the merge has
  the real analytical source
- `django_project/api/project_views.py` + `project_urls.py`:
  SensorListView (/projects/sensors/) and SensorDetailView
  (/projects/sensors/<key>/) - adapter profiles, setting options, usage,
  per-sensor assessment and suggestions
- Templates `sensor_list.html`, `sensor_detail.html` + navigation entry
- `tests/test_op29_sensor_agent.py` (53 checks) + CI matrix extended

### Out of Scope

- New database tables (explicit user constraint: use the existing database)
- Device driver changes (the adapters stay as they are)
- Remote device control / live acquisition (catalog only)

### Success Criteria

- All registered adapters are discovered and profiled with capabilities
- Setting options with ranges from the recommender are listed and assessed
  (completeness + plausibility) against recorded measurement metadata
- Usage (spectra, projects, settings, samples) is read from the existing
  database without a new migration
- Optimization suggestions from analyses are deduplicated per parameter;
  conflicts are shown, not silently overwritten
- /sensors/ pages render (list + detail) and are linked in the navigation
- All existing test matrices stay green (no regressions)

## Completed Task: OP28 - File-Type Agnostic Data Loading (MO 1)

### Objective

MO 1 requires raw data import independent of the file format, but the
platform still rejected files by extension at three levels: the Django
spectrum upload accepted only .txt/.csv/.json/.h5/.hdf5 (HTTP 400 for
everything else), the data-preparation loader hard-dispatched seven
extensions and logged 'Unsupported spectral file format' for anything
else (even .hdf5 had no loader), and the MCP ingest required a single
wavelength/intensity column pair, so wide measurement matrices were not
ingestable. OP28 removes all extension gates and makes the search for
measurement values and metadata content-driven.

### Scope

- `agents/data_preparation_agent.py`: `_load_spectral_data` never rejects
  a file - the extension picks a dedicated fast-path parser (.hdf5 alias
  and YAML/XML/Excel/Parquet/Feather added), and any file (unknown or no
  extension, failed fast path) goes through the new content-driven chain
  `_load_content_driven`: archive -> HDF5 -> SPC/MAT binary magic -> Excel
  -> Parquet/Feather -> JSON -> YAML/XML -> generic table parse -> line-
  filtered extraction -> raw number extraction. Metadata is searched in
  every text file (`_extract_text_metadata`: comment lines, 'Key: Value',
  'Key = Value'; aliases map to the canonical platform fields). Batch
  discovery and `_get_file_type` no longer skip unknown files (UNKNOWN
  instead of None).
- `agents/mcp_agent.py`: `_ingest` detects wide measurement matrices
  (channel columns '<prefix>_<wavelength>', same rule as the ingest
  service) BEFORE pair extraction, validates candidate wavelength axes
  (ascending, >10 nm span) so reference values (Brix) are never misread
  as wavelengths, scans all column pairs when the named pair yields
  nothing, and reports the matrix layout honestly.
- `services/mcp_data_server.py`: ingest tool description updated (any
  format, content inspection)
- `django_project/api/views.py`: upload whitelist removed (every file
  type accepted); `_parse_spectrum_file` uses the content-driven loader
  instead of the '#'-header-only TXT reader
- `django_project/templates/analysis.html`, `spectra.html`,
  `static/js/analysis.js`: accept-restrictions and file-type hints removed
- `tests/test_op28_file_type_agnostic.py` (23 checks) + CI matrix extended

### Out of Scope

- Binary image/audio parsing beyond the existing agents (no measurements
  in PNG/JPG/WAV/MP3 for the spectral pipeline)
- The legacy `generic_file_handler_agent.py` (orthogonal metadata
  extraction; untouched)

### Success Criteria

- Every file type is accepted at upload; no extension whitelist remains
- Measurements and metadata are found in known, unknown and extensionless
  files (XLSX, Parquet, Feather, YAML, XML, ZIP, .dat, no extension)
- A file with no extractable measurements returns an honest error/None,
  never invented values
- All existing test matrices stay green (no regressions)

## Completed Task: OP27 - .deb Package and systemd Service

### Objective
The OP26 ansible playbook expects `nir_intelligence_main.deb` (or a tar.gz
with install.sh) on the ventoy stick - this OP provides the packaging so
that artifact actually exists and installs a running, service-managed
platform on Debian 13.

### Scope
- `packaging/DEBIAN/control` + `postinst`: dpkg metadata; postinst creates
  the system user `nir`, builds the venv, installs requirements (tolerant -
  optional heavy deps like TensorFlow degrade gracefully per the OP14/18
  truthfulness design), migrates the SQLite database and enables/restarts
  the systemd service
- `packaging/nir_intelligence.service`: systemd unit - web UI via
  `manage.py runserver 127.0.0.1:8000` as user nir, restart on failure
- `packaging/install.sh`: archive-method installer (same steps as postinst,
  root check, .install_completed marker as the OP26 idempotency guard)
- `packaging/build_deb.sh`: stages the repo payload (django_project, agents,
  services, config, templates, docs) into /opt/nir_intelligence, strips
  caches/dev DB, sets the version and builds dist/nir_intelligence_main.deb
  with dpkg-deb
- `tests/test_op27_deb_package.py`: builds the real .deb + tar.gz and
  verifies structure, metadata, service contract and OP26 expectations

### Out of Scope
- Installing/unpacking the package on a real target (needs a Debian machine)
- Production web server (gunicorn/nginx) - the platform runs on the Django
  development server on loopback, matching the local-first design

### Success Criteria
- `packaging/build_deb.sh` produces a valid nir_intelligence_main.deb
- Package payload, postinst, unit and install.sh match the OP26 playbook
  expectations (paths /opt/nir_intelligence, install.sh, service name)
- All existing test matrices stay green (no regressions)

## Completed Task: OP26 - Ansible Install Playbook for Debian 13

### Objective
The platform should be installable on a blank Debian 13 (x86_64) machine
from a Ventoy stick with a single Ansible run. Two methods are supported:
the packaged app as a .deb (preferred) or as a tar.gz archive with an
install.sh script (fallback).

### Scope
- `ansible/install_nir_intelligence.yml`: the playbook - ventoy mount and
  source presence checks (clean abort before any change), apt update,
  dependency install (python3, wget, git, unzip), .deb method (copy to /tmp,
  apt install) or archive method (copy to /opt, unarchive to
  /opt/nir_intelligence, run install.sh as root), systemd service
  nir_intelligence enabled/started (if present), verification via service
  status; all paths and names as vars; block/rescue error handling;
  idempotent (creates-guards, state: present)
- `ansible/INSTALL_NIR_INTELLIGENCE.md`: short run guide (prerequisites,
  ansible-playbook command, variables table, error handling, idempotency)
- `tests/test_op26_ansible_install.py` (structural matrix) + CI line

### Out of Scope
- Building the .deb package itself (separate OP)
- Running the playbook against a real Debian 13 target (target machine)

### Success Criteria
- Playbook is valid YAML with all required tasks, error handling and
  idempotency guards
- Guide documents execution after the Debian installation
- All existing test matrices stay green (no regressions)

## Completed Task: OP25 - Website Cleanup and Workflow Overview

### Objective
The website accumulated many legacy demo pages (dashboard, agents, spectra,
files, analysis, jobs, settings, documentation, chatbot, ilias) that are not
part of the implemented project workflow. OP25 cleans the navigation down to
the real workflow (start page -> projects -> spectral database), rebuilds the
start page as a workflow overview diagram, and explains each workflow step on
mouse-over.

### Scope
- `django_project/templates/base.html`: navbar reduced to Workflow
  (start page), Projekte, Spektrendatenbank + Login/Logout/Register; settings
  entry removed from the user dropdown; footer reduced to the workflow links
- `django_project/templates/index.html`: new start page with a numbered
  workflow diagram (Login/Registrierung -> Projekt anlegen (Upload) ->
  Metadaten bearbeiten -> Dateien erganzen (Bearbeiten) -> Release
  (Agenten-Analyse) -> Abschlussbericht -> Spektrendatenbank); each step
  card carries a German hover/focus tooltip that references the real pages
  and buttons; workflow CTAs instead of the legacy quick-nav
- `django_project/templates/login.html`: dead /password-reset/ link removed
- Legacy routes and templates stay functional but unlinked (test_op7 and
  test_op8 still depend on files.html / analysis.html)
- `tests/test_op8_crew_results_ui.py`: T7 navigation checks adapted to the
  OP25 navigation (files.html stays functional, workflow links verified)
- `django_project/templates/index.html`: workflow diagram centered - two
  centered rows (4 + 3 steps) with a wrap arrow, max-width 900px
- `services/project_report.py`: visible figure captions - every chart in the
  final report (overview + agent sections) carries "Abbildung N: <Titel>"
  with the SAME numbering as the OP23 Diskussion explanations and the OP24
  chatbot references (overview charts first, then agent sections in report
  order); `_figure_registry` + `_figure_caption` + `_CHART_TITLES`
- `tests/test_op25_website_cleanup.py` (65 checks) + CI matrix extended

### Out of Scope
- Deleting legacy templates/routes (kept unlinked for compatibility)
- New backend functionality

### Success Criteria
- Navbar and start page link only the implemented workflow targets
- Every workflow step has a German mouse-over explanation
- All existing test matrices stay green (no regressions)

## Completed Task: OP24 - Embedded Report Chatbot

### Objective

Students should be able to ask questions about the analysis directly in
the final report. The report is a self-contained offline HTML file, so a
live CrewAI chat would break the concept (server dependency, no offline
use). Hybrid design:

1. `ChatbotAgent` (CrewAI agent, `agents/chatbot_agent.py`) runs at
   release time with the REAL crew results and builds a structured Q&A
   knowledge base: categories (Projekt, Spektrum, Sensor, Statistik,
   Neuronales Netz, Kalibration, Datenbank, Optimierung, Warnungen,
   Methoden), anticipated student questions, answers carrying the real
   numbers (R2, RMSE, drift level, wavelength range, similarity scores),
   keyword matching sets and figure references (Abbildung numbers
   consistent with the OP23 explanations). Consistent with the OP14
   truthfulness rule: the agent only answers what the results contain.
2. Embedded chat widget (`services/report_chatbot.py`): vanilla-JS,
   fully offline client-side matching (umlaut-folded keyword scoring +
   question-text similarity), answer chips as suggested questions, jump
   links that scroll to and highlight the referenced figure, fallback
   answer when nothing matches. No server, no network, no external
   libraries.

### Scope

- `agents/chatbot_agent.py`: release-time knowledge base builder
- `services/report_chatbot.py`: widget template + payload embedding
- `services/project_report.py`: the final report gains the chatbot
  section between Literaturhinweise and Originaldaten

### Out of Scope

- Live LLM backend (a local Ollama endpoint would be a separate OP with
  infrastructure requirements)
- Multi-turn conversations (single-question matching by design)

### Success Criteria

- Knowledge base entries carry only real numbers from the crew results
- Widget works fully offline (no external URLs, no fetch)
- All existing test matrices stay green (no regressions)

## Completed Task: OP23 - Student-Friendly Report Sections (Diskussion, Fazit, Literatur)

### Objective

The final report listed per-agent results but was not written for students.
OP23 renders three sections from the REAL analysis results (no invented
findings, Fachbegriffe explained in plain language at first use):

- **Diskussion**: interpretation of the spectra (band assignment from the
  measured wavelength range), assessment of the model quality (R2, RMSE from
  the agent results with an honest RMSEP note), possible error sources
  (concrete agent findings + general NIR effects like Streulicht,
  inhomogeneous samples, temperature) and a detailed explanation of every
  figure (Abbildung 1..N in report order, each describing what the chart
  shows and how to read it)
- **Fazit**: summary of the key findings (overall score, best R2, completed
  sections) and every optimization option collected from all agents, each
  with a short explanation of the underlying effect
- **Literaturhinweise**: real, accessible standard works cited in APA style
  (Pasquini 2003; Workman & Weyer 2012; Geladi & Kowalski 1986; Wold et al.
  2001; Williams & Norris 2001; N\u00e6s et al. 2002; Burns & Ciurczak 2007)

### Scope

- `services/student_report.py`: spectrum interpretation, model quality
  paragraphs, error sources, figure explanations, conclusion builder and
  the APA literature list; everything degrades honestly to 'no data'
  statements, never to invented findings
- `services/project_report.py`: the final report gains Diskussion, Fazit
  and Literaturhinweise between the agent sections and the original data

### Out of Scope

- Per-agent section text changes (the sections stay as they are)
- English report variant

### Success Criteria

- Every figure in the final report is explained (Abbildung 1..N, no gaps)
- Model quality text uses the real agent numbers, with an honest note that
  no independent RMSEP validation set exists
- All existing test matrices stay green (no regressions)

## Completed Task: OP22 - Spectrum Chart and Top-3 Similarity Comparison

### Objective

The uploaded spectral data was only ever shown as numbers: the spectral
analysis section had no plot of the measured spectrum, and the FAISS
similarity search reported scores without visualising the matches.
OP22 renders both:

| Chart | Content |
|-------|---------|
| Spectrum | The uploaded spectrum as a single line (same style as the database detail page) in the spectral analysis section |
| Similarity Top-3 | The measurement overlaid with the three most similar spectra (spectral database + sibling project files), matches ordered by FAISS similarity |

### Scope

- `services/similarity_charts.py`: spectrum line chart and top-3
  comparison overlay (base64 PNG data URLs, never raises, '' without
  data; the comparison returns '' when no reference curve can be drawn
  - never a fake overlay)
- `services/project_crew.py`: the spectral analysis section carries
  `charts`/`charts_note` with the uploaded spectrum; the similarity
  section builds the reference curve map (sibling datasets + database
  references) and overlays the top-3 matches on the measurement
- Templates and the final OP11 report render both charts through the
  generic section-charts loop (no template change needed)

### Out of Scope

- FAISS metric changes (the chart visualises the existing cosine search)
- Cross-grid interpolation (references on a different wavelength grid
  stay excluded, per the OP15 design rule)

### Success Criteria

- Both charts render from the real Triad preview (18 channels)
- The similarity section shows the three most similar spectra from
  database + sibling files with their similarity scores
- All existing test matrices stay green (no regressions)

## Completed Task: OP21 - Sensor Quality SPC Dashboard and Optimization Recommendations

### Objective

The old NIR platform showed the sensor quality as a nicely presented
panel with optimization recommendations. The new agent computes drift,
offset, noise and a quality score from the real replicas (OP14 fixed
the false alarms), but nothing was plotted and no recommendations were
shown. OP21 renders a 4-panel SPC-style dashboard from the real
measurement replicas and derives concrete German optimization
recommendations from the agent results:

| Panel | Type | Content |
|-------|------|---------|
| A | Control chart (Shewhart) | Drift trend over the replicas with a +/-3 sigma band |
| B | Spectral overlay (all curves) | Visual drift as a systematic shift |
| C | Noise per channel (box plot) | Which of the channels drive the noise? |
| D | Quality gauge (0-1) | Traffic-light overall score with sub-scores |

### Scope

- `services/sensor_charts.py`: 4-panel dashboard builder (base64 PNG data
  URL, never raises, empty dict without matplotlib, fewer than two
  replicas or no sensor results) plus `sensor_recommendations()` deriving
  concrete German optimization recommendations from the agent findings
  (drift -> warm-up/re-calibration, offset -> dark/white reference, noise
  -> averaging/longer integration, good -> keep control measurements)
- `services/project_crew.py`: the sensor section carries `charts` and
  `charts_note` (outside `data`) and injects the recommendations into the
  section data as `optimization_recommendations`
- Templates and the final OP11 report render the chart through the
  generic section-charts loop (no template change needed)

### Out of Scope

- Sensor agent metric changes (the dashboard visualises the OP14-fixed
  metrics as they are)
- Time-based SPC (the replicas carry no timestamps; the measurement
  order is the control axis)

### Success Criteria

- Dashboard renders from the real Triad replicas (18 channels) with the
  real sensor agent results
- Every agent finding maps to a concrete recommendation
- All existing test matrices stay green (no regressions)

## Completed Task: OP20 - Standard Calibration Plots

### Objective

A chemometric calibration is judged by three standard plots. The
 calibration agent computed cross-validated scores but nothing was
 plotted. OP20 renders these plots from the real calibration samples
 with scikit-learn PLS (no TensorFlow needed, CI-safe):

| Plot | Content |
|------|---------|
| Ref. vs. Pred | Reference vs. cross-validated predicted values (5-fold KFold, R2cv + RMSECV annotated) - how good is the calibration? |
| Regression Coefficients | Signed PLS coefficients per wavelength (why does it work? the sought-after plot) |
| RMSECV vs. n | RMSECV over the number of PLS components, minimum marked (how complex must the model be?) |

### Scope

- `services/calibration_charts.py`: PLS-based chart builder; base64 PNG
  data URLs, never raises, empty dict without matplotlib/scikit-learn or
  with insufficient calibration rows (<10 rows, constant target)
- `services/project_crew.py`: the calibration section carries `charts`
  and `charts_note` (outside `data`) whenever the dataset provides
  calibration samples and reference values
- Templates and the final OP11 report render the charts through the
  generic section-charts loop (no template change needed)

### Out of Scope

- Calibration agent context changes (the charts use the same ingest-side
  calibration data as OP18/OP19)
- Coefficient plots for non-PLS methods (SVM, RandomForest)

### Success Criteria

- All three plots render from the real Triad calibration data (200 rows,
  real Brix 4.3-8.1)
- Predictions are strictly cross-validated (out-of-sample), coefficients
  from a real PLS fit
- All existing test matrices stay green (no regressions)

## Completed Task: OP19 - XAI Visualisations for the Neural Network Analysis

### Objective

A neural calibrator on NIR spectra is interpreted through standard XAI
plots. OP18 fixed the CNN training; OP19 renders the seven standard XAI
visualisations from REAL computations on the trained attention-CNN:

| Plot | Content |
|------|---------|
| SHAP Summary (global) | Permutation importance (mean |dR2| per wavelength over the test set) |
| SHAP Force/Waterfall (lokal) | Occlusion deltas of one measurement, sorted by magnitude |
| Saliency Map | |d(output)/d(input)| gradient heatmap over the spectrum |
| Grad-CAM | Class activation over the last Conv1D layer (spatial-axis weights) |
| Attention-Weights | Learned softmax attention-pooling weights per wavelength |
| Prediction vs. Actual | Model fit on the test split (R2, RMSE) |
| Training/Validation Loss | Overfitting diagnosis per epoch |

The `shap` package stays a non-dependency (permutation importance and
occlusion are the SHAP-equivalents); nothing is simulated.

### Scope

- `services/xai_charts.py`: attention-CNN trainer (Conv1D stack + softmax
  attention pooling + dense regression head, scaled features/target) and
  seven plot renderers; base64 PNG data URLs, never raises, empty dict
  without TensorFlow/matplotlib or with insufficient calibration rows
- `services/project_crew.py`: the neural network section carries `charts`
  and `charts_note` (outside `data`) whenever the dataset provides
  calibration samples and reference values
- Templates and the final OP11 report render the charts through the
  generic section-charts loop (no template change needed)

### Out of Scope

- SHAP package integration (permutation/occlusion equivalents suffice)
- XAI plots for non-CNN models (MLP, PLS)

### Success Criteria

- All seven plots render from the real Triad calibration data (200 rows,
  real Brix 4.3-8.1) with TensorFlow installed
- Without TensorFlow: empty charts, report intact (CI-safe)
- All existing test matrices stay green (no regressions)

## Completed Task: OP18 - CNN Agent Fix and Supervised Calibration Pipeline

### Objective

The CNN agent never trained for two root causes:
1. The training code was broken for current Keras (deprecated input_shape
   argument), lacked feature scaling (raw ADC values against Brix ~5 stall
   the gradient descent) and recorded no loss history.
2. No reference values ever reached the supervised agents: the wide ingest
   kept Brix only as a column statistic, never per measurement - and the
   replica block is one object with a constant Brix, which cannot train a
   calibrator.

### Scope

- `agents/neural_network_agent.py`: `_train_cnn` rebuilt - Keras 3 Input
   layer, StandardScaler for features and target, validation split, loss +
   validation loss curves, RMSE, convergence flag from the real history;
  graceful deferred without TensorFlow, skipped without reference values
- `services/project_ingest.py`: calibration samples sampled across the
  whole wide file (one reference value per measured object, target column
  by name priority brix/sugar/reference first, index/counter-like columns
  skipped, saturated rows excluded, up to 200 rows); replicas stay for the
  sensor agent
- `agents/nir_analysis_crew.py`: supervised context (statistical + neural
  network agents) uses the calibration samples; the sensor agent keeps the
  replica context
- `requirements.txt`: CNN activation documented (tensorflow-cpu optional)

### Out of Scope

- XAI visualisations (SHAP, saliency, Grad-CAM etc.) - follow-up on top of
  the now-working CNN
- CNN architecture search (fixed sensible 1D-CNN)

### Success Criteria

- Triad file: 200 calibration samples with real Brix values (4.3-8.1)
- CNN trains end-to-end on the triad data with usable R2 and loss curve
  (with TensorFlow); deferred/skipped states reported honestly without it
- All existing test matrices stay green (no regressions)

## Completed Task: OP17 - Project Delete and File-Add Buttons on the Projects List

### Objective

The projects list had no way to remove a leftover project or to extend a
drafted project with further files. OP17 adds both actions to every
project row.

### Scope

- Delete button (every phase) with a Bootstrap confirmation dialog;
  `ProjectDeleteView` (POST `<uuid>/delete/`) enforces ownership via the
  same `_get_project` contract as all views (404 for other users)
- Edit button (drafted phase only): modal uploads further files via the
  existing `/api/files/upload/` and attaches them with
  `ProjectFilesAddView` (POST `<uuid>/files/add/`); the preparation
  report is rebuilt so the report page reflects the new files
  immediately; duplicate file ids are skipped and reported; released
  projects are frozen (400)

### Safety Contract

- Only the owner can delete or edit (404 for other users)
- Uploaded GenericFiles stay in the media store (may be shared by other
  projects)
- Persisted SpectrumRecords survive a deletion (SET_NULL on the project
  link) - the spectral database is not damaged

### Success Criteria

- Delete: project gone from list and DB, records keep their data
- Add files: file count and preparation report updated, duplicates
  skipped, released projects rejected
- `tests/test_op17_project_delete.py` (29 checks) + CI matrix extended
- All existing test matrices stay green (no regressions)

## Completed Task: OP16 - Standard PCA Visualisations

### Objective

The statistical agent computed PCA metrics (explained variance,
components), but a PCA in spectroscopy is judged by its standard plots.
OP16 renders the six standard PCA graphics from the measurement replicas
of a dataset and shows them in the statistical section of the project
report and the final OP11 report:

- Score-Plot (PC1 vs PC2): sample clustering, outlier detection
- Loading-Plot: which wavelengths drive each component
- Biplot: scores and loadings in one graphic
- Scree-Plot: eigenvalues -> choice of component count
- R2 per wavelength: which spectral regions the PCs explain
- SPE-Plot (squared prediction error): outliers / model fit

### Scope

- `services/pca_charts.py`: `pca_chart_data_urls()` - six matplotlib (Agg)
  plots as base64 PNG data URLs from measurement_samples + wavelengths,
  never raises, empty dict without matplotlib or without replicas
- `services/project_crew.py`: statistical section carries `charts` and
  `charts_note` outside `data` so the pprint block stays small
- `django_project/templates/project_report.html` +
  `services/project_report.py`: charts rendered in the project page and
  the final HTML report
- `tests/test_op16_pca_charts.py` (27 checks) + CI matrix extended

### Out of Scope

- Interactive plots (static PNGs only)
- PCA on the full 2049-measurement matrix (charts use the extracted
  replicas, capped at 25, same basis as the sensor agent)

### Success Criteria

- Triad file: all six plots rendered as base64 PNG from the replicas
- No replicas / single spectrum -> no charts, report stays intact
- Charts strictly JSON serializable (crew_results contract)
- All existing test matrices stay green (no regressions)

## Completed Task: OP15 - Persistent Spectral Database

### Objective

Released projects were compared only against their own sibling datasets -
spectra from earlier projects were lost after the run, so the FAISS
similarity section always started from an empty reference set. OP15
persists every usable dataset of a released project as a `SpectrumRecord`
so later projects can compare against the visible database records.

### Design Decisions

- Comparison metric: same wavelength grid only (grid key over rounded
  wavelengths) - no cross-grid interpolation, by design
- Visibility with federated learning in mind: user-private default,
  explicit per-record `lab_shared` opt-in. FL ground rule: raw spectra stay
  local, only parameter updates leave clients. Provenance fields
  (instrument_type, sample_type) double as non-IID sharding dimensions
  for the federated learning roadmap (S9 grouping)

### Scope

- `core/models.py`: `SpectrumRecord` (UUID, user, project, file_name,
  visibility, wavelengths/intensities/metadata JSON, wavelength_grid,
  instrument_type, sample_type, created_at) + migration 0006
- `services/spectrum_database.py`: `persist_project_spectra()` (idempotent
  per project+file_name, never raises), `visible_records()` (own +
  lab_shared), `references_for_dataset()` (same grid, unified FAISS schema)
- `services/project_crew.py`: similarity section appends visible database
  records to the FAISS reference set, `database_references` count
- `api/project_views.py` + templates: release persists spectra with the
  `spectrum_visibility` option, database list/detail pages with FAISS
  top-5 matches, projects page links the database, release offers the
  lab-sharing opt-in
- `tests/test_op15_spectral_database.py` (41 checks) + CI matrix extended

### Success Criteria

- Releasing a project persists its usable datasets; re-release updates
  instead of duplicating
- A new project finds visible same-grid records from earlier projects as
  FAISS references; cross-grid records are excluded, not interpolated
- Private records of other users stay invisible (enforced in query and
  detail view)
- All existing test matrices stay green (no regressions)

## Completed Task: OP14 - Truthful Agent Statements in the Project Report

### Objective

The report for the Dpark fun NIR Triad file (18 channels, 410-940 nm, 2049
measurements) contained wrong agent statements: the wide-format export went
through the two-column fallback loader (garbled wavelength axis), the spectral
agent called the valid VIS range 'outside expected range (700, 2500)', the
sensor agent derived noise 0.71 from the genuine channel shape, FAISS failed
with 'no usable intensity vector' despite 18 intensities (schema mismatch),
and the metadata agent complained about fields the platform itself knows.
OP14 fixes each statement at the root cause so the report describes the data
truthfully.

### Scope

- `services/project_ingest.py`: wide-format detection now survives preamble
  blank lines (skip_blank_lines=False + dropna), channel conversion without
  the thousands-separator heuristic, median per channel (robust against ADC
  overflow markers), replicate extraction from the longest same-object run,
  saturated-measurement count
- `agents/spectral_analysis_agent.py`: expected wavelength range is opt-in
  (None default) - spectrometer agnostic, no false VIS/NIR complaint
- `agents/sensor_quality_agent.py`: replica-based noise (std across
  measurements, not channel-shape differences), trend-based drift,
  no false offset against the replicates' own mean
- `agents/nir_analysis_crew.py`: known sample_id/instrument/acquisition_time
  aliases fed into the metadata assessment; measurement replicas passed to
  the sensor agent
- `services/project_crew.py`: FAISS query in the unified schema, skipped
  when the project has no other datasets; saturation warning surfaced in
  the crew result; timezone-aware timestamps
- `tests/test_op14_agent_truthfulness.py` (31 checks) + CI matrix extended

### Out of Scope

- Persistent spectral database comparison (OP15+, user explicitly deferred)
- Editing the agent thresholds per project (defaults stay)

### Success Criteria

- Triad file: 18 channels 410-940 nm, 2049 measurements, Brix 4.3-8.1 reported
- All seven agent sections complete; no false range/noise/FAISS statements
- Saturated measurements (ADC overflow) reported as their own warning
- Existing test matrices stay green (no regressions)

## Completed Task: OP13 - Online Metadata Editing in the Project Report

### Objective

The phase-1 report showed missing metadata fields with recommendations,
but the only adaptation path was editing files externally and re-uploading
them. OP13 adds the online path per MO 2-4: a metadata editor per dataset on
the project page (drafted phase only) - recommended fields prefilled from the
assessment, custom fields addable - the overrides are stored on the project
(metadata_overrides), the preparation report is rebuilt and the metadata
quality score updates immediately. No external file versions, no re-upload.

### Predecessors

- OP10: COMPLETED (project workflow)
- OP11: COMPLETED (rendered final report)
- OP12: COMPLETED (project creation UI)

### Scope

- `core/models.py`: `metadata_overrides` JSON field + migration 0005
- `services/project_ingest.py`: apply_metadata_overrides (empty values ignored,
  user-entered fields tracked for the report)
- `api/project_views.py` + `project_urls.py`: ProjectMetadataView (POST
  /projects/<id>/metadata/, drafted phase only, 409 after release)
- `templates/project_report.html`: per-dataset metadata editor (accordion,
  prefilled recommended fields, custom field add, inline status)
- `tests/test_op13_online_metadata_editing.py` (28 checks) + CI matrix extended

### Out of Scope

- Editing the measurement data itself (still re-upload, by design)
- Metadata editing after release (phase guard 409)

### Success Criteria

- Metadata editable online in the drafted phase; score updates immediately
- Overrides persisted on the project and visible in the rebuilt report
- Metadata editing rejected after release (409)
- Existing test matrices stay green (no regressions)

## Completed Task: OP12 - Project Creation UI on the Projects Page

### Objective

The projects page linked 'Dateien hochladen' to the legacy files page - files
were uploaded there but no project was created; the OP10 project workflow was
reachable only via the API. OP12 closes the UI gap per MO 1: the projects page
gets its own upload modal (multi-file, optional project name) that uploads
the files via /api/files/upload/, creates the project via
/api/projects/create/ with the returned file ids and navigates to the
preparation report (phase 1).

### Predecessors

- OP10: COMPLETED (project workflow, API)
- OP11: COMPLETED (rendered final report)

### Scope

- `django_project/templates/projects.html`: upload modal replaces the legacy
  /files/ link; upload -> create -> navigate flow with error paths
- `tests/test_op12_project_upload_ui.py` (19 checks) + CI matrix extended

### Out of Scope

- The legacy files page itself (stays as-is for single-file analysis)
- Inline metadata editing

### Success Criteria

- Upload on the projects page creates a project and lands on the preparation
  report without leaving the page flow
- Upload and project-creation error paths are visible to the user
- Existing test matrices stay green (no regressions)

## Completed Task: OP11 - Rendered Final Project Report (Charts, Original Data, Source Code)

### Objective

Replace the raw quarto-markdown project final report (found in the OP10 local
test: unrendered R fragments in a .html file, no charts) with a rendered,
self-contained HTML report: overview KPIs, embedded spectrum chart of the
full measurement series (matplotlib PNG as data URLs), per-agent quality bar
chart (evaluation), one section per agent (content + metrics + status),
original data tables, recommendations, warnings and the analysis source
code. The legacy reporting-agent template rendering stays as fallback;
matplotlib stays optional (charts degrade gracefully, anti-code-creep).

### Predecessors

- OP10: COMPLETED (project workflow upload -> preparation -> release -> crew)
- The local end-to-end test of OP10 exposed the raw-markdown final report

### Scope

- `services/project_report.py`: new OP11 report builder (rendered HTML with
  embedded charts, per-agent sections, original data, source code)
- `services/project_crew.py`: `_generate_final_report` uses the OP11 builder
  and passes the full measurement series; legacy template rendering kept
  as `_generate_final_report_legacy` fallback
- `tests/test_op11_rendered_final_report.py` (30 checks) + CI matrix extended

### Out of Scope

- Quarto binary integration (separate step; the OP7 single-file path is
  unchanged)
- PDF/Word export formats
- Per-agent charts beyond the spectrum and quality bar chart

### Success Criteria

- The project final report is a rendered HTML document without raw quarto/
  R fragments
- The report contains embedded spectrum + quality charts, original data,
  recommendations and source code
- Charts degrade gracefully without matplotlib; the legacy fallback stays
- Existing test matrices stay green (no regressions)

## Completed Task: OP10 - Project Workflow (Upload -> Preparation -> Release -> Crew -> Quarto Report)

### Objective
Structure the end-to-end workflow as an analysis project: uploaded files open a
new project (file-type agnostic), phase 1 turns the files into usable datasets
(measurement data + metadata) with a preparation report, quality assessment and
improvement recommendations for the user. The user adapts the data (re-ingest)
and releases the project; phase 2 runs the full NIRAnalysisCrew over every
usable dataset with one report section per agent (content + charts), renders
the project overview page and generates the final comprehensive Quarto report
(original data, source code, evaluation and graphics).

### Predecessors
- S1-S9 + G1-G8: COMPLETED
- OP1-OP4, OP6, OP7: COMPLETED (OP7 delivers the single-file crew bridge)

### Scope
- `core/models.py`: new `AnalysisProject` model (phases drafted/released/
  completed, preparation report, crew results, final report path) + migration
  `0004_analysisproject.py`
- `services/project_ingest.py`: phase 1 - files -> datasets (measurement data,
  metadata) + metadata quality assessment + improvement recommendations
- `services/project_crew.py`: phase 2 - full crew run per dataset, per-agent
  report sections, final comprehensive report generation
- `django_project/api/project_views.py` + `project_urls.py`: project list,
  create, detail (phase 1 report + phase 2 overview), re-ingest, release,
  final report download
- Templates `projects.html`, `project_report.html` (datasets, recommendations,
  per-agent sections, release/re-ingest buttons, final report link)
- `tests/test_op10_project_workflow.py` (56 checks) + CI matrix extended

### Out of Scope
- Inline metadata editing (adaptation = re-upload / re-ingest of adapted files)
- Federated learning, chatbot and ILIAS changes
- Live container verification (target machine)

### Success Criteria
- Upload opens a project; preparation report shows datasets, metadata quality
  and improvement recommendations
- User can re-ingest adapted data and release for analysis
- Phase 2 produces per-agent report sections and the final comprehensive report
- Existing test matrices stay green (no regressions)
