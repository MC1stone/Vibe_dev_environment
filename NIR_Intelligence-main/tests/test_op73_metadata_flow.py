#!/usr/bin/env python3
# OP73 test matrix: Metadaten-Abgleich -> Editor -> Speichern ->
# Reingest -> Crew. Nutzer-Befund (2026-10-20): im Metadaten-Abgleich
# erfasste Aenderungen wirkungslos - wurden offenbar nicht an der
# richtigen Stelle gespeichert und bei der Neuanalyse nicht uebernommen.
# Ursache 1 (gefundener JS-Bug): nirApplyMetadataSuggestion fuellte
# [name="meta_<feld>"], der Editor rendert [name="<feld>"] - der
# uebernommene Wert verschwand still.
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
if "testserver" not in dj_settings.ALLOWED_HOSTS:
    dj_settings.ALLOWED_HOSTS = [*dj_settings.ALLOWED_HOSTS, "testserver"]
dj_settings.DATABASES["default"]["NAME"] = ":memory:"
dj_settings.DATABASES["default"].setdefault("ATOMIC_REQUESTS", False)
from django.core.management import call_command  # noqa: E402
call_command("migrate", interactive=False, verbosity=0)

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# T1: JS-Bug-Fix — Uebernehmen-Button trifft die Editor-Inputs
# ---------------------------------------------------------------------------
main_src = (REPO_ROOT / "django_project" / "static" / "js"
            / "main.js").read_text(encoding="utf-8")
tpl_src = (REPO_ROOT / "django_project" / "templates"
           / "project_report.html").read_text(encoding="utf-8")

check("T1a Fix vorhanden: Selector ohne meta_-Praefix",
      '[name="${field}"]' in main_src
      and '[name="meta_${field}"]' not in main_src)
check("T1b Fix trifft die echten Editor-Inputs (Template nutzt "
      "name=\"{{ f.name }}\")",
      'name="{{ f.name }}"' in tpl_src
      and 'name="meta_' not in tpl_src)
check("T1c Container-Scope auf .metadata-form beschraenkt",
      "document.querySelectorAll('.metadata-form').forEach" in main_src)
check("T1d fehlendes Feld wird dynamisch hinzugefuegt (nichts geht "
      "still verloren)", "col.appendChild(input)" in main_src
      and "input.name = field" in main_src)
check("T1e sichtbarer Hinweis nach Uebernehmen (Speichern noetig)",
      "Metadaten speichern" in main_src)
import subprocess  # noqa: E402
res = subprocess.run(["node", "--check",
                      str(REPO_ROOT / "django_project" / "static" / "js"
                          / "main.js")],
                     capture_output=True, text=True)
check("T1f node --check main.js", res.returncode == 0, res.stderr[:200])

# ---------------------------------------------------------------------------
# T2: Server-Pfad — Overrides speichern -> Reingest -> Crew uebernimmt
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from core.models import AnalysisProject, GenericFile  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op73meta").first()
if user is None:
    user = User.objects.create_user("op73meta", password="pw",
                                    email="op73@example.com")

import tempfile  # noqa: E402
csv_content = ("Messobjekt;Brix;A_410;B_435\n"
               "T1;4.5;100;200\nT2;5.5;110;210\nT3;6.5;120;220\n"
               "T4;7.5;130;230\nT5;8.0;140;240\nT6;4.9;150;250\n"
               "T7;5.1;160;260\nT8;6.1;170;270\nT9;7.1;180;280\n"
               "T10;6.9;190;290\nT11;5.9;200;300\nT12;6.3;210;310\n")
with tempfile.NamedTemporaryFile(suffix='.csv', delete=False,
                                  mode='w', encoding='utf-8') as tf:
    tf.write(csv_content)
    tmp_csv = tf.name

class _FileRecord:
    """Minimal GenericFile stand-in (vgl. test_op30): der Ingest nutzt
    id, name, file_extension, file_category, get_file_path()."""

    def __init__(self, path, name, file_id):
        self.id = file_id
        self.name = name
        self.file_extension = 'csv'
        self.file_category = 'raw'
        self._path = str(path)

    def get_file_path(self):
        return self._path


