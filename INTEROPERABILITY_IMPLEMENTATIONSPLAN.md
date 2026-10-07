# Implementationsplan: Interoperabilität & Datenmodell (NIR-IP)

Status: Future Release (vorgemerkt, Freigabe durch Head of Development)
Quelle: Analyse von 15 Open-Source-Spektronomie-Projekten (OpenChrom, HyperSpy,
Mantid, SpectroChemPy, RamanSPy, Open Specy, Orange, PyOpenMS, MZmine, OpenMS,
NMRium, CcpNmr, Fityk, RDKit, specutils). Lizenz-Verifikation: siehe
`THIRD_PARTY_LICENSES.md`; Lizenz-Regel: siehe `AGENTS.md`.

## Ziel und Master-Objective-Bezug

Stärkung der Master Objectives 1 (format-agnostischer Import), 11 (ähnliche
Spektren identifizieren), 12 (Wellenlängen mit Datenbank vergleichen) und 9
(Kalibrationen optimieren) durch: semantisches Spektrum-Datenmodell mit Einheiten,
zusätzliche Labor-Importformate, eine bevölkerte Referenzspektren-Datenbank und
reproduzierbare Verarbeitungs-Pipelines.

## Release-Inhalte (nach Priorität)

### P1 — Einheiten-bewusstes Spektrum-Datenmodell (`SpectrumRecord`)

- Neue Kernstruktur in `NIR_Intelligence-main/services/` (Vorschlag:
  `spectrum_record.py`): Pflichtfelder `x_values`, `x_unit` (`nm` | `cm^-1` |
  `µm` | `wavenumber`), `y_unit`, `x_label`, `provenance`, optionale
  `spectral_regions`.
- Zentraler Einheiten-Konvertierer (nm ↔ cm⁻¹ ↔ µm); alle Vergleiche
  (FAISS, Qdrant, Referenz-DB) laufen nur über normalisierte Einheiten.
- Migration: `_load_spectral_data()` (`agents/data_preparation_agent.py`)
  liefert zusätzlich `x_unit`/`y_unit` — SPC x-units werden bereits gelesen
  (`tests/test_s3_format_loaders.py`), JCAMP-Header analog auswerten;
  unbekannte Einheit → `unknown` + Warnung (kein Silent-Fail).
- Vorbild: SpectroChemPy `NDDataset` (CeCILL-B, Abhängigkeit zulässig —
  hier jedoch Konzept-Nachbau ohne neue Dependency, gemäß Anti-Code-Creep).

### P2 — Bruker OPUS `.d`-Import und echter JCAMP-DX-Parser

- OPUS `.d`-Verzeichnis-Reader (in Bruker-Laboren de-facto-Standard) — eigenständige
  Implementierung, Referenz: öffentliche OPUS-Formatdokumentation/opusFC (MIT).
- JCAMP-DX (ASTM) als strukturierter Parser statt Text-Fallback; bestehende
  `.jdx`-Route in `data_preparation_agent.py` ersetzen.
- Erweiterung der Loader-Testmatrix (`tests/test_s3_format_loaders.py`).

### P3 — Referenzspektren-Datenbank (Objektive 11/12)

- `spectrum_database`-Erweiterung (`services/spectrum_database.py`): Import-Routine
  für öffentliche NIR-Referenzdatensätze; je Eintrag Pflichtmetadaten `source`,
  `license`, `version`, `instrument`, `x_unit`.
- **Lizenz-Regel:** Je Datensatz Lizenz einzeln verifizieren und in
  `THIRD_PARTY_LICENSES.md` dokumentieren; nur eindeutig weitergabefähige Daten
  einbringen (Vorbild Open Specy, MIT-Software; Datenbestand separat geprüft).
- Endpunkt „Match gegen Bibliothek": Konfidenz + Quellenanzeige je Treffer.

### P4 — `PipelineRecord` für Reproduzierbarkeit

- Je Spektrum vollständige Verarbeitungs-Kette maschinenlesbar speichern
  (Operation + Parameter je Schritt; SNV/MSC/Savitzky-Golay/Detrending aus
  `data_preparation_agent.py` erfassen).
- Ausgabe als Methodensektion im Quarto-Report; JCAMP-DX-Export als
  Interchange-Format für analysierte Spektren.
- Vorbild: Mantid Algorithmus-Log — **GPL, daher nur Konzept-Nachbau,
  kein Code und keine Dependency.**

### P5 — Peak-Fitting-Modul (Feature-Extractor)

- Eigenständiges scipy-basiertes Peak-Detection-Modul
  (`scipy.signal.find_peaks`, Second-Derivative-Peaks); Integration in
  `shift_detector_agent` (Drift) und FAISS-Peakvergleich.
- Vorbild: Fityk — **GPL-2.0, strikt nur Konzept, Modul komplett eigenständig
  mit scipy bauen.**

### Zurückgestellt / out of scope

- Visuelle Workflow-Editoren (Orange/MZmine-Stil) und weitere
  Framework-Ebenen: Aufwand/Nutzen für das Lehrszenario zu schlecht.
- CcpNmr: restriktive Lizenz, keine Anleihe.
- RDKit: erst bei Struktur-Wirkungs-Kopplung relevant.

## Meilensteine

1. M1: `SpectrumRecord` + Konvertierer + Migration der Loader, Tests grün.
2. M2: OPUS `.d` + JCAMP-DX-Parser, Testmatrix erweitert (M1+M2 = Objektiv 1).
3. M3: Referenz-DB-Import inkl. Lizenz-Dokumentation je Datensatz.
4. M4: `PipelineRecord` + Quarto-Methodensektion + JCAMP-DX-Export.
5. M5: Peak-Fitting-Modul, Integration Drift/Peakvergleich.

Jeder Meilenstein: fokussierter Commit, `THIRD_PARTY_LICENSES.md` bei neuen
Third-Party-Berührungen aktualisieren, Iterationsregel (ERRORS/CRITICAL_WARNINGS/
OPEN_CHANGE_REQUESTS = 0) je Meilenstein erfüllen.

## Lizenz-Compliance (verbindlich für alle Schritte)

- Permissiv (MIT/BSD/Apache/CeCILL-B/MPL): Abhängigkeit zulässig, Attribution wahren.
- Copyleft (GPL/EPL) und restriktive Lizenzen: kein Code, keine Dependency — nur
  Konzept-Nachbau. Betrifft hier: HyperSpy, Mantid, Fityk, OpenChrom, CcpNmr.
- Vor jeder Umsetzung: Lizenz der konkret genutzten Quelle gegen
  `THIRD_PARTY_LICENSES.md` verifizieren; im Zweifel Head of Development fragen.
