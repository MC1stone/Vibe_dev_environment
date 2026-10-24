# Artikel-Update: Neuausrichtung Öffentlicher Sektor + Sensor-Datenbank + Standardisierte Testeinheit

> Stand 24.10.2026. Ergänzung zum konsolidierten Artikel-Stand (20.10.2026,
> `ARTICLE_FINAL_VERSION_MARKED.md`) und zur letzten PDF-Fassung
> (konsolidierter Artikel-Stand 19.10.2026). Der Artikel ist auf den
> **öffentlichen Sektor** ausgerichtet. Die Software wird in zwei Teile
> geteilt: dieser Artikel beschreibt ausschließlich die **Plattform für den
> öffentlichen Sektor** (Teil 1); die **Sensor-Datenbank** und die
> Informationen zur **standardisierten Testeinheit** sind Bestandteil dieses
> Artikels. Die Teilung der Software folgt als zweiter Arbeitsschritt.
>
> **Ehrlichkeitsregel:** Alle beschriebenen Software-Eigenschaften sind
> real implementiert und getestet (OP29, OP49, OP53, OP68 — siehe
> Verifikation unten). Die Artikel-Texte sind fertig formuliert zum direkten
> Übernehmen in das Manuskript.

---

## 1. Fertige Manuskript-Änderungen (Englisch, zum Übernehmen)

### 1.1 Titel

> NIR-IP: An Open-Science Infrastructure for Iterative, Reproducible
> Low-Cost VIS/NIR Spectroscopy **in the Public Sector**

### 1.2 Abstract — zwei neue Sätze (nach dem Fünf-Kapazitäten-Satz)

> This fragmentation hits the **public sector** hardest — municipal
> laboratories, schools and universities, environmental and food-safety
> authorities, and non-governmental organizations buy the same inexpensive
> sensors as industry, but lack the commercial suites, the certified
> reference materials, and the specialist staff that make their measurements
> trustworthy and comparable. … Two further components address the
> public-sector setting directly: a **sensor database** that consolidates
> everything the platform knows about every device in use — adapter
> profiles, recorded settings, plausibility assessments, documents, and
> AI-generated summaries — and a **standardized test unit** in the form of a
> sensor-agnostic reference-measurement protocol contract (dark/white
> references, at least 50 repetitions, declared as metadata) that places any
> compliant device on a common radiometric scale without prescribing
> hardware and without certified reference material.

### 1.3 Abstract — Schlusssatz (ersetzt den Citizen-Science-Schlusssatz)

> This iterative, self-critical, fully traceable behaviour, not predictive
> accuracy, is the property that reproducible spectroscopy in the public
> sector requires: a measurement taken by a municipal lab, a school, or a
> citizen-science group becomes scientifically usable exactly when its
> analysis can show, from its own archived history, why its number deserves
> trust — and comparable across institutions when every device declares the
> same standardized test unit.

### 1.4 Keywords (erweitert)

> low-cost spectroscopy; VIS/NIR spectroscopy; **public sector; municipal
> laboratories; education;** citizen science; iterative analysis; multi-agent
> systems; metadata governance; FAIR data; scientific reproducibility;
> provenance tracking; **sensor database; standardized test unit; reference
> measurement protocol;** federated calibration; chemometrics; automated
> quality assurance; data fusion

### 1.5 §1.2 Motivation — neuer Absatz (Öffentlicher Sektor)

> The public sector faces this trust problem under the tightest constraints.
> A municipal laboratory or a school buys the same consumer-grade sensor as
> a research group, but cannot buy the commercial analysis suite, cannot
> commission certified reference materials, and cannot employ a
> chemometrician to audit every pipeline. Measurements that should be
> comparable across institutions — the same water body measured by an
> authority and by a citizen group, the same batch screened by two
> municipal labs — are in practice incomparable, because nothing records
> the device, the settings, the reference measurements, or the quality
> verdict behind each number. When public decisions rest on such
> measurements, the missing infrastructure is not a convenience gap but a
> governance gap. NIR-IP addresses this audience directly: it is designed to
> run on local hardware, to require no certified reference material, to
> teach correct measurement practice through its interface, and to make
> every number traceable to the device, the settings, and the quality
> verdicts that produced it.

