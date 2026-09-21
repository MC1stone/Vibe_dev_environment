# AGENTS.md — Verbindliche Einstiegsregeln für jede KI-Session in diesem Repository

> Diese Datei wird automatisch bei Session-Beginn gelesen. Sie verpflichtet jede KI
> (und jeden Agenten), **vor jedem Entwicklungsschritt** die folgenden Steuerdateien
> vollständig zu lesen, zu analysieren und entsprechend umzusetzen:

1. **`AGENT_FRAMEWORK_INIT_PROMPT.md`** — Initialisierung des Development Agent
   Frameworks: Agenten-Rollen, Initialisierungsprotokoll (8 Schritte),
   Anti-Code-Creep-Regeln, Definition of Done, Selbstprüfung (§7).
2. **`MISSION_STATEMENT.md`** — Mission und Master Objectives der NIR Intelligence
   Platform (NIR-IP), Technologie-Stack, verpflichtende Startsequenz
   (`TASK.md`, `task_definition.yaml`, `system_manifest.json` — aktuell unter
   `NIR_Intelligence-main/`), Agentensystem, Iterationsregel, Abschlussbericht.
3. **`REPOSITORY_ALIGNMENT_AND_ROADMAP.md`** — Abgleich des Mission Statements mit
   dem Repository-Stand (Lücken G1–G8) und Planung der Entwicklungsschritte (S1–S9).

## Nicht verhandelbare Regeln

- **Keine Implementierung**, bevor das Initialisierungsprotokoll (§2 des Init-Prompts)
  durchlaufen und die schriftliche Selbstprüfung (§7) beantwortet ist.
- **Jeder Entwicklungsschritt muss Teil der Roadmap (S1–S9) sein.** Andernfalls: erst
  Freigabe durch den Head of Development und Roadmap-Update, dann Umsetzung.
- **Alle Dateiformate und alle Spektrometer unterstützen** — kein Hard-Coding von
  Formaten oder Geräten (Grundregeln im Init-Prompt, §1).
- **Weaviate ist out of scope** — Qdrant ist der Ersatz für Vektor-/Embedding-Speicherung.
- **Anti-Code-Creep:** Kleinste korrekte Lösung, Anforderungsbezug für jede Änderung,
  keine neuen Abhängigkeiten ohne zwingende Notwendigkeit, fokussierte Commits.
- **Iterationsregel:** Der Zyklus läuft bis `ERRORS = 0`, `CRITICAL_WARNINGS = 0`,
  `OPEN_CHANGE_REQUESTS = 0`.

## Führendes Projekt

`NIR_Intelligence-main/` ist die Single Source of Truth der Plattform. Die Verzeichnisse
`nir_platform/`, `HANDHELD/` und `framework/` werden gemäß Roadmap (S1) behandelt
(integrieren / einfrieren / als Referenz deklarieren) — nicht parallel weiterentwickeln.

## Kurzanleitung für den Session-Start

```text
1. AGENT_FRAMEWORK_INIT_PROMPT.md lesen
2. MISSION_STATEMENT.md lesen → Startsequenz einlesen
   (NIR_Intelligence-main/TASK.md, task_definition.yaml, system_manifest.json)
3. REPOSITORY_ALIGNMENT_AND_ROADMAP.md lesen → betroffenen Schritt (S1–S9) identifizieren
4. Schriftliche Selbstprüfung (§7, 7 Fragen) beantworten und zeigen
5. Erst danach: Implementierung gemäß Head-of-Development-Freigabe
```
