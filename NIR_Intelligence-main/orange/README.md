# Orange-Workflow: Tomaten NIR Brix Analyse

## Inhalt

| Datei | Beschreibung |
|---|---|
| `tomato_nir_brix_analysis.ows` | Fertiger Orange-Workflow (23 Widgets, 28 Verbindungen) |
| `tomato_nir_brix.tab` | Bereinigter Datensatz im Orange-eigenen Format (2014 Messungen, 40 Tomaten, 18 Kanäle 410–940 nm, °Brix als Zielvariable) |

## Nutzung

1. Orange 3.38+ installieren (https://orangedatamining.com).
2. Beide Dateien in **denselben Ordner** legen (das File-Widget referenziert `tomato_nir_brix.tab` relativ zum Workflow-Ordner, Prefix `basedir`).
3. `tomato_nir_brix_analysis.ows` per Doppelklick oder **File → Open** in Orange öffnen.
4. Bei Bedarf im File-Widget den Pfad einmalig neu wählen, falls Orange den Ordner nicht erkennt (dann einmal speichern, damit `basedir` neu gesetzt wird).

## Aufbau des Workflows

```text
File ──► Preprocess (Standardisieren) ──► Select Columns (18 Kanäle als Features, Brix als Ziel)
                                              │
        ┌─────────────────────────────────────┼──────────────────────────────┐
        ▼                                     ▼                              ▼
  Line Plot / Box Plot              PCA ──► Scatter Plot            Correlations
  Distributions / Feature Stats            Distances ──► Hierarchical Clustering (Ward)
        │
        ▼
  Python Script (Qualität: Rauschen, Drift, SNR, Ampel-Score)
  Python Script (XAI: Permutationswichtigkeit der Kanäle)
  Python Script (FAISS: Top-3 ähnlichste Spektren; benötigt pip install faiss-cpu)
        │
        ▼
  PLS (9 Komponenten) ─┐
  Neural Network ─────┤──► Test and Score (5-fach Kreuzvalidierung) ──► Predictions
  Linear Regression ──┘         │
                        Permutation Plot
```

## Datenhintergrund

- Quelle: `data/raw/T4-T5_ALLE_mit_Brix_2.txt` (Versuch „Tomaten Reifegradbestimmung", Dpark fun NIR Triad)
- Bereinigt wie in der Skript-Analyse: 31 ADC-Überläufe (Kanäle F_535/R_610) und 4 Null-Messungen (I_645/K_900) entfernt → 2014 von 2049 Messungen
- Zielvariable: °Brix (Refraktometer-Referenz, 4.32–8.1)
- Metadaten als Orange-Metas: Messobjekt, Kurz, Tomate, Rispe, Reihe, Tag, Temp0–2

## Erneutes Erzeugen

```bash
python3 scripts/make_orange_dataset.py   # erzeugt tomato_nir_brix.tab
python3 scripts/make_ows_workflow.py     # erzeugt tomato_nir_brix_analysis.ows
```