### 1.6 §1.3 Technology Landscape — Satz-Erweiterung

> … and increasingly the statutory and educational tasks of the public
> sector: municipal food and water surveillance, school and university
> teaching, environmental screening by authorities, and community-based
> monitoring by NGOs and citizen groups. These are precisely the
> applications in which measurement conditions are least controlled **and**
> the operators are least specialized: a public-sector user is typically not
> a chemometrician, works with a consumer device, and must still produce a
> number that a colleague in another institution — or a regulator — can
> trust and compare.

### 1.7 §1.5 Delimitation — neuer Absatz (Artikelumfang Teil 1)

> **Scope of this article.** This article describes exclusively the platform
> for the public sector (part 1 of the software split). It does not cover:
> commercial laboratory workflows, proprietary acquisition formats of
> commercial laboratory instruments, certified reference materials (CRMs)
> and regulatory calibration procedures — public-sector institutions
> typically cannot procure these; the platform relies on the standardized
> test unit instead (dark/white reference protocol, Section 6.7). Also not
> covered: the commercial product variant of the software (part 2), which is
> split off from this software in a second work step. The article does not
> claim a superior prediction model; the tomato Brix dataset serves solely
> as proof of concept.

### 1.8 §3.2 Sensor Database (neuer Abschnitt, Figure 5)

> The platform maintains a **sensor database** that consolidates everything
> it knows about every spectrometer in use — the component a public-sector
> institution needs most, because its devices are heterogeneous (a school's
> DIY spectrometer, a municipal lab's consumer sensor, a university's
> grating module) and nobody keeps the overview by hand. The database has
> three layers (Figure 5).
>
> **Layer 1 — registered adapters.** Every device the platform can talk to
> is described by an adapter profile in the device registry (`devices/`):
> capabilities (wavelength range, detector, interface, resolution,
> streaming, external trigger) and the calibration contract. New devices are
> integrated by implementing one adapter interface and registering a model
> ID — the platform core never changes, and no file format is hard-coded.
> The registry currently covers the proof-of-concept sensor (SparkFun Triad,
> AS7265x), a DIY ESP32-S3 camera spectrometer, and a DIY matchbox
> spectrometer; the adapter contract is the extension point for every
> further device.
>
> **Layer 2 — usage from the existing database.** The catalog reads what
> analyses have actually recorded — instrument types on spectrum records,
> recorded settings in preparation reports and crew results — without
> introducing new tables. Usage statistics (spectra, projects, samples, last
> used) and the recorded setting values appear per sensor, together with
> deduplicated optimization suggestions from the crew analyses. Names that
> do not match a registered adapter are not silently deduplicated: an
> AI-supported matcher proposes assignments ("SparkFun Triad" vs. "Triad")
> and asks the user.
>
> **Layer 3 — the per-sensor information page.** Each sensor has a single
> page (`/projects/sensors/<name>/`) combining the adapter profile, the
> recorded usage, a completeness and plausibility assessment of the recorded
> settings (checked against the known device limits, e.g. a scan count
> above the instrument maximum is flagged), uploaded documents of any type
> (datasheet, manual, calibration certificate), and a live AI-generated
> summary executed locally — with an honest fallback when the local model
> server is unavailable.
>
> The database feeds back into analysis: the metadata agent's plausibility
> checks use the known device limits, the fusion branch's
> reference-protocol compliance check (Section 6.7) reads the sensor's
> declared references, and the introduction page teaches device-specific
> measurement practice — the same dark/white reference protocol the fusion
> branch enforces. For the public sector this is the difference between
> owning a sensor and being able to defend its measurements: the database
> turns scattered device knowledge into one governed, inspectable record per
> instrument.

### 1.9 §6.2 — Screenshots der Metadaten-Governance (Figures 6–7)