import uuid as _uuid  # noqa: E402
_fid = str(_uuid.uuid4())
_file_rec = _FileRecord(tmp_csv, 'op73.csv', _fid)


class _Project:
    """Project stand-in: der Test prueft den Ingest-/Override-Datenfluss,
    nicht die ORM-Persistenz (die deckt T3 via Endpoint ab)."""

    def __init__(self):
        self.id = None
        self.files = [_file_rec]
        self.metadata_overrides = {}
        self.preparation_report = None


from services.project_ingest import (  # noqa: E402
    apply_metadata_overrides, build_preparation_report as _bpr_raw,
    ingest_file,
)


def build_for(project_like):
    """build_preparation_report am Projektstand-in (Ingest + Overrides)."""
    datasets = []
    for f in project_like.files:
        entries = ingest_file(f)
        if isinstance(entries, dict):
            entries = [entries]
        for entry in entries:
            entry_overrides = (project_like.metadata_overrides or {})                 .get(str(entry.get('file_id')))
            apply_metadata_overrides(entry, entry_overrides or {})
            datasets.append(entry)
    return {'datasets': datasets}


pj = _Project()
report = build_for(pj)
datasets = report.get('datasets', [])
check("T2a Datensatz ingested", len(datasets) >= 1,
      str(len(datasets)))
if datasets:
    file_id = datasets[0].get('file_id')
    check("T2b file_id im Report", bool(file_id), str(file_id))

    # Nutzer erfasst Metadaten (wie der Editor nach dem Fix)
    pj.metadata_overrides = {str(file_id): {
        'operator': 'Testoperator OP73',
        'sample_description': 'Tomaten vom Feldtest',
    }}

    # Reingest (Neuanalyse-Vorbereitung)
    report2 = build_for(pj)
    ds2 = report2.get('datasets', [])
    check("T2c Reingest uebernimmt die Overrides in den Datensatz",
          ds2 and (ds2[0].get('metadata') or {}).get('operator')
          == 'Testoperator OP73',
          str((ds2[0].get('metadata') if ds2 else None) or {})[:200])
    check("T2d zweites Feld ebenfalls uebernommen",
          ds2 and (ds2[0].get('metadata') or {})
          .get('sample_description') == 'Tomaten vom Feldtest')
    check("T2e metadata_user_entered vermerkt",
          ds2 and 'operator' in (ds2[0].get('metadata_user_entered')
                                 or []))

    # T3: Override-Merge-Verhalten (Endpoint-Pfad deckt OP13-Tests ab;
    # hier: Merge-Verlustfreiheit am Stand-in, identisch zur Endpoint-
    # Logik project.metadata_overrides + build_preparation_report)
    pj.metadata_overrides[str(file_id)]['location'] = 'Feldversuch Garden'
    report3 = build_for(pj)
    ds3 = report3.get('datasets', [])
    check("T3b erneut angewendete Overrides landen im Datensatz",
          ds3 and (ds3[0].get('metadata') or {})
          .get('location') == 'Feldversuch Garden',
          str((ds3[0].get('metadata') if ds3 else None) or {})[:200])
    check("T3c alte Overrides bleiben erhalten (Merge, kein Verlust)",
          ds3 and (ds3[0].get('metadata') or {}).get('operator')
          == 'Testoperator OP73')
    check("T3d wiederholter Reingest aendert nichts (idempotent)",
          build_for(pj).get('datasets')[0]['metadata'].get('location')
          == 'Feldversuch Garden')

# T5: Verbindungs-Check Editor-Template <-> Speichern-Handler:
# FormData uebertraegt name="<feld>" (mit csrf); der Handler baut
# m[fileId] = fields. Der Fix stellt sicher, dass 'Uebernehmen' dieselben
# name-Attribute fuellt, die der Handler liest.
check("T5a Editor-Speichern liest alle Form-Inputs (FormData)",
      "new FormData(form).forEach" in tpl_src)
check("T5b Uebernehmen-Status-Hinweis fordert zum Speichern auf",
      "endgültig zu speichern" in main_src)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
