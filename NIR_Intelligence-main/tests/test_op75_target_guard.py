#!/usr/bin/env python3
# OP75 test matrix: Zielwert-Guard - das erkannte Messziel (Brix) darf
# den Analysemodus bestimmen; numerische Pseudo-Kategorien (Temp0) sind
# KEINE Klassen-Labels, wenn ein Kalibrationsziel existiert. Die
# Beobachtung wird als offene KI-Frage IN DER APP sichtbar gemacht
# (Nutzer-Befund 2026-10-20: Temp0 kaperte den Modus still, keine
# Meldung, 0 Kalibrationszeilen).
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "django_project"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")

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


try:
    import django
    django.setup()
    check("T0a django setup", True)
except Exception as exc:
    check("T0a django setup", False, str(exc))
    sys.exit(1)

from django.conf import settings as dj_settings  # noqa: E402
dj_settings.DATABASES["default"]["NAME"] = ":memory:"
from django.core.management import call_command  # noqa: E402
call_command("migrate", interactive=False, verbosity=0)

import uuid  # noqa: E402
from services.project_ingest import ingest_file  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


class _Rec:
    def __init__(self, path, name, fid):
        self.id = fid
        self.name = name
        self.file_extension = 'csv'
        self.file_category = 'raw'
        self._p = str(path)

    def get_file_path(self):
        return self._p


def _ingest(path, name='test.csv'):
    entries = ingest_file(_Rec(path, name, str(uuid.uuid4())))
    if isinstance(entries, dict):
        entries = [entries]
    return entries[0] if entries else {}


# ---------------------------------------------------------------------------
# T1: Nutzer-Szenario nachgebaut - Brix-Ziel + numerische Pseudo-Kategorie
# ---------------------------------------------------------------------------
import tempfile  # noqa: E402
import pandas as pd  # noqa: E402

rows = 240
rng = pd.Series(range(rows))
csv_a = pd.DataFrame({
    'Messobjekt': [f'{1000 + i // 30}' for i in range(rows)],
    'Brix': [4.0 + (i % 33) * 0.1 for i in range(rows)],
    'Temp0': [28 + (i % 3) for i in range(rows)],   # Pseudo-Kategorie!
    **{f'{c}_{w}': [100.0 + j + (i % 7) for i in range(rows)]
       for j, (c, w) in enumerate(zip(
           'ABCDEFGHIJKL', (410, 435, 460, 485, 510, 535, 560, 585,
                            610, 645, 680, 705)))},
})
with tempfile.NamedTemporaryFile(suffix='.csv', delete=False,
                                 mode='w', encoding='utf-8') as tf:
    csv_a.to_csv(tf.name, sep=';', index=False)
    path_a = tf.name

e = _ingest(path_a)
meta = e.get('metadata') or {}
check("T1a Brix als Ziel erkannt", meta.get('target_name') == 'Brix',
      str(meta.get('target_name')))
check("T1b Analysemodus regression (trotz Temp0-Kategorie-Kandidat)",
      meta.get('analysis_mode') == 'regression',
      str(meta.get('analysis_mode')))
check("T1c Temp0 NICHT als Klassen-Label",
      meta.get('class_label_column') is None,
      str(meta.get('class_label_column')))
oq = [str(q) for q in (e.get('open_questions') or [])]
check("T1d Meldung in der App (offene KI-Frage zur Pseudo-Kategorie)",
      any('Messziel' in q and 'Klassen-Label' in q for q in oq),
      str(oq)[:200])
check("T1e Kalibrationszeilen erzeugt",
      len(e.get('calibration_samples') or []) >= 50,
      str(len(e.get('calibration_samples') or [])))
check("T1f Referenzwerte = Brix je Zeile",
      len(e.get('reference_values') or [])
      == len(e.get('calibration_samples') or []))

# T2: echter Klassifikationsfall bleibt unberuehrt (kein Zielwert,
# Text-Label-Spalte = Kaffeesorte)
csv_b = pd.DataFrame({
    'Sorte': ['Arabica'] * 60 + ['Robusta'] * 60,
    **{f'{c}_{w}': [100.0 + j + (i % 9) for i in range(120)]
       for j, (c, w) in enumerate(zip(
           'ABCDEFGHIJKL', (410, 435, 460, 485, 510, 535, 560, 585,
                            610, 645, 680, 705)))},
})
with tempfile.NamedTemporaryFile(suffix='.csv', delete=False,
                                 mode='w', encoding='utf-8') as tf:
    csv_b.to_csv(tf.name, sep=';', index=False)
    path_b = tf.name
e2 = _ingest(path_b)
meta2 = e2.get('metadata') or {}
check("T2a echter Klassifikationsfall unberuehrt (Text-Label)",
      meta2.get('analysis_mode') == 'classification',
      str(meta2.get('analysis_mode')))
check("T2b class_label_column = Sorte",
      meta2.get('class_label_column') == 'Sorte',
      str(meta2.get('class_label_column')))

# T3: Ziel + echtes Text-Klassen-Label koexistieren weiterhin
csv_c = pd.DataFrame({
    'Brix': [4.0 + (i % 20) * 0.15 for i in range(120)],
    'Sorte': ['A'] * 60 + ['B'] * 60,
    **{f'{c}_{w}': [100.0 + j + (i % 9) for i in range(120)]
       for j, (c, w) in enumerate(zip(
           'ABCDEFGHIJKL', (410, 435, 460, 485, 510, 535, 560, 585,
                            610, 645, 680, 705)))},
})
with tempfile.NamedTemporaryFile(suffix='.csv', delete=False,
                                 mode='w', encoding='utf-8') as tf:
    csv_c.to_csv(tf.name, sep=';', index=False)
    path_c = tf.name
e3 = _ingest(path_c)
meta3 = e3.get('metadata') or {}
check("T3a Ziel vorhanden -> regression gewinnt",
      meta3.get('analysis_mode') == 'regression',
      str(meta3.get('analysis_mode')))

# T4: Echte Nutzer-CSV (falls Upload verfuegbar)
real = None
for cand in Path('/mnt/vibefs/uploads').rglob(
        'epWxfnUg-Alle_Daten_Brix*.CSV'):
    real = cand
    break
if real is not None:
    e4 = _ingest(real, 'Alle_Daten_Brix.csv')
    meta4 = e4.get('metadata') or {}
    check("T4a echte CSV: regression (war classification)",
          meta4.get('analysis_mode') == 'regression',
          str(meta4.get('analysis_mode')))
    check("T4b echte CSV: Temp0-Frage in der App",
          any('Temp0' in str(q) for q in (e4.get('open_questions') or [])))
    check("T4c echte CSV: Kalibrationszeilen > 1000 (waren 0)",
          len(e4.get('calibration_samples') or []) > 1000,
          str(len(e4.get('calibration_samples') or [])))
else:
    print('[SKIP] echte CSV nicht im Sandbox-Upload (nur Struktur-Test)')

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