> The two screenshots show the governance dialogue in operation on the
> proof-of-concept dataset: the overview grades the recorded metadata
> (Figure 6) and surfaces the open questions the metadata agent formulates;
> the improvement dialogue (Figure 7) turns each missing field into a
> concrete, answerable question. For a public-sector user without specialist
> training this dialogue is the governance mechanism made tangible:
> governance becomes a conversation, not a checklist. Both screenshots are
> taken from the running platform (German UI); the platform is fully
> internationalized (i18n), and the figures are labelled as German originals
> in the caption.

### 1.10 §6.7 — Standardized test unit (neuer Unterabschnitt, Figure 8)

> **The standardized test unit: a reference-measurement protocol, not a
> device.** The reference-protocol contract of Section 6.7 is the
> platform's answer to a question the public sector cannot solve by
> procurement: how can measurements from different institutions, on
> different devices, become comparable when no one can afford certified
> reference materials or a calibration laboratory? NIR-IP defines a
> **standardized test unit** as a *measurement condition* — not a prescribed
> instrument. Every source declares two reference measurements as metadata:
> a **dark** reference (shutter closed / no illumination) and a **white**
> reference (a diffuse reflectance standard), each with at least 50
> repetitions and a declared artifact (Figure 8). From compliant references
> the platform estimates the sensor transfer function radiometrically —
> (raw − dark)/(white − dark) per channel, smoothed over the wavelength
> axis, with a confidence note derived from the repetition spread — and
> offers the resulting gain curve as a correction variant in the fusion
> loop. Reference datasets never enter a calibration: they are declared as
> `reference_measurement` and are not samples.
>
> Three properties make this contract suitable for the public sector.
> **Comparability:** any device that measures the two references can be
> placed on a common radiometric scale — a school's DIY spectrometer and a
> municipal lab's consumer sensor become comparable without either
> institution buying anything beyond a diffuse white standard and a
> light-tight cover. **Teachability:** the platform's introduction page
> teaches exactly this protocol — lighting conditions, the dark/white
> reference procedure, the metadata contract — with the sensor database
> (Section 3.2) feeding device-specific guidance; one procedure, every
> device. **Trust without certification:** dark and white references are
> reproducible by anyone, and the repetition spread states the confidence
> honestly; the platform never simulates a gain curve when the contract is
> not met — it reports "not estimable" together with the protocol text, as
> it did for both tomato sources. The measurement-condition contract, not a
> device list, is what makes the infrastructure sensor-agnostic — and it is
> the same contract that scales to every future sensor added to the growing
> database.

### 1.11 §5 — Ergänzung nach §5.6 (Öffentlicher Sektor)

> For the public sector the loop is more than convenience. A measurement
> taken by a municipal laboratory, a school, or a citizen-science group
> becomes scientifically usable — and comparable across institutions —
> exactly when its analysis can show, from its own archived history, why
> its number deserves trust: which device produced it (sensor database,
> Section 3.2), which settings and quality verdicts accompanied it, and
> which standardized test unit (Section 6.7) placed it on a common scale.

### 1.12 §7.3 Limitations — neuer Absatz

> Public-sector scope: the platform is designed for, and demonstrated on,
> consumer-grade low-cost devices in public-sector settings; it does not
> replace certified reference materials or regulatory calibration
> procedures, and its standardized test unit (Section 6.7) is a
> comparability contract, not a certification. The proof of concept uses
> one dataset, one sensor model, one target analyte; the public-sector
> claim is about the infrastructure's behaviour — governance, quality
> verdicts, comparability — not about predictive performance on any
> particular analyte.

### 1.13 §8 Conclusions — neuer Absatz "Vision for the public sector"

> The longer-term vision is a standard infrastructure for public-sector
> spectroscopy: a world in which a measurement taken by a municipal
> laboratory, a school, or a citizen-science group on a consumer device
> carries enough governance to be scientifically usable — and enough
> standardization to be comparable across institutions. The sensor database
> (Section 3.2) gives every institution one governed record per device; the
> standardized test unit (Section 6.7) gives every device a common
> radiometric scale without certified reference material; the metadata
> governance and provenance machinery makes every number traceable; and the
> platform that produced the analysis can prove, from its own iteration
> archive, exactly why that number deserves trust. Public-sector
> institutions then share calibration models federated — improving each
> other's measurements without centralizing their data — and a regulator,
> a teacher, or a citizen can audit any number back to the device, the
> settings, and the quality verdicts that produced it.

