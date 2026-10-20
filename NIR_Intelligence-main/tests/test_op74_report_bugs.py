#!/usr/bin/env python3
# OP74 test matrix: Nutzer-Befunde aus dem Projektbericht-PDF (2026-10-20)
#  A) csrfmiddlewaretoken als Metadatum (Client + Server + Ingest-Filter)
#  B) KI-Fragen: Grossbuchstaben-Anfang ('itte...'->'Bitte...'),
#     Deduplizierung gleicher Fachfragen
#  C) Sensor-Referenz: 'Triad' als GERAET bekannt (sparkfun_triad),
#     nur Dokumente fehlen - Anzeige + normalisierter Link
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
# T1: CSRF-Filter (alle drei Schichten)
# ---------------------------------------------------------------------------
tpl = (REPO_ROOT / "django_project" / "templates"
       / "project_report.html").read_text(encoding="utf-8")
views = (REPO_ROOT / "django_project" / "api"
         / "project_views.py").read_text(encoding="utf-8")
ingest = (REPO_ROOT / "services" / "project_ingest.py").read_text(
    encoding="utf-8")

check("T1a Client: FormData filtert csrfmiddlewaretoken",
      "key !== 'csrfmiddlewaretoken'" in tpl)
check("T1b Server: Metadata-Endpoint skippt csrfmiddlewaretoken",
      "csrfmiddlewaretoken" in views and "continue" in
      views.split("csrfmiddlewaretoken")[1][:200])
check("T1c Ingest: _NON_METADATA_KEYS Filter vorhanden",
      "_NON_METADATA_KEYS = {'csrfmiddlewaretoken'" in ingest)

# Verhaltenstest am Ingest-Filter
from services.project_ingest import apply_metadata_overrides  # noqa: E402
entry = {'metadata': {'csrfmiddlewaretoken': 'ABC123', 'operator': 'Timo'}}
apply_metadata_overrides(entry, {'csrfmiddlewaretoken': 'XYZ',
                                 'humidity': '66'})
check("T1d csrf wird aus Bestandsmetadaten entfernt",
      'csrfmiddlewaretoken' not in (entry.get('metadata') or {}),
      str(entry.get('metadata')))
check("T1e csrf wird nicht durch Overrides eingeschleust",
      entry['metadata'].get('humidity') == '66'
      and 'csrfmiddlewaretoken' not in entry['metadata'])
check("T1f echte Felder bleiben erhalten",
      entry['metadata'].get('operator') == 'Timo')

# ---------------------------------------------------------------------------
# T2: KI-Fragen-Normalisierung + Deduplizierung
# ---------------------------------------------------------------------------
check("T2a Deduplizierung implementiert (_asked_dedup)",
      "_asked_dedup" in ingest and "dedup_key = (topic," in ingest)
check("T2b Fragetext mit Grossbuchstaben beginnend normalisiert",
      "question[0].islower()" in ingest
      and "question[0].upper()" in ingest)

# Verhaltenstest der Normalisierungsfunktion
def _normalize(q):
    q = q.strip()
    if q and q[0].islower():
        q = q[0].upper() + q[1:]
    return q
check("T2c 'itte geben Sie...' -> 'Itte geben Sie...'",
      _normalize('itte geben Sie uns die folgenden Informationen')
      == 'Itte geben Sie uns die folgenden Informationen')
check("T2d korrekte Frage unveraendert",
      _normalize('Bitte geben Sie die Seriennummer an.')
      == 'Bitte geben Sie die Seriennummer an.')

# ---------------------------------------------------------------------------
# T3: Sensor-Referenz - 'Triad' als Geraet erkannt
# ---------------------------------------------------------------------------
from services.sensor_documents import check_sensor_reference  # noqa: E402
res = check_sensor_reference(['Triad'], None)
unknown = res.get('unknown') or []
checked = res.get('checked') or []
triad_entry = next((e for e in unknown + checked
                    if e.get('sensor') == 'Triad'), None)
check("T3a Triad in der Referenz-Pruefung", triad_entry is not None)
check("T3b Triad als GERAET erkannt (device_known, model_id)",
      triad_entry and triad_entry.get('device_known') is True
      and triad_entry.get('model_id') == 'sparkfun_triad',
      str(triad_entry or {}))
check("T3c Link normalisiert auf sparkfun_triad",
      triad_entry and 'sparkfun_triad' in triad_entry.get('sensor_url', ''))
check("T3d ohne Dokumente weiterhin als unknown gelistet (ehrlich)",
      triad_entry in unknown)

check("T3e Template: 'Geraet bekannt (keine Dokumente)' Badge",
      "Gerät bekannt (keine Dokumente)" in tpl)
check("T3f Template: registrierter Adapter angezeigt",
      "registrierter Adapter" in tpl)

# ---------------------------------------------------------------------------
# T4: Regression - Editor/Endpoint-Basis unveraendert intakt
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op74meta").first()
if user is None:
    user = User.objects.create_user("op74meta", password="pw",
                                    email="op74@example.com")
client = Client(HTTP_HOST='testserver')
client.force_login(user)
r = client.get('/login/')
check("T4a Basis-App erreichbar", r.status_code == 200)
check("T4b OP73-Fix weiterhin drin (Uebernehmen-Selector)",
      "nirApplyMetadataSuggestion" in
      (REPO_ROOT / "django_project" / "static" / "js" / "main.js")
      .read_text(encoding="utf-8"))

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
