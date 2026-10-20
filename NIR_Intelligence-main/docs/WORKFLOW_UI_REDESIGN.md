# NIR-IP Workflow & UI Redesign — Expertengruppen-Entwurf

Version: 1.0 (Entwurf zur Freigabe)
Autoren: Expertengruppe (Interface-Analyse, NIR-Workflow, UI/Usability)
Basis: Vollständige URL-/Template-Aufnahme der Django-App, MISSION_STATEMENT
(Master Objectives 1–15), Nutzer-Feedback aus dem Live-Test

---

## Experte 1: Ist-Analyse der Django-App (Bestandsaufnahme)

### 1.1 Vorhandene Seiten (28 Templates, alle URLs verifiziert)

| Seite | URL | Zweck | In Hauptnavigation? |
|---|---|---|---|
| Dashboard | `/dashboard/` | Übersicht, Kachel-Einstieg | ❌ nein (nur `/`) |
| Projekte | `/projects/` | Projektliste, Anlage, Analyse-Orchestrierung | ✅ „Projekte" |
| Projekt-Detail | `/projects/<id>/` | Dateien, Crew-Analyse, Freigabe, Report | (unter Projekte) |
| Spektraldatenbank | `/projects/database/` | Persistierte Spektren, Referenz-Import | ✅ (Untermenü) |
| Kalibrierung | `/calibration/` | Kalibrationsübersicht (RMSECV/RPD) | ✅ „Kalibrieren" |
| Sensoren | `/projects/sensors/` | Sensor-Datenbank | ✅ „Sensoren" |
| DIY-Spektrometer | `/api/projects/sensors/diy/` | Selbstbau-Anleitungen | ✅ (Untermenü) |
| ILIAS | `/ilias/` | E-Learning-Anbindung | ✅ „Lernen mit Kursen" |
| Federated | `/federated/` | Föderiertes Lernen | ✅ (Untermenü) |
| **Spektren** | `/spectra/` | Upload, Galerie, Einzel-Analyse | ❌ **NICHT verlinkt** |
| Dateien | `/files/` | Generische Dateiverwaltung | ❌ |
| Analyse | `/analysis/` | Analyse-Ergebnisse | ❌ (nur per Redirect) |
| Jobs | `/jobs/` | Job-Status | ❌ |
| Agents | `/agents/` | Agenten-Status | ❌ |
| Chatbot | `/chatbot/` | Ergebnis-Diskussion (MO 10) | ❌ |
| Workflow-Liste/Ergebnisse | — | alte Workflow-UI | ❌ (Leiche) |
| Reports | `/documentation/` | Doku/Reports | ❌ |
| Settings | `/settings/` | Einstellungen | ❌ |
| Login/Register | `/login/`, `/register/` | Auth | Footer/Login |
| Dashboard (farbig) | — | `dashboard_colorful.html` = `/dashboard/` | als `/dashboard/` |

### 1.2 Befunde der Interface-Analyse

**B1 — Verwaiste Seiten (nicht erreichbar über Navigation):**
`/spectra/`, `/files/`, `/analysis/`, `/jobs/`, `/agents/`, `/chatbot/`,
`/settings/`, `/documentation/` existieren und sind funktional, sind aber
**nirgends in der Hauptnavigation verlinkt**. Der Nutzer kann sie nur durch
Zufall (Redirect nach Analyse) oder URL-Raten finden. Das ist die
Hauptursache des Nutzer-Feedbacks („Seite Spectra ist nirgendwo verlinkt").

**B2 — Doppelte/parallele Konzepte:**
- „Spektren" (`/spectra/`, NIRSpectrum) vs. „Spektraldatenbank"
  (`/projects/database/`, SpectrumRecord) vs. „Dateien" (`/files/`,
  GenericFile) — drei Speicherungen für Messdaten, für den Nutzer
  nicht unterscheidbar.
- „Analyse starten" (Spektren-Seite, sofort-Response) vs. „Projekt
  analysieren" (Projekt-Detail, Crew-Workflow mit Statusseite) vs.
  „Quick Analysis" („Analyze Now"-Kachel, `quickAnalyzeSelected`) —
  drei Analyse-Einstiege mit unklarer Abgrenzung.
- Dashboard (`/dashboard/`) ist nicht Startseite und nicht verlinkt.

**B3 — Inkonsistente Beschriftung:**
- „Analyze Now" (Kachel) vs. „Analyse starten" (Tabelle/Galerie) vs.
  „Analyze Spectrum" (Modal) vs. „Quick Analysis" — vier Labels für
  dieselbe Aktion; Mischung Englisch/Deutsch obwohl i18n vorhanden.
- Navigation: „Projekte/Sensoren/Kalibrieren/Lernen mit Kursen" (deutsch),
  Seiteninhalte überwiegend englisch.

**B4 — Buttons ohne klare Wirkung:**
- „Analyze Now"-Kachel: wirkt auf „selected spectra", ohne dass markierte
  Auswahl sichtbar kommuniziert wird.
