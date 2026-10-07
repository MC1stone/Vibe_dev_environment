# Third-Party-Lizenzen — Verifikation der analysierten Open-Source-Spektronomie-Software

Zweck: Referenz für die Lizenz-Compliance-Regel in `AGENTS.md`. Verifiziert per
Projekt-Homepage/Repository/PyPI (Stand der Prüfung; vor jeder konkreten Integration
erneut gegen die jeweilige Quelle prüfen).

## Erlaubte Nutzungsarten

- **Abhängigkeit zulässig** (permissive Lizenz): Bibliothek darf als Dependency
  eingebunden werden; Attribution/Copyright-Hinweis wahren.
- **Nur Konzept** (Copyleft): weder Code übernehmen noch einbinden — nur die
  Idee als eigenständige, unabhängige Entwicklung nachbauen.
- **Nicht nutzen**: keine Anleihe jeglicher Art.

## Auswertung

| Projekt | Lizenz | Nutzungsart für NIR-IP | Relevanz |
|---|---|---|---|
| SpectroChemPy | CeCILL-B (BSD-artig, permissiv) | Abhängigkeit zulässig | Einheiten-/Datenmodell, OPUS-/JCAMP-Reader |
| OpenMS / pyOpenMS | BSD-3-Clause | Abhängigkeit zulässig | Pipeline-/Modulkonzept (kein NIR-Bezug, geringe praktische Relevanz) |
| Open Specy | MIT (Software; Datenbank separat prüfen) | Software zulässig; **Datenbestand vor Einbringung einzeln lizenzprüfen** | Referenzspektren-Datenbank-Konzept |
| RamanSPy | MIT | Abhängigkeit zulässig | Benchmark-Dataloader-Konzept, ML-Preprocessing |
| specutils (Astropy) | BSD-3-Clause | Abhängigkeit zulässig | SpectralRegion-/Einheiten-Konzept |
| NMRium | MIT | Abhängigkeit zulässig | Browser-first-Spektrenanzeige (Konzept) |
| MZmine | MIT (Code) | Abhängigkeit grundsätzlich zulässig | Pipeline-GUI-Konzept (MS-Fokus, gering) |
| Orange / Orange Spectroscopy | BSD (Orange-Kern) | Abhängigkeit zulässig | Interaktive Exploration (Konzept) |
| HyperSpy | **GPL-3.0** | **Nur Konzept** | Interoperabilität/Standards (NeXus/EMD), lazy Arrays |
| Mantid | **GPL-3.0 (LGPL für Teile)** | **Nur Konzept** (Kern); Teile LGPL → Einzelfallprüfung | Provenance/Algorithmus-Log, Reproduzierbarkeit |
| Fityk | **GPL-2.0** | **Nur Konzept** | Peak-Fitting-Modul → eigenständig mit scipy nachbauen |
| OpenChrom | **EPL-1.0/2.0** | **Nur Konzept** | Konverter-Orchestrierung |
| CcpNmr Analysis v3 | **Restriktiv/kommerziell** (v2: LGPL für Datenmodell) | **Nicht nutzen** (v3); v2-Datenmodell-Idee: Dokumentation genügt | Experiment-Datenmodell |
| RDKit | Apache-2.0 (Teile BSD/LGPL) | Abhängigkeit zulässig | nur bei künftiger Struktur-Wirkungs-Kopplung |

## Konsequenzen für die Analyse-Empfehlungen

1. **Einheiten-Datenmodell, JCAMP-DX/OPUS-Reader:** SpectroChemPy (CeCILL-B) und
   specutils (BSD) sind als Abhängigkeit zulässig; alternativ eigenständig nachbauen.
2. **Peak-Fitting:** Fityk ist GPL — Modul **eigenständig mit scipy** implementieren,
   keinen Fityk-Code portieren.
3. **PipelineRecord/Provenance:** Mantid ist GPL — nur das Konzept des
   Algorithmus-Logs nachbauen, keine Mantid-Klassen übernehmen.
4. **Interoperabilität (NeXus etc.):** HyperSpy ist GPL — Standards (NeXus ist
   eigenes, permissives Format) direkt gegen die Formatspezifikation umsetzen,
   nicht gegen HyperSpy-Code.
5. **Referenzdatenbank:** Open Specy als Software (MIT) nutzbar; die Referenzdaten
   selbst unterliegen teils anderen Lizenzen → je Datensatz Quelle und Lizenz
   dokumentieren, nur eindeutig weitergabe-fähige Daten einbringen.

## Für die Umsetzung konkret genutzte/geprüfte Pakete (M2)

| Paket | Lizenz | Entscheidung | Datum |
|---|---|---|---|
| opusfc | MIT | Als optionale Dependency für OPUS-`.d`-Import zulässig (`services/opus_reader.py`, lazy import; ohne Installation greift der content-driven Fallback) | bei M2-Umsetzung verifiziert |
| brukeropusreader | GPLv3 | **Verworfen** — Copyleft-Verstoß gegen die eigene Regel | bei M2-Umsetzung verifiziert |
| brukeropus | MIT (PyPI) | Nicht genutzt; Alternative falls opusfc nicht genügt | bei M2-Umsetzung verifiziert |

Der JCAMP-DX-Parser (`services/jcamp_parser.py`) ist eigenständig gegen die
öffentliche JCAMP-DX-Data-Label-Spezifikation entwickelt — kein Third-Party-Code.

## Regel für künftige Third-Party-Software

Siehe `AGENTS.md`, Abschnitt „Nicht verhandelbare Regeln" → Lizenz-Compliance.
Vor jeder neuen Abhängigkeit: Lizenz hier ergänzen (Projekt, Lizenz, Quelle,
Datum der Prüfung, Entscheider).