### 1.14 Data Availability / Appendix A / Supplementary Materials — Ergänzungen

> … the sensor database contents (adapter profiles, recorded usage,
> plausibility assessments) are reproducible from the platform's own
> database via the sensor pages (Section 3.2). … sensor database export
> (adapter profiles for all registered devices, recorded usage statistics,
> setting plausibility assessments); standardized test unit specification
> (reference-measurement protocol contract: dark/white, ≥ 50 repetitions,
> metadata schema) with the compliance-check implementation and the honest
> "not estimable" reporting path; UI screenshots of the metadata governance
> dialogue (Figures 6–7) and the figure sources (SVG + 300-dpi PNG) for
> Figures 1–8 in `article_figures/`.

---

## 2. Neue Figuren und Screenshots (`article_figures/`)

| Datei | Inhalt | Abschnitt |
|---|---|---|
| `fig5_sensor_database.svg` / `.png` (300 dpi) | Sensor-Datenbank: drei Ebenen (Adapter-Registry, Nutzung aus Bestands-DB, Sensor-Informationsseite) + Rückkopplung in die Analyse | §3.2, Figure 5 |
| `fig6_metadata_scorecard_screenshot.png` | Screenshot: Datensatz-Übersicht mit Metadaten-Score, Missing-Field-Analyse, offenen KI-Fragen (deutsche UI) | §6.2, Figure 6 |
| `fig7_metadata_dialog_screenshot.png` | Screenshot: Metadaten-Verbesserungsdialog (Felder operator/humidity/temperature/instrument/acquisition_time, Liste fehlender Felder, deutsche UI) | §6.2, Figure 7 |
| `fig8_test_unit.svg` / `.png` (300 dpi) | Standardisierte Testeinheit: Referenz-Protokoll-Vertrag (dark/white, ≥ 50 Wiederholungen), radiometrische Auswertung, Rolle im Korrektur-Loop, öffentlicher-Sektor-Rationale | §6.7, Figure 8 |
| `make_fig5_fig8.py` | Reproduzierbares Generator-Skript für fig5 + fig8 (matplotlib, 300 dpi) | — |

Die Screenshots (fig6/fig7) sind echte UI-Aufnahmen aus
`NIR_Intelligence-main/docs/images/` (Bild1/Bild2), umbenannt und im Artikel
als deutsche Original-UI gekennzeichnet. fig5 und fig8 sind neue Grafiken im
einheitlichen Stil von fig1–fig4 (SVG = Vektorquelle, PNG = 300 dpi
druckfertig); die Generierung ist über `make_fig5_fig8.py` reproduzierbar.

---

## 3. Verifikation (Programm-Stand — alles real implementiert)

Die beschriebenen Software-Eigenschaften wurden gegen den tatsächlichen
Code verifiziert (keine Erfindungen):

- **Sensor-Datenbank (§3.2):**
  - Adapter-Registry: `devices/base_spectrometer.py`
    (`SpectrometerAdapter`, `SpectrometerCapabilities`,
    `CalibrationParameters`), `devices/registry.py`
    (`SpectrometerRegistry`, MODEL_ID-Lookup),
    registrierte Adapter: `devices/sparkfun_triad.py` (MODEL_ID
    `sparkfun_triad`), `devices/esp32_s3_camera.py`, `devices/diy_matchbox.py`.
  - Katalog ohne neue Tabellen: `services/sensor_catalog.py` (liest
    `SpectrumRecord.instrument_type`, Preparation-Reports, Crew-Ergebnisse;
    `suggest_sensor_matches` — KI-Match mit Rückfrage, keine stille
    Deduplizierung).
  - Sensor-Seiten: `SensorListView` / `SensorDetailView` /
    `SensorSummaryView` / `SensorDocumentUploadView` in
    `django_project/api/project_views.py` (Zeilen 262–461), Routen in
    `django_project/api/project_urls.py` (72–81), Templates
    `sensor_list.html` (222 Zeilen) / `sensor_detail.html` (319 Zeilen).
  - Dokumente pro Sensor: `services/sensor_documents.py` (`DOC_TYPES`,
    Upload/Delete, `document_stats`); `django_project/core/models.py`
    (`SensorDocument`, Zeile 1292).
  - Tests: **OP29 53/53 grün**, **OP49 23/23 grün**, **OP53 46/46 grün**
    (lokal ausgeführt am 24.10.2026).
