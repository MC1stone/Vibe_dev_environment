# 📖 Einführung: NIR Intelligence Platform (NIR-IP)

> Eine verständliche Einführung in das Projekt und seine Vorzüge.
> Verbindliche Details stehen in `MISSION_STATEMENT.md`, `AGENTS.md` und
> `REPOSITORY_ALIGNMENT_AND_ROADMAP.md`.

## Worum geht es in diesem Projekt?

**NIR-IP** ist eine vollständig **lokale, containerisierte und selbstoptimierende
Softwareplattform** zur Auswertung von **Nahinfrarot-Spektroskopie-Daten (NIR)**.

**Einfach erklärt:** Ein Spektrometer "schießt" Licht auf eine Probe (z. B. eine
Tomate, Getreide, Boden) und misst, wie viel Licht bei jeder Wellenlänge
zurückkommt. Dieses Spektrum ist wie ein "Fingerabdruck" der Probe. Mit passenden
Kalibrationsmodellen kann man daraus z. B. **Zuckergehalt (Brix), Feuchte oder
Frische** berechnen — ganz ohne Zerstörung der Probe. Genau diesen Weg vom
Rohdatensatz bis zum belastbaren Ergebnis automatisiert diese Plattform.

## 🏗️ Wie ist das Repository aufgebaut?

```
Vibe_dev_environment/
├── MISSION_STATEMENT.md                    → Mission, Ziele, Agenten-Rollen
├── AGENT_FRAMEWORK_INIT_PROMPT.md          → Verbindliche Regeln für KI-Sessions
├── REPOSITORY_ALIGNMENT_AND_ROADMAP.md     → Ist-Aufnahme + Entwicklungs-Roadmap (S1–S9)
├── AGENTS.md                               → Einstiegsregeln (wird automatisch gelesen)
└── NIR_Intelligence-main/                  → ★ Das eigentliche Projekt (Single Source of Truth)
```

`NIR_Intelligence-main/` enthält die komplette Plattform: **25+ spezialisierte
KI-Agenten**, einen **Docker-Compose-Stack** (PostgreSQL, Qdrant, FAISS, Ollama,
Redis, Flower, ILIAS …), ein **Django-Backend mit APIs und Web-UI**, Tests,
Deployment-Guides (Docker, Ansible, Produktion) und die Steuerdateien `TASK.md`,
`task_definition.yaml` und `system_manifest.json`, die jede KI-Session vor der
Arbeit einlesen muss.

## 🔄 Der Arbeitsablauf (Pipeline)

```
Rohdaten ( beliebiges Format )
   ↓  Import + automatische Metadaten-Erkennung
   ↓  Datenqualität & Sensorfehler-Erkennung (Drift, Rauschen)
   ↓  Analyse — zwei Wege, IMMER parallel:
   │     • Statistisch: PCA, PLS, PCR, ANOVA, Clustering
   │     • Neuronal: CNN, MLP, Autoencoder, Ensembles
   ↓  Kalibration erstellen & optimieren (PLS, SVM, Random Forest, XGBoost, CNN)
   ↓  Ähnliche Spektren finden (FAISS) & semantische Suche (Qdrant)
   ↓  Chatbot zur Ergebnisdiskussion (Ollama/Mistral, lokal)
   ↓  Automatischer Bericht (Quarto)
   ↺  Iteration, bis ERRORS = 0, CRITICAL_WARNINGS = 0, offene Change Requests = 0
```

## 🤖 Das Agentensystem

Statt einem monolithischen Programm arbeitet die Plattform mit **spezialisierten
Agenten**, die von einem Master-Orchestrator koordiniert werden — wie ein
Expertenteam:

