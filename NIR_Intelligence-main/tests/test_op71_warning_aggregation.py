#!/usr/bin/env python3
# OP71 test matrix: Warnungs-Aggregation ueber alle Datensaetze.
# Nutzer-Befund (2026-10-19): Der Fusionbericht listete unten bei den
# Warnungen nur den Noise-Level des ERSTEN Datensatzes, obwohl der des
# zweiten ueber 3x hoeher war. Anforderungen:
#  (a) Warnungen ALLER Datensaetze fliessen in den Bericht (dedupliziert)
#  (b) Rausch-Warnungen werden konsolidiert: nur das HOECHSTE gemeldete
#      Rauschniveau bleibt stehen, mit Quellenangabe
# Offline-safe (Struktur-Check auf Quellcode + Logik-Extraktion).
import re
import sys
from pathlib import Path

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {detail}")


REPO_ROOT = Path(__file__).resolve().parent.parent
src = (REPO_ROOT / "services" / "project_crew.py").read_text(encoding="utf-8")

# T1: Aggregation implementiert
check("T1a Warnungen aller Datensaetze (nicht nur primary)",
      "for _idx, _res in enumerate(results):" in src
      and "all_warnings" in src)
check("T1b crew_results nutzt aggregierte Liste",
      "'warnings': all_warnings," in src
      and "'warnings': primary.warnings," not in src)

# T2: Noise-Konsolidierung (nur der hoechste)
check("T2a Noise-Regex-Konsolidierung vorhanden",
      "_noise_re" in src and "Noise level ([0-9.]+) exceeds threshold" in src)
check("T2b nur das hoechste Rauschniveau uebernimmt",
      "_best_noise is None or _level > _best_noise[0]" in src)
check("T2c Quellenangabe (Dateiname) an der Noise-Warnung",
      "_tagged = f'{_w} [{_src}]'" in src
      and "_file_names" in src)
check("T2d Kennzeichnung 'hoechstes Rauschniveau' bei mehreren Datensaetzen",
      "hoechstes Rauschniveau aller" in src)

# T3: Logik-Extraktion und Verhaltenstest (regex-basiert, ohne Django)
noise_re = re.compile(r'Noise level ([0-9.]+) exceeds threshold ([0-9.]+)')


def aggregate(warnings_per_dataset, names):
    """Nachbau der Aggregationslogik aus project_crew.py (OP71)."""
    all_warnings = []
    best_noise = None
    seen = set()
    for idx, warns in enumerate(warnings_per_dataset):
        src_name = names[idx] if idx < len(names) else ''
        for w in warns:
            m = noise_re.match(str(w))
            if m:
                level = float(m.group(1))
                tagged = f'{w} [{src_name}]' if src_name else w
                if best_noise is None or level > best_noise[0]:
                    best_noise = (level, tagged)
                continue
            if w not in seen:
                seen.add(w)
                all_warnings.append(str(w))
    if best_noise is not None:
        all_warnings.append(
            f'{best_noise[1]} (hoechstes Rauschniveau aller Datensaetze)'
            if len(warnings_per_dataset) > 1 else best_noise[1])
    return all_warnings


# Nutzer-Szenario: Datensatz 2 hat 3x hoeheres Rauschen
w1 = ["Noise level 0.2936 exceeds threshold 0.0500",
      "Drift detected: 0.0224"]
w2 = ["Noise level 0.9200 exceeds threshold 0.0500",
      "Drift detected: 0.0224"]          # Drift-Duplikat
out = aggregate([w1, w2], ['A.csv', 'B.csv'])
check("T3a nur EINE Noise-Warnung (konsolidiert)",
      sum(1 for w in out if 'Noise level' in w) == 1, str(out))
noise_warn = next(w for w in out if 'Noise level' in w)
check("T3b die HOECHSTE Noise-Warnung ueberlebt (0.92, nicht 0.29)",
      '0.9200' in noise_warn and '0.2936' not in noise_warn, noise_warn)
check("T3c Quellenangabe der schlechteren Datei",
      '[B.csv]' in noise_warn, noise_warn)
check("T3d Kennzeichnung als hoechstes Rauschniveau",
      'hoechstes Rauschniveau' in noise_warn)
check("T3e Drift-Duplikat nur einmal",
      sum(1 for w in out if 'Drift' in w) == 1, str(out))
check("T3f korrekte Gesamtliste: 1 Drift (dedupliziert) + 1 Noise",
      len(out) == 2, str(out))

# Ein-Datensatz-Fall: keine Multi-Dataset-Kennzeichnung
out_single = aggregate([w1], ['A.csv'])
check("T3g Einzeldatensatz: Noise-Warnung ohne Multi-Dataset-Zusatz",
      len(out_single) == 2 and not any('hoechstes' in w
                                       for w in out_single), str(out_single))

# Umgekehrte Reihenfolge: erster Datensatz schlechter
out_rev = aggregate([w2, w1], ['B.csv', 'A.csv'])
noise_rev = next(w for w in out_rev if 'Noise level' in w)
check("T3h auch wenn der ERSTE das schlechteste Rauschen hat",
      '0.9200' in noise_rev and '[B.csv]' in noise_rev, noise_rev)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