- **Standardisierte Testeinheit (§6.7):**
  - Protokoll-Vertrag: `services/fusion_sensor_analysis.py` —
    `reference_measurements()` prüft `reference_type` ('dark' | 'white'),
    `n_repeats >= 50`, Artifact; Datensätze mit `dataset_type ==
    'reference_measurement'` fließen nie in eine Kalibration ein
    (Zeilen 22–24, 41–70, 102, 202, 242).
  - Radiometrische Auswertung: `(raw − dark)/(white − dark)` pro Kanal,
    Glättung über die Wellenlängenachse, Confidence-Note aus der
    Wiederholungsspanne; Gain-Kurve als Korrektur-Variante; bei
    Nichterfüllung ehrliche Meldung "not estimable" mit Protokolltext —
    nie simuliert.
  - Sensor-Agent-Beitrag: `agents/sensor_quality_agent.py`
    (`SensorQualityAgent`, Referenz-Compliance-Check für Fusionsprojekte).
  - Tests: **OP68 44/44 grün** (lokal ausgeführt am 24.10.2026).
- **Berichte (Referenzen im Artikel):**
  - Produktionsbericht 25.09.2026 (29 Seiten, 23 Figuren, Score 81.7/100,
    Projekt-ID 69613ab6-8962-4f6e-be2e-09e3589f1474) — zitiert als [28].
  - Report-Artefakte im Repo: `django_project/static/reports/`
    (`test_spectral_report.html`, `test_metadata_report.html`,
    `test_custom_report.html` + Params-YML), Quarto-Templates unter
    `django_project/templates/reports/`.
  - KNIME-Referenz: `knime/tomato_brix_reference/FUSION_ANALYSIS.md` +
    `VALIDATION_REPORT.md` (Fusions-Gegencheck mit Korrekturvarianten).
- **Screenshots:** echte UI-Aufnahmen aus dem laufenden Stack
  (`docs/images/Bild1.png`, `Bild2.png`), als Figures 6–7 eingebunden und
  als deutsche Original-UI gekennzeichnet (Gestaltungsregel E des
  PDF-Anhangs: deutsche Original-Screenshots beibehalten, im Caption
  benennen).

### Testlauf (lokal, 24.10.2026)

```text
OP29 sensor agent matrix:            53 passed, 0 failed
OP49 sensor websearch + DIY matrix:  23 passed, 0 failed
OP53 sensor pages matrix:            46 passed, 0 failed
OP68 fusion sensor correction:       44 passed, 0 failed
```

Hinweis: OP49 benötigt lokal kompilierte Übersetzungsdateien
(`django_project/locale/{de,en}/LC_MESSAGES/django.mo`, via polib aus den
vorhandenen `.po`-Dateien erzeugt — `.mo` ist git-ignored, kein Commit
nötig).

---

## 4. Software-Teilung (zweiter Arbeitsschritt — folgt)

Die Software wird in zwei Teile geteilt:

- **Teil 1 — Öffentlicher Sektor** (dieser Artikel): Plattform inkl.
  Sensor-Datenbank (§3.2) und standardisierter Testeinheit (§6.7).
- **Teil 2 — Kommerzielle Variante**: wird in einem zweiten Arbeitsschritt
  abgespalten (Roadmap S1–S9, Abschnitt `REPOSITORY_ALIGNMENT_AND_ROADMAP.md`).

Dieser Artikel beschreibt ausschließlich Teil 1 (siehe §1.5 Delimitation).
