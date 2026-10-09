# Workflow-Design: Projekt-Workflow mit sichtbarer Position und KI-Entscheidungspunkten

> **Einordnung:** Dieses Papier definiert den Projekt-Workflow (Stationen 1–6), die
> durchgängig sichtbare Workflow-Position und das Event-Muster für
> Nutzerentscheidungen, wenn ein Agent entscheidet, dass eine Nutzerentscheidung
> zu treffen ist. Es ist verbindliche Grundlage für die Umsetzung; Änderungen
> ergehen über den Head of Development (vgl. `AGENT_FRAMEWORK_INIT_PROMPT.md`
> §3.10 Workflow-Agent, §3.11 UI-Spezialist).
>
> **Anforderungsbezug:** Master Objectives 1, 2, 3, 4, 11, 13, 14
> (`MISSION_STATEMENT.md`); Roadmap-Abgleich über `REPOSITORY_ALIGNMENT_AND_ROADMAP.md`.

---

## 1. Workflow-Stationen

Der Workflow startet immer mit der Anlage eines Projekts. Die aktuelle Position ist
in der Projektansicht jederzeit über ein persistentes Workflow-Band (Stepper)
ersichtlich:

```
(1) Projekt anlegen ──> (2) Ingest & Datengrundlage ──> (3) Sensor-Zuordnung ──>
(4) Spektren-Abgleich ──> (5) Analyse-Zyklus ──> (6) Abschlussbericht
```

### Station 1 — Projekt anlegen
- **Mindestanforderungen:** Projektname + Bereitstellung eines Datensatzes.
- Erst wenn beide vorhanden sind, ist Station 2 erreichbar; die UI zeigt konkret,
  was fehlt (keine Dead Ends).

### Station 2 — Ingest & Datengrundlage
- Der file-typ-agnostische Data-Loader-Agent (Grundregel 1: **alle Dateiformate**,
  kein Hard-Coding) erzeugt mit KI-Unterstützung:
  - einen **Standard-Metadatensatz**,
  - eine **Tabelle der Spektraldaten**, die in den Dateien gefunden wurden.
- Die KI macht **Änderungs- und/oder Ergänzungsvorschläge**, um die Qualität der
  beiden Datensätze zu verbessern (Anknüpfung an das bestehende
  Vorbereitungs-Reporting der Phase 1, `django_project/api/project_views.py`).
- **Zwei-Fenster-Anforderung:** In zwei Fenstern wird jederzeit der aktuelle
  Datenbestand angezeigt — Fenster A: Metadaten, Fenster B: Spektraldatentabelle —
  jeweils mit Option zum **Anpassen**. Diese Ansicht bleibt über alle Stationen
  erhalten (permanente Sidebar), nicht nur in Station 2.

### Station 3 — Sensor-Zuordnung
- Sobald ein Sensor angegeben/hinzugefügt wurde, sucht die KI in der
  Sensordatenbank nach dem Sensor (Anknüpfung `services/sensor_catalog.py`,
  `match_model_id`).
- **Entscheidet** die KI, dass es Standardwerte gibt, die automatisch zugeordnet
  werden können, werden diese Werte dem Anwender **vorgeschlagen** mit der Option,
  sie **abzuändern** (Decision-Objekt, Abschnitt 3; Grundregel 2: **alle
  Spektrometer**, keine geräte-spezifische Hard-Codierung von Standardwerten).

### Station 4 — Spektren-Abgleich
- Sobald aus den Daten ein Spektrum erstellt werden kann, wird die
  Spektrendatenbank auf **vergleichbare Spektren** geprüft (FAISS-Agent).
- Werden Treffer gefunden, werden diese **mit ihren Metadaten in einem
  Vergleichsfenster** dem Nutzer angezeigt.
- **Shortcut:** Der Nutzer kann hier entscheiden: „Das ist genau das, was ich
  gemessen habe (z. B. BRIX)" — dann lässt er seinen Datensatz mit dem
  vorhandenen Modell bewerten und überspringt den vollen Analyse-Zyklus.
- Andernfalls startet er, nachdem die Daten für ihn schlüssig präsentiert wurden,
  den **Analyse-Zyklus**.

### Station 5 — Analyse-Zyklus
- Wie in der Software vorgesehen (NIRAnalysisCrew, iterativ bis alle Agenten
  fehlerfrei sind; Neural Network Agent verpflichtend parallel zur statistischen
  Analyse).

### Station 6 — Abschlussbericht
- Der Abschlussbericht wird final wie in der Software vorgesehen erstellt
  (Quarto/HTML): **alle iterativen Schritte werden nachvollziehbar dargestellt**,
  inklusive der Nutzer-Entscheidungen dazwischen (Quelle: das Decision-Log,
  Abschnitt 3c).

### Stations-Zustände
Jede Station führt einen Zustand: `offen / in_arbeit / wartet_auf_nutzer /
erledigt`. Der Ist-Marker des Steppers ergibt sich aus den Stationszuständen.
Als Minimum first-class-content ist die Station-Konstante zu prüfen; die
persistente Ablage erfolgt im laufenden Projekt (analog zum bestehenden
Phasenmodell `drafted/released/completed` in `project_views.py`, das erhalten
bleibt und durch die Stationszustände verfeinert, nicht ersetzt wird).

---

