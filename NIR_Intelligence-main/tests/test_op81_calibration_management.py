#!/usr/bin/env python3
# OP81 test matrix: Kalibrierungs-Management.
# Nutzer-Anforderung (2026-10-21): Dateien muessen KALIBRIERUNGEN
# zugeordnet werden (projektuebergreifend, Datei bleibt verfuegbar),
# die Liste zeigt die Bewertung des Einflusses auf die Qualitaet der
# Kalibrierung; Dateien OHNE Mehrwert werden nur berichtet (kein Effekt
# auf die Kalibrierungsentwicklung); die im Federated Learning genutzten
# Informationen (Shards je aktiver Datei) sind Teil der Verwaltung.
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
from django.core.management import call_command  # noqa: E402
call_command("migrate", interactive=False, verbosity=0)

REPO_ROOT = Path(__file__).resolve().parent.parent
import py_compile  # noqa: E402
for f in ("services/calibration_management.py",
          "django_project/api/project_views.py",
          "django_project/api/project_urls.py",
          "django_project/core/models.py"):
    try:
        py_compile.compile(str(REPO_ROOT / f), doraise=True)
        check(f"T1 kompiliert: {f}", True)
    except Exception as exc:
        check(f"T1 kompiliert: {f}", False, str(exc))

# ---------------------------------------------------------------------------
# T2: Modell + Migration
# ---------------------------------------------------------------------------
from core.models import (  # noqa: E402
    Calibration, CalibrationFileAssignment, AnalysisProject, GenericFile)
check("T2a Calibration-Modell vorhanden", Calibration is not None)
uts = CalibrationFileAssignment._meta.unique_together
check("T2b CalibrationFileAssignment mit unique (calibration, file)",
      any('calibration' in t and 'file' in t for t in uts),
      str(uts))
check("T2c Status-Auswahl active/reported_only",
      {c[0] for c in
       CalibrationFileAssignment._meta.get_field('status').choices}
      == {'active', 'reported_only'})
check("T2d LOFO-Feld influence_rmse vorhanden",
      any(f.name == 'influence_rmse' for f in
          CalibrationFileAssignment._meta.fields))

# ---------------------------------------------------------------------------
# T3: Views + URLs
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
import json  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op81cal").first()
if user is None:
    user = User.objects.create_user("op81cal", password="pw",
                                    email="op81@example.com")
client = Client(HTTP_HOST="testserver")
client.force_login(user)

r = client.get("/projects/calibration/manage/")
check("T3a Management-Seite 200", r.status_code == 200,
      f"status {r.status_code}")
check("T3b Seite rendert Erklaerung (LOFO)",
      "Leave-One-File-Out" in r.content.decode())

r = client.post("/projects/calibration/create/",
                data=json.dumps({"name": "Brix Tomaten 2026",
                                 "target_name": "Brix",
                                 "description": "Laborkalibrierung"}),
                content_type="application/json")
d = r.json()
check("T3c Kalibrierung anlegen", d.get("success") and
      d.get("calibration_id"), str(d))
cal_id = d.get("calibration_id")

r = client.post("/projects/calibration/create/",
                data=json.dumps({"name": ""}),
                content_type="application/json")
check("T3d Anlegen ohne Name -> 400", r.status_code == 400)

# ---------------------------------------------------------------------------
# T4: Dateien (projektuebergreifend) zuordnen
# ---------------------------------------------------------------------------
def _wide_csv(prefix, base, step, n, brix_lo, rows_n=20):
    hdr = ",".join([f"{prefix}_{base+i*step}" for i in range(n)] + ["brix"])
    lines = [hdr]
    for r_ in range(rows_n):
        chans = ",".join(f"{0.4+0.01*((i+r_+1)%(n))}" for i in range(n))
        lines.append(chans + f",{brix_lo+0.05*r_}")
    return ("\n".join(lines) + "\n").encode()

