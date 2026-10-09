# Validierungsplan: Heutiger Funktionsumfang (2026-10-08)

Status: Entwurf fuer den Start morgen (vom User freigegebenes Vorgehen)
Basis: Live-Feedback des Users auf dem Kaffee-Projekt; teilweise
Identifizierte Lücken sind im Branch `vibe/kaffee-ausreisser-konfusionsmatrix-43d0d0`
vorbreitet (classification_samples, WIP - siehe V1.1).

---

## Heute gebaut (Merge-Stand)

| # | Funktion | PR | Status |
|---|---|---|---|
| 1 | Struktur-Klaerungsdialog Stufe B (KI + gelernte StructureProfile) | #133 | merged |
| 2 | 7z-Archiv-Support + Modal-Reset | #134 | merged |
| 3 | DisallowedHost-Fix (django-app Alias) | #135 | merged |
| 4 | Upload-Robustheit (media-Dirs, UID 1000) | #136 | merged |
| 5 | mime_type-IntegrityError-Fix (Upload) | #137 | merged |
| 6 | Button-Feedback (Speichern/Reingest) | #138 | merged |
| 7 | Versuchskontext (experiment_name/purpose) + Klassifikations-Erkennung | #139 | merged |
| 8 | Agenten-gesteuerte Klassifikation (LDA/kNN, yaml) | #140 | merged |
| 9 | Iterations-Evaluation + Iterationsplan im Bericht | #141 | merged |
| 10 | Kaffee-Fix: classification_samples (alle Zeilen) | Branch | **WIP - morgen fertigstellen** |

## Bekannte, noch offene User-Befunde (Prioritaet morgen)

- **A. Ausreisser-Analyse lief nicht** (Report: keine Ausreisser-Sektion-
  Ergebnisse): `measurement_samples` = Replica-Block; bei
  Messobjekt-wechselnden Datensaetzen (Kaffee: 451 Messungen) ist der
  Block winzig -> "zu wenige Messungen".
  -> **Fix-Richtung:** Ausreisser-Analyse auf ALLE Messreihen ausweiten
  (nicht nur Replicas), wenn kein Replica-Block vorliegt.
- **B. Keine Konfusionsmatrix im Report**: (a) classification_samples
  fehlten (Branch vorbereitet: alle Zeilen mit Label, gecappt 2000);
  (b) supervised_context muss classification_samples bevorzugen;
  (c) Konfusionsmatrix muss im Report gerendert werden
  (HTML-Tabelle, Klassen x Klassen).
- **C. "Eigen"-Werte im Report** (PCA-Scree): Klartext-Beschriftung +
  Erklaerung fehlt (Triage-Punkt von heute Mittag).

---

## Validierungsplan morgen (Reihenfolge)

### Stufe 0 - WIP-Branch fertigstellen (VOR den User-Tests)
1. classification_samples in supervised_context bevorzugen:
   `spectra` = classification_samples (bei classification) vor
   calibration_samples; class_labels aus classification_labels
   (zeilensynchron!), nicht aus metadata.class_labels (nur unique Liste).
2. Ausreisser-Analyse (A): `analyse_dataset` auf
   classification_samples/measurement_samples-Alternative erweitern -
   Fallback: alle Messreihen, wenn Replica-Block < MIN.
3. Konfusionsmatrix-Rendering (B): Report-Sektion fuer LDA-Ergebnis
   mit HTML/MD-Konfusionsmatrix-Tabelle + Klassenliste.
4. PCA-Scree-Beschriftung (C): "Eigenwert (erkltaerte Varianz je
   Hauptkomponente)" + Kurzerklaerung.
5. E2E-Tests: Kaffee-Struktur (3 Sorten x N) -> Ausreisser-Sektion
   vorhanden, LDA mit Konfusionsmatrix im gerenderten Report,
   class_labels laengensynchron.
6. Regressionstests: OP30/OP37/OP14/OP8 + Journal + Kalibration.
7. PR aufmachen, CI gruen, User mergt.

### Stufe 1 - Live-Validierung mit dem User (Kaffee-Projekt)
Der User fuehrt aus (wir begleiten jede Zeile):
1. `git pull` + `docker compose up -d` (kein Rebuild noetig - Python/
   Templates; Rebuild nur falls requirements geaendert).
2. Projekt Kaffee: **"Aufbereitung erneut ausfuehren"** (Button zeigt
   jetzt Feedback).
3. Pruefen: Metadaten-Editor zeigt experiment_name/purpose aus der
   Beschreibungsdatei (Fix 7); keine Zielwert-Frage mehr (Klassifikation).
4. **"Zur Analyse freigeben"** - Analyse laufen lassen.
5. Report pruefen gegen Checkliste (unten).

### Stufe 2 - Report-Checkliste (Abnahme pro Punkt)
| Pruefpunkt | Erwartung |
|---|---|
| Ausreisser-Analyse | Sektion mit allen Messungen bewertet, nicht "zu wenige Messungen" |
| Klassifikation | LDA + kNN Ergebnisse, CV-Genauigkeit je Sorte |
| **Konfusionsmatrix** | Tabelle Klassen x Klassen, sichtbar im HTML-Report |
| Agenten-Journal | Modus-Entscheidung dokumentiert ("classification erkannt") |
| Iterations-Evaluation | verdict + Stop-Bedingungen + ggf. Plan |
| Eigenwerte | Beschriftet + erklaert (kein kryptisches "Eigen") |
| Versuchskontext | experiment_name/purpose im Metadaten-Block |
| Brix-Projekt unbeeinflusst | Kalibration (PLS, RMSECV/RPD) laeuft weiter wie vorher |

### Stufe 3 - Cross-Validierung Brix (Regressionsschutz)
1. Brix-Projekt reingesten + freigeben.
2. Kalibrationsergebnisse unveraendert (R2/RMSECV/RPD);
   KEINE Klassifikations-Sektion; Zielwert-Frage wie bisher.

### Stufe 4 - Struktur-Dialog (Stufe B) Live-Nachweis
1. Eine absichtlich "unlesbare" Datei hochladen (z.B. umbenannte CSV).
2. Struktur-Dialog mit KI-Vorschlag bestaetigen.
3. Zweiter Upload desselben Formats: Profil wird automatisch angeboten
   (structure_learned=true) - Lern-Nachweis.

### Abnahme-Kriterium
Alle Checkpunkte Stufe 2 + 3 gruen; User bestaetigt
"vorgestern-Niveau plus" fuer Metadaten-KI UND die neuen Funktionen.

---

## Offene Punkte HINTERHER (nicht morgen, documented)
- S3/S4 Redesign (Spektren-Ergebnis-Panel, Projekt-Phasenansicht)
- S8 Async-Analyse
- Eigentliche Klassifikations-Modelle im NN-Agent (CNN-Klassifikator)