## 2. Workflow-Position (Stepper)

- Persistentes Workflow-Band in der Projektansicht (alle Projektseiten), mit
  klarem Ist-Marker und Stationszuständen.
- **Keine Dead Ends:** Wartet der Workflow auf den Nutzer, zeigt die Station
  „wartet auf Ihre Entscheidung" — jederzeit ersichtlich, warum nichts
  weiterläuft.
- **Rückkehr erlaubt:** Jede abgeschlossene Station bleibt anwählbar und
  anpassbar (Verallgemeinerung des bestehenden „Reingest zurück in Draft"-
  Musters). Eine Änderung erzeugt ein neues Decision-Objekt an der Folgestation,
  statt Fortschritt zu löschen.

---

## 3. Event-Muster: „Nutzerentscheidung erforderlich"

Drei Komponenten: **Decision-Objekt**, **Wartezustand**, **Entscheidungslog**.

### a) Decision-Objekt
Jede anstehende Nutzerentscheidung ist ein first-class, persistentes Objekt:

```yaml
decision:
  id: "dec-<workflow_id>-<seq>"
  project: "<projektname>"
  station: 3                      # Sensor-Zuordnung
  question: "Für Sensor 'X' wurden Standardwerte gefunden. Übernehmen?"
  options:
    - id: accept
      label: "Standardwerte übernehmen"
      effect: sensor_defaults_applied
    - id: modify
      label: "Werte abändern"
      effect: opens_inline_editor
    - id: decline
      label: "Nicht übernehmen"
      effect: manual_entry_required
  ki_basis: "Sensordatenbank-Eintrag #4711, Konfidenz 0.9"
  created_at: "<ISO-8601>"
```

- Es gibt immer mindestens zwei Optionen; **keine Option ohne definiertes
  Weiterkommen** (keine Sackgassen-Optionen).
- `modify` öffnet einen Inline-Editor im Kontext der Station — kein Sprung auf
  eine andere Seite.

### b) Wartezustand `AWAITING_DECISION`
- Erweitert `WorkflowStatus` im Workflow-Orchestrator um
  `AWAITING_DECISION = "awaiting_decision"`.
- Der Workflow geht **nicht** in FAILED/PENDING, sondern in den expliziten
  Wartezustand mit Referenz auf das(n) offene(n) Decision-Objekt(e).
- Der Workflow läuft nach jeder Entscheidung automatisch weiter: der
  Orchestrator liest beim Weiterlaufen das Decision-Log.

### c) Decision-Log (append-only)
- Jede getroffene Entscheidung wird append-only geloggt:
  `decision_id, option_id, ggf. geänderte Werte, timestamp, workflow_snapshot`.
- **Zweck:**
  1. Der Workflow fährt nach jeder Entscheidung automatisch fort — der Agent muss
     nie „warten" implementieren.
  2. Station 6 bekommt die vollständige Nachvollziehbarkeit: „Station 3: KI
     schlug Standardwerte vor (Basis: Sensordatenbank #4711) → Nutzer übernahm
     sie unverändert."
  3. Mehrere offene Entscheidungen sind möglich (Queue); der Stepper zeigt
     „N Entscheidungen offen".

### UI-Muster des Events
- **Kein blockierender Modal-Dialog** (erzeugt Sackgassen): stattdessen eine
  **Entscheidungsleiste** am oberen Rand der Projektansicht:
  „⚠️ N Entscheidungen offen — [Sensor-Standardwerte] …" mit Badge an der
  betroffenen Station.
- Klick springt zur Station und klappt das Decision-Panel inline auf
  (Vorschlag + KI-Basis + Optionen).
- Nach Wahl: kurzes Feedback („Standardwerte übernommen"), Station wird grün,
  Workflow läuft weiter.
- Der Shortcut in Station 4 ist semantisch dasselbe Muster: Decision-Objekt mit
  Option `use_existing_model` — dadurch landet auch der Shortcut zuverlässig im
  Abschlussbericht.

### Zusatzregeln gegen Dead Ends
- **Escalation statt Timeout:** Nach hinreichend langer Zeit ohne Entscheidung
  erzeugt das System eine Erinnerung (Dashboard/Toast); es bricht **nie** ab und
  setzt **nie** stillschweigend etwas voraus.
- **Vorschlag ist nie Zwang:** Jedes Decision-Objekt enthält immer eine Option,
  den Vorschlag abzulehnen, mit definiertem Weiterkommen.

---

## 4. Umsetzungsreihenfolge (kleinste korrekte Schritte)

1. `WorkflowStatus.AWAITING_DECISION` + Decision-Objekt/-Log im
   Workflow-Orchestrator (`agents/workflow_orchestrator.py`) — Grundlage.
2. Persistenz der Stationen/Entscheidungen im Projektmodell (Django) — Ausbau.
3. Stepper-UI + Entscheidungsleiste (Django-Templates) — Ausbau.
4. Verankerung der Stationen 3/4-Logik (Sensor-Vorschlag, FAISS-Abgleich mit
   Shortcut-Option) in den Agenten — Ausbau.
5. Abschlussbericht: chronologische Decision-Log-Sektion — Ausbau.

Jeder Schritt folgt Anti-Code-Creep: kleinste korrekte Lösung, Anforderungsbezug
je Änderung, keine neuen Abhängigkeiten.