- Analyse-Redirects auf `/analysis/` — Erfolgs-/Fehlermeldung nur als
  flüchtiger Toast, dann weg.

**B5 — Workflow-Leichen:** workflow_list/workflow_results-Templates und
Dateien-Seite ohne Rolle im aktuellen Konzept.

---

## Experte 2: NIR-Workflow-Ordnung (fachliche Reihenfolge)

### 2.1 Der fachliche Kernprozess (aus Mission/Objectives 1–15)

Ein NIR-Analytiker arbeitet naturgemäß in dieser Reihenfolge:

1. **Messung erfassen** — Datei ins System bringen (MO 1–3)
2. **Datenqualität prüfen** — Sensor/Drift, Ausreißer (MO 4–5)
3. **Analysieren** — Statistik + NN parallel, Metadaten-KI (MO 6–7, 2–3)
4. **Kalibrieren** — Modell erstellen, optimieren, RMSECV/RPD beurteilen (MO 8–9)
5. **Vergleichen** — gegen Referenz-/Bibliotheksspektren (MO 11–12)
6. **Dokumentieren** — Report, Reproduzierbarkeit (MO 13)
7. **Lernen/Lehren** — ILIAS, Föderation (Plattform-Mission)

### 2.2 Abgeleitete UI-Ordnung („eine Seite pro Phase, eine Navigation entlang des Prozesses")

**Primärer Pfad (der normale Nutzer-Workflow):**

```
PROJEKT ANLEGEN → DATEIEN HOCHLADEN → (Ingest+Metadaten-KI läuft)
→ ANALYSE STARTEN → ERGEBNISSE ANSEHEN (Statistik/NN/Kalibration/Similarität)
→ KALIBRATION PRÜFEN (RMSECV/RPD) → FREIGEBEN → REPORT
```

Der **Projekt-Workflow deckt Phase 1–6 bereits vollständig ab** —
Projekt-Detail ist das organisierende Zentrum. Die Spektren-Seite ist
ein **Sonderweg** (Einzelmessung ohne Projektkontext) und gehört
nachgelagert/sekundär, nicht als verwaiste Parallelwelt.

**Sekundäre Pfade:**
- **Referenz-DB** (Phase 5-Vorbereitung): Import + Browse, gehört zur
  Kalibration/Vergleichs-Phase in der Navigation.
- **Sensoren/DIY** (Vor-Phase 1): Wissensbasis, korrekt heute.
- **ILIAS/Federated** (Phase 7): korrekt heute.

### 2.3 Ziel-Navigation (7 Punkte, entlang des Fachprozesses)

| # | Nav-Punkt | URL | Phase |
|---|---|---|---|
| 1 | **Start** | `/dashboard/` | Übersicht + Einstieg „Neues Projekt" |
| 2 | **Projekte** | `/projects/` | 1–6 (Kernprozess) |
| 3 | **Kalibration & Datenbank** | `/calibration/` (+ DB-Tab) | 4–5 |
| 4 | **Einzel-Spektren** | `/spectra/` | 1–3 (Schnell-Check ohne Projekt) |
| 5 | **Sensoren** | `/projects/sensors/` | 0 |
| 6 | **Lernen (ILIAS)** | `/ilias/` | 7 |
| 7 | **Admin/Diagnose** (nur Staff) | Agents/Jobs/Settings | Betrieb |

Chatbot wird **kontextuell** in Analyse-Ergebnis und Projekt-Report
eingebettet (sein Zweck ist „Ergebnisse diskutieren", MO 10) statt
als einsame Seite.

---

## Experte 3: UI-/Usability-Entwurf

### 3.1 Design-Grundsätze

1. **Eine Aktion — ein Label — ein Ort.** „Analyse starten" heißt überall
   so und lebt dort, wo der Kontext ist.
2. **Sichtbarer Workflow statt Feature-Inseln:** Der Nutzer sieht in der
   Navigation, wo er im Prozess ist (nummerierte Phasen im Header).
3. **Keine Sackgassen:** Jede Seite zeigt den nächsten Schritt („Analyse
   abgeschlossen → Ergebnisse ansehen / Kalibration prüfen").
4. **Feedback mit Konsequenz:** Nach jeder Aktion weiß der Nutzer, was
   passiert ist UND wohin er jetzt geht.
5. **Wissenschaftliche Integrität sichtbar:** Einheiten immer an der
   Achse, Provenance immer am Datensatz, RMSECV/RPD immer bei R².

### 3.2 Seiten-Entwurf (Redesign je Seite)

**Start (`/dashboard/`) — die fehlende Landkarte:**
- Große Kachel „**Neues Projekt** starten" (Wizard: Name → Dateien →
  Metadaten-Check → Analyse) als Primäraktion
- „Meine letzten Projekte" (mit Status-Chip: In Vorbereitung / Analysiert /
  Freigegeben)