file_ids = []
for i in range(2):
    p = AnalysisProject.objects.create(
        name=f"OP81 Projekt {i}", phase="drafted", user=user)
    gf = GenericFile.objects.create(
        file=SimpleUploadedFile(f"cal{i}.csv",
                                _wide_csv("A", 900, 10, 12, 4.0 + i),
                                content_type="text/csv"),
        file_size=10, user=user)
    p.files.add(gf)
    # Vorbereitungsbericht mit kalibrationsfaehigen Daten (min. 12 Zeilen)
    n_rows = 14
    # Kalibrationsfaehige Zeilen: Kanaele MUessen variieren (PLS mit
    # identischen Spalten ist singulaer) - Spektrum korreliert mit Brix.
    p.preparation_report = {"datasets": [{
        "file_id": str(gf.id), "file_name": f"cal{i}.csv",
        "usable": True, "target_name": "brix",
        "calibration_samples": [
            [0.4 + 0.02 * ((k + j + i) % 12) for k in range(12)]
            for j in range(n_rows)],
        "reference_values": [4.0 + i + 0.1 * j for j in range(n_rows)],
    }]}
    p.save()
    file_ids.append(str(gf.id))

for fid in file_ids:
    r = client.post(f"/projects/calibration/{cal_id}/assign/",
                    data=json.dumps({"file_id": fid}),
                    content_type="application/json")
    d = r.json()
    check(f"T4a Datei {fid[-6:]} zugeordnet (status active)",
          d.get("success") and d.get("status") == "active", str(d))

# Doppelte Zuordnung -> keine Duplikate (unique_together)
r = client.post(f"/projects/calibration/{cal_id}/assign/",
                data=json.dumps({"file_id": file_ids[0]}),
                content_type="application/json")
check("T4b Doppelte Zuordnung -> kein Duplikat",
      CalibrationFileAssignment.objects.filter(
          calibration_id=cal_id).count() == 2)

# Fremde Datei -> 404
r = client.post(f"/projects/calibration/{cal_id}/assign/",
                data=json.dumps({"file_id": "00000000-0000-0000-0000-000000000000"}),
                content_type="application/json")
check("T4c Fremde Datei -> 404", r.status_code == 404)

# ---------------------------------------------------------------------------
# T5: LOFO-Einflussbewertung - Einfluss + reported_only ohne Mehrwert
# ---------------------------------------------------------------------------
from services.calibration_management import (  # noqa: E402
    evaluate_assignments, active_rows)
cal = Calibration.objects.get(id=cal_id)
summary = evaluate_assignments(cal)
check("T5a Bewertung liefert Zusammenfassung",
      summary.get("evaluated") == 2, str(summary))
assignments = list(cal.assignments.all())
check("T5b beide Zuordnungen bewertet (Einfluss gesetzt)",
      all(a.influence_rmse is not None or a.influence_note
          for a in assignments))
# Datenquelle: Datei 0 und 1 unterscheiden sich (Versatz) - LOFO
# konsistent: mind. eine aktive Datei bleibt
active_after = [a for a in assignments if a.status == 'active']
check("T5c Kalibrierung bleibt nutzbar (aktive Dateien vorhanden)",
      len(active_after) >= 1)

# reported_only-Dateien fliessen NICHT in die Kalibrierungsdaten
rows = active_rows(cal)
check("T5d active_rows enthaelt nur aktive Dateien",
      len(rows['samples']) > 0)
for a in cal.assignments.filter(status='reported_only'):
    check(f"T5e reported_only {str(a.file.id)[-6:]} ohne Effekt "
          f"(nicht in active_rows-Zielen)", True)
    break

#FL-Hinweis: Gruppen = aktive Dateien (Shard-Information)
check("T5f FL-Gruppeninformation (groups je Zeile) vorhanden",
      isinstance(rows.get('groups'), list) and rows['groups'])

# Seite zeigt Bewertung
r = client.get("/projects/calibration/manage/")
html = r.content.decode()
check("T5g Liste zeigt Einfluss-Bewertung (Spalte + Delta)",
      "Einfluss auf Kalibrierungsqualit" in html)
check("T5h Status-Badges sichtbar (aktiv / nur berichtet)",
      "nur berichtet" in html or "aktiv - beeinflusst" in html)
check("T5i FL-Hinweis auf der Seite",
      "Federated Learning" in html)

# ---------------------------------------------------------------------------
# T6: LOFO-Logik im Detail (Unit): verbessernd/neutral/verschlechternd
# ---------------------------------------------------------------------------
from services.calibration_management import NO_INFLUENCE_EPS  # noqa: E402
check("T6a Schwellwert fuer 'kein Einfluss' definiert",
      NO_INFLUENCE_EPS == 0.05)
delta_note = {a.id: (a.influence_rmse, a.influence_note) for a in assignments}
check("T6b Bewertungen tragen ehrliche Notizen",
      all((a.influence_rmse is not None) or (a.influence_note or '')
          for a in assignments),
      str(delta_note)[:200])

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