| Agent | Aufgabe |
|---|---|
| **Master Agent** | Planung, Orchestrierung, Qualitätskontrolle, Freigaben |
| **Data Preparation** | Import, Bereinigung, Ausreißeranalyse, Normalisierung |
| **Sensor Quality** | Driftanalyse, Rauschbewertung, Instrumentenüberwachung |
| **Statistical / Neural Network** | Die beiden parallelen Analyse-Säulen |
| **Calibration** | Kalibrationsmodelle erstellen und optimieren |
| **Metadata** | Metadaten extrahieren, bewerten, priorisieren |
| **Qdrant / FAISS** | Vektor-/Embedding-Speicherung, Spektrenvergleich, Similarity Search |
| **Chatbot** | Ergebnisse diskutieren (RAG auf Analyseergebnissen) |
| **Django** | UI, APIs, Benutzerverwaltung |
| **Flower** | Federated Learning (datenschutzfreundliches, verteiltes Training) |
| **Quarto** | Automatisierte Berichte und Diagramme |
| **ILIAS** | Lernszenarien für die e-learning-Plattform |

## ✨ Die Vorzüge des Projekts

1. **🔍 Vollständig – alles aus einer Hand:** Von Rohdaten bis zum dokumentierten
   Bericht; statistische und neuronale Analyse laufen *vorgeschrieben parallel*
   und werden verglichen — so wird keine Methode blind vertraut.

2. **🏠 100 % lokal und datenschutzfreundlich:** Keine Cloud. Die KI
   (Ollama mit Mistral) läuft lokal, Daten verlassen das Netz nicht — ideal für
   sensible Labor- und Forschungsdaten. Federated Learning ermöglicht sogar
   standortübergreifendes Modelltraining *ohne* Rohdaten-Austausch.

3. **📁 Format- und geräteunabhängig:** SPC (binäres Thermo/Galactic-Format),
   MATLAB, CSV/TXT/JSON, JMP-Exporte u. a. werden über eine erweiterbare
   Importschicht unterstützt. Neue Spektrometer (z. B. ESP32-S3, SparkFun Triad,
   DIY-Geräte) integrieren sich über ein einheitliches Adapter-Muster — ganz ohne
   Änderung am Plattform-Kern.

4. **🔁 Selbstoptimierend mit klarem Qualitätsziel:** Die Plattform iteriert
   (Analyse → Evaluation → Optimierung → Reanalyse), bis messbar **0 Fehler,
   0 kritische Warnungen und 0 offene Change Requests** erreicht sind — und
   überwacht laufend die Open-Source-Abhängigkeiten auf Aktualisierbarkeit.

5. **🐳 Reproduzierbar & deploymentfertig:** Der komplette Stack läuft über
   Docker-Compose (Dev & Prod inkl. Healthchecks); Ansible-Playbooks und
   Produktionsskripte liegen bei. Ein einziger Befehl startet alles.

6. **🤝 KI-gesteuerte, aber disziplinierte Entwicklung:** `AGENTS.md` +
   Init-Prompt erzwingen bei *jeder* KI-Session ein festes Protokoll
   (Startdateien lesen, Selbstprüfung, Anti-Code-Creep: kleinste korrekte
   Lösung, keine unnötigen Abhängigkeiten). Das Repository bleibt sauber und
   wartbar — belegt durch die sauber dokumentierte Roadmap (S1–S9 erledigt,
   inkl. Testabdeckung von inzwischen 332 Tests).

7. **💬 Ergebnisdiskussion mit Chatbot:** Ein RAG-Chatbot auf Basis der eigenen
   Analyseergebnisse und Dokumentation erlaubt es, Befunde in natürlicher
   Sprache zu hinterfragen — ein großer Vorteil für Nicht-Programmierer:innen.

8. **🎓 Bildungsintegration:** ILIAS-Anbindung und Lernpfade machen die
   Plattform auch für die Lehre nutzbar (Hochschulkontext: HSWT).

## 🚀 Schneller Einstieg

```bash
cd NIR_Intelligence-main
docker-compose up -d          # Startet den gesamten Stack
./quickstart.sh 8001          # Oder: Django-Server direkt starten
# → Dashboard: http://localhost:8001/dashboard/
```

**Kurz gesagt:** NIR-IP ist ein durchstrukturiertes, lokales KI-Ökosystem, das
den kompletten NIR-Analyseprozess automatisiert — robust, nachvollziehbar und
ohne Cloud-Zwang — und sich dabei aktiv selbst überwacht und verbessert.