- Sekundär: „Referenz-Spektrum importieren", „Schnell-Check eines
  Spektrums" (→ /spectra/)
- Systemstatus (Ollama/Qdrant erreichbar) dezent unten

**Projekt-Detail — Prozesssteuerung als Zeitachse:**
- Horizontaler Phasen-Indikator: Dateien → Qualität → Analyse →
  Kalibration → Freigabe/Report (erledigte Phasen grün, aktuelle
  hervorgehoben, künftige ausgegraut mit Klartext was fehlt)
- Pro Phase ein klarer Primär-Button („Analyse starten", „Projekt
  freigeben", „Report erzeugen") + Ergebnis-Vorschau in der Phase

**Einzel-Spektren (`/spectra/`) — ehrlicher Schnell-Check:**
- Umbenannt im Selbstverständnis: „Schnell-Check" (Einzelanalyse ohne
  Projektkontext, mit Hinweis „Für vollständige Analysen ein Projekt
  anlegen")
- Galerie mit **echter Kurve** (nie Fake, Empty-State mit Klartext)
- Ein Button je Karte: „**Analyse starten**" — danach sichtbarer
  Ergebnisbereich auf derselben Seite (nicht Redirect auf eine
  ungelinkte Seite): Metadaten-Qualität, Spektrum, Ausreißer-Verdict
- Die „Analyze Now"-Quick-Kachel entfällt (doppelt zur Karte)

**Kalibration & Datenbank (`/calibration/`):**
- Zwei Tabs: „Kalibrationen" (Tabelle mit R²/RMSECV/RPD, Sortierung,
  Farbcodierung nach RPD-Güte: >5 grün, 3–5 gelb-grün, 2–3 gelb, <2 rot)
  und „Referenzspektren" (heutige DB-Seite inkl. Import-Card)

**Chatbot (MO 10):**
- Eingebettet als Panel/Split-View im Analyse-Ergebnis und Projekt-Report
  („Ergebnisse mit dem Assistenten diskutieren") — Kontext wird
  mitgegeben; die Solo-Seite bleibt als Fallback.

**Entfall/Rückbau:**
- `/files/` (Generisch-Seite ohne Rolle) → aus Navigation/Bestand, falls
  kein Use Case; Funktion bleibt über Projekt-Dateien
- workflow_list/workflow_results-Templates → Löschenkandidaten (CI prüfen)

### 3.3 Konsistenz-Regeln (sofort umsetzbar)

| Regel | Umsetzung |
|---|---|
| Einheitliche Labels | „Analyse starten", „Referenz importieren", „Report erzeugen" — überall identisch |
| Sprache | UI vollständig Deutsch (i18n-Kataloge de/en vorhanden; `{% trans %}` konsequent) |
| Navigation | 7-Punkte-Header (Experte 2), aktiver Zustand, nummerierte Phasen auf Projektdetail |
| Buttons | Primäraktion grün gefüllt, Sekundär outline, destruktiv rot mit Bestätigung |
| Feedback | Toast + Ziel-Hinweis („Analyse gestartet → Ergebnisse in 2–5 Min hier") |
| Verwaiste Seiten | `/analysis/`, `/jobs/`, `/agents/` unter „Diagnose" (Staff-only) verlinken |

---

## Umsetzungsplan (Vorschlag, priorisiert)

| Schritt | Inhalt | Aufwand |
|---|---|---|
| S1 | Navigation auf 7-Punkte-Schema umbauen, `/dashboard/` als Start (`/` → Dashboard), `/spectra/` + Diagnose-Seiten verlinken | klein |
| S2 | Label-Konsistenz: „Analyse starten" überall (inkl. „Analyze Now"-Kachel entfernen), Deutsch durchgängig | klein |
| S3 | Spektren-Seite: Ergebnis-Panel auf derselben Seite statt Redirect auf `/analysis/` | mittel |
| S4 | Projekt-Detail: Phasen-Zeitachse + je-Phase-Buttons/Ergebnisse | mittel-groß |
| S5 | Kalibration: Tabs + RPD-Farbcodierung | klein |
| S6 | Chatbot-Kontexteinbettung in Analyse/Report | mittel |
| S7 | Rückbau `/files/` + Workflow-Leichen (nach CI-Check) | klein |
| S8 | Async-Analyse (Jobs-Seite als Fortschritts-Ort, Upload nie blockierend) — wie bereits geplant | groß |

Jeder Schritt separat testbar und rollback-fähig; S1+S2+S5 zuerst, da sie
das Nutzererlebnis sofort und risikoarm ordnen.

---

## Offene Fragen an den Product Owner

1. Einverstand mit 7-Punkte-Navigation und Dashboard-als-Start?
2. `/files/` wirklich rückbaubar (oder gibt es Nutzer mit Direkt-Links)?
3. Priorität S4 (Projekt-Phasenansicht) vor oder nach S8 (Async)?
