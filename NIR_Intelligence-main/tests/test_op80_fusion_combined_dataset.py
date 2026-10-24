#!/usr/bin/env python3
# OP80 test matrix: Echter MERGE der Fusions-Datensaetze zu EINER
# Auswertung + Wellenlaengen-Harmonisierung + Nutzer-Review.
# Nutzer-Anforderung (2026-10-21): 'Bei einem Merge sollen die
# Datensaetze gemergt werden und damit bekomme ich im Grunde nur noch
# EINE Auswertung. Ist der Unterschied (z. B. anderer Sensor)
# signifikant? Was bei unterschiedlichen Wellenlaengen-Rastern - mit
# der Kurve selbst arbeiten?'
# OP80b (Nachtrag): 'Zeige dem Nutzer die erstellten Daten zum Review,
# um sicherzustellen, dass die KI die Daten richtig zusammengefuehrt
# hat' -> Review-Karte auf der Projektseite.
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

for f in ("services/fusion_combine.py", "services/project_ingest.py",
          "services/project_crew.py"):
    try:
        py_compile.compile(str(REPO_ROOT / f), doraise=True)
        check(f"T1 kompiliert: {f}", True)
    except Exception as exc:
        check(f"T1 kompiliert: {f}", False, str(exc))

# ---------------------------------------------------------------------------
# T2: Einheit - Harmonisierung + Kombination
# ---------------------------------------------------------------------------
from services.fusion_combine import (  # noqa: E402
    build_combined_dataset, sensor_significance_hint)

d_a = {
    'usable': True, 'file_name': 'sensor_a.csv', 'target_name': 'brix',
    'preview': {'wavelengths': [900.0, 910.0, 920.0, 930.0],
                'intensities': []},
    'calibration_samples': [[0.5, 0.6, 0.7, 0.8]] * 12,
    'reference_values': [4.0 + 0.1 * i for i in range(12)],
}
d_b = {
    'usable': True, 'file_name': 'sensor_b.csv', 'target_name': 'brix',
    'preview': {'wavelengths': [905.0, 915.0, 925.0],
                'intensities': []},
    'calibration_samples': [[0.52, 0.62, 0.72]] * 10,
    'reference_values': [5.0 + 0.1 * i for i in range(10)],
}
combined = build_combined_dataset([d_a, d_b])
check("T2a zwei Quellen kombinierbar", combined is not None)
check("T2b EIN kombinierter Datensatz (fusion_merged)",
      (combined.get('metadata') or {}).get('fusion_merged') is True)
check("T2c Zeilen = 22 (12 + 10)",
      len(combined['calibration_samples']) == 22,
      f"got {len(combined['calibration_samples'])}")
check("T2d Harmonisierung dokumentiert (linear_interpolation)",
      (combined['fusion_merge']['harmonization'] or {})
      .get('method') == 'linear_interpolation')
check("T2e gemeinsames Raster im Schnittbereich",
      combined['preview']['wavelengths'][0] == 905.0
      and combined['preview']['wavelengths'][-1] == 925.0,
      str(combined['preview']['wavelengths']))
check("T2f Gruppen-Labels je Zeile gespeichert",
      len(combined['metadata']['group_labels']) == 22
      and set(combined['metadata']['group_labels'])
      == {'sensor_a.csv', 'sensor_b.csv'})
check("T2g Quell-Bericht je Datei (merged + Zeilenzahl)",
      len(combined['fusion_merge']['sources']) == 2
      and all(s.get('status') == 'merged'
              for s in combined['fusion_merge']['sources']))
check("T2h Signifikanz-Hinweis bei mehreren Gruppen",
      sensor_significance_hint(combined) is not None)

# Gleiche Raester -> keine Interpolation
d_c = dict(d_a, file_name='sensor_c.csv')
combined_eq = build_combined_dataset([d_a, d_c])
check("T2i gleiche Raester: keine Harmonisierung noetig",
      combined_eq['fusion_merge']['rasters_equal'] is True
      and combined_eq['fusion_merge']['harmonization'] is None)

# Wuensche auf den KOMBINIERTEN Daten
wishes = [{'type': 'classes', 'n': 3, 'name': '3 Gruppen'}]
combined_w = build_combined_dataset([d_a, d_b], parsed_wishes=wishes)
check("T2j Wuensche wirken auf kombinierten Daten",
      bool(combined_w.get('classification_samples'))
      and 'wishes_applied' in combined_w['fusion_merge'])

# ---------------------------------------------------------------------------
# T3: Ingest-Hook - Fusionsprojekt erhaelt den kombinierten Datensatz
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from core.models import AnalysisProject, GenericFile  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op80fusion").first()
if user is None:
    user = User.objects.create_user("op80fusion", password="pw",
                                    email="op80@example.com")

# Wide-Format-Kanal-Spalten im _WAVELENGTH_COLUMN_RE-Muster (A_900):
# Sensor A: 18 Kanaele 900-1070 nm; Sensor B: 15 Kanaele 905-1045 nm
# (absichtlich ANDERES Raster -> Harmonisierung wird geprueft).
def _wide_csv(prefix, base, step, n, brix_lo):
    hdr = ",".join([f"{prefix}_{base+i*step}" for i in range(n)] + ["brix"])
    rows = ["\n".join([])]
    lines = [hdr]
    for r in range(20):
        chans = ",".join(f"{0.4+0.01*((i+r)%(n))}" for i in range(n))
        lines.append(chans + f",{brix_lo+0.05*r}")
    return ("\n".join(lines) + "\n").encode()

csv_a = _wide_csv("A", 900, 10, 18, 4.0)
csv_b = _wide_csv("B", 905, 10, 15, 5.0)

fused = AnalysisProject.objects.create(
    name="OP80 Fusionsprojekt", phase="drafted", user=user)
for name, content in (("sensor_a.csv", csv_a), ("sensor_b.csv", csv_b)):
    gf = GenericFile.objects.create(
        file=SimpleUploadedFile(name, content, content_type="text/csv"),
        file_size=len(content), user=user)
    fused.files.add(gf)
fused.preparation_report = {
    'user_options': {},
    'fusion': {'source_projects': [
        {'project_id': 'x1', 'project_name': 'A'},
        {'project_id': 'x2', 'project_name': 'B'}],
        'created_by': 'op63_fusion'},
}
fused.save()

from services.project_ingest import build_preparation_report  # noqa: E402
report = build_preparation_report(fused)
rep = fused.preparation_report or {}
ds_list = rep.get('datasets') or []
check("T3a Bericht erzeugt", len(ds_list) >= 1)
check("T3b kombiniert + Quell-Datensaetze im Bericht",
      any((d.get('metadata') or {}).get('fusion_merged')
          for d in ds_list)
      and len(ds_list) >= 3,
      f"n_datasets={len(ds_list)}")
check("T3c kombinierter steht OBEN (erste Auswertung = Merge)",
      (ds_list[0].get('metadata') or {}).get('fusion_merged') is True)
merged_ds = ds_list[0]
check("T3d group_labels im Bericht",
      bool((merged_ds.get('metadata') or {}).get('group_labels')))
check("T3e fusion_merge-Review-Daten im Bericht (sources)",
      bool((merged_ds.get('fusion_merge') or {}).get('sources')))
check("T3f Harmonisierung im Bericht dokumentiert",
      bool((merged_ds.get('fusion_merge') or {})
           .get('harmonization')))

# ---------------------------------------------------------------------------
# T4: Crew reicht group_labels an den Statistik-Agenten durch
# ---------------------------------------------------------------------------
crew_src = (REPO_ROOT / "services" / "project_crew.py").read_text("utf-8")
check("T4a group_labels im Agenten-Request",
      "'group_labels':" in crew_src)

# ---------------------------------------------------------------------------
# T5: OP80b - Review-Karte auf der Projektseite
# ---------------------------------------------------------------------------
tpl_src = (REPO_ROOT / "django_project" / "templates"
           / "project_report.html").read_text("utf-8")
check("T5a Review-Karte vorhanden (fusionCombinedReview)",
      "fusionCombinedReview" in tpl_src)
check("T5b Karte zeigt Quellen-Tabelle (fusion_merge.sources)",
      "d.fusion_merge.sources" in tpl_src)
check("T5c Karte zeigt Harmonisierung (range/step/Zeilen)",
      "d.fusion_merge.harmonization" in tpl_src
      and "n_interpolated_rows" in tpl_src)
check("T5d Zeilen-/Kanal-/Referenz-Zahlen pruefbar",
      "d.calibration_samples|length" in tpl_src
      and "d.preview.wavelengths|length" in tpl_src)
check("T5e Signifikanz-Hinweis in der Karte",
      "signifikanztesten" in tpl_src)

client = Client(HTTP_HOST="testserver")
client.force_login(user)
r = client.get(f"/projects/{fused.id}/")
html = r.content.decode()
check("T5f Projektseite 200", r.status_code == 200)
check("T5g Review-Karte gerendert mit echten Zahlen",
      "fusionCombinedReview" in html
      and "sensor_a" in html and "sensor_b" in html)
check("T5h Harmonisierungs-Hinweis sichtbar (linearer Interpolation)",
      "linearer Interpolation" in html)

# ---------------------------------------------------------------------------
# T6: OP82 - Reingest am Fusionsprojekt erhaelt die fusion-Sektion.
# Nutzer-Versuch (2026-10-22): 'Aufbereitung erneut ausfuehren' am
# zusammengefuehrten Projekt LEERTE den Report inkl. fusion -> der
# OP80-Hook erkannte das Projekt nicht mehr als Fusion, es wurde KEIN
# kombinierter Datensatz gebaut (Merge ins Leere).
# ---------------------------------------------------------------------------
views_src = (REPO_ROOT / "django_project" / "api"
             / "project_views.py").read_text("utf-8")
check("T6a Reingest bewahrt fusion-Sektion (OP82)",
      "preserved['fusion'] = report['fusion']" in views_src)

# E2E: Reingest-Endpoint laesst fusion im Report stehen
import json as _json3  # noqa: E402
client2 = Client(HTTP_HOST="testserver")
client2.force_login(user)
# Projekt ist nach T3 vorbereitet (fusion + kombinierter Datensatz);
# Reingest triggern und pruefen, dass fusion ueberlebt.
fused.phase = "drafted"
fused.save()
r7 = client2.post(f"/projects/{fused.id}/reingest/")
d7 = r7.json()
check("T6b Reingest-Endpoint antwortet mit preparing",
      d7.get("preparing") is True, str(d7)[:120])
fused.refresh_from_db()
rep7 = fused.preparation_report or {}
check("T6c fusion-Sektion nach Reingest-Start erhalten",
      bool(rep7.get("fusion")), str(rep7.keys())[:120])
check("T6d user_options ebenfalls erhalten",
      "user_options" in rep7)

# ---------------------------------------------------------------------------
# T7: OP85 - Ehrlichkeit, wenn der Merge NICHT moeglich ist (Still-
# Schweigen war der Bug: der Nutzer sah keine Review-Karte und keinen
# Grund). Jetzt: fusion_merge_note mit Grund + Warnkarte.
# ---------------------------------------------------------------------------
ingest_src2 = (REPO_ROOT / "services" / "project_ingest.py").read_text("utf-8")
check("T7a fehlgeschlagener Merge dokumentiert (fusion_merge_note)",
      "fusion_merge_note" in ingest_src2)
check("T7b Grund mit kalibrationsfaehiger Anzahl",
      "calibratable_datasets" in ingest_src2)
tpl2 = (REPO_ROOT / "django_project" / "templates"
        / "project_report.html").read_text("utf-8")
check("T7c Warnkarte im Template (fusionMergeNote)",
      "fusionMergeNote" in tpl2)
check("T7d Karte zeigt den Grund",
      "preparation.fusion_merge_note.reason" in tpl2)

# E2E: Fusionsprojekt mit nur EINEM kalibrationsfaehigen Datensatz
# -> Note + Warnkarte statt stiller Einzel-Auswertung
p2 = AnalysisProject.objects.create(name="OP85-NoMerge", phase="drafted",
                                    user=user)
gf_a = GenericFile.objects.create(
    file=SimpleUploadedFile("a.csv", _wide_csv("A", 900, 10, 12, 4.0),
                            content_type="text/csv"),
    file_size=10, user=user)
gf_b = GenericFile.objects.create(
    file=SimpleUploadedFile("b.csv", b"nur,text,ohne,brix\n1,2,3,4\n",
                            content_type="text/csv"),
    file_size=10, user=user)
p2.files.add(gf_a)
p2.files.add(gf_b)
p2.preparation_report = {
    'user_options': {},
    'fusion': {'source_projects': [{'project_id': 'x1'}],
               'created_by': 'op63_fusion'}}
p2.save()
from services.project_ingest import build_preparation_report  # noqa: E402
report2 = build_preparation_report(p2)
rep2 = p2.preparation_report or {}
note2 = rep2.get('fusion_merge_note') or {}
check("T7e E2E: Note gesetzt (combined False)",
      note2.get('combined') is False, str(note2)[:100])
check("T7f E2E: Grund nennt die kalibrationsfaehige Anzahl",
      'kalibrationsf' in str(note2.get('reason', '')),
      str(note2.get('reason', ''))[:80])
r8 = client.get(f"/projects/{p2.id}/")
html8 = r8.content.decode()
check("T7g E2E: Warnkarte gerendert",
      "fusionMergeNote" in html8)
check("T7h E2E: Grund auf der Seite sichtbar",
      "kalibrationsf" in html8)

# ---------------------------------------------------------------------------
# T8: OP86 - Metadaten der Quellen ueberleben den Merge (Nutzer-Befund:
# 'Obwohl alle Daten fuer 100% vorhanden sind, entsteht im Merge nur
# 20% - dann brauchen wir den Aufwand nicht zu betreiben').
# ---------------------------------------------------------------------------
combine_src = (REPO_ROOT / "services" / "fusion_combine.py").read_text("utf-8")
check("T8a Quell-Metadaten werden uebernommen (kein Hardcode mehr)",
      "merged_meta" in combine_src
      and "src_meta" in combine_src)
check("T8b metadata_sources ebenfalls gemergt",
      "merged_sources" in combine_src)
check("T8c Konflikte ehrlich dokumentiert (nie still waehlen)",
      "konflikt" in combine_src
      and "Metadatenkonflikt im Merge" in combine_src)

from services.fusion_combine import build_combined_dataset as _bcd  # noqa: E402
META_FIELDS = {"operator_name": "Anna", "instrument_type": "diy_matchbox",
               "timestamp": "2026-10-22 07:00:00", "location": "Lab 1",
               "experiment_name": "Tomaten"}
d_m1 = {
    'usable': True, 'file_name': 'm1.csv', 'target_name': 'brix',
    'preview': {'wavelengths': [900.0, 910.0, 920.0], 'intensities': []},
    'calibration_samples': [[0.5, 0.6, 0.7]] * 12,
    'reference_values': [4.0 + 0.1 * i for i in range(12)],
    'metadata': dict(META_FIELDS),
    'metadata_sources': {k: 'deterministisch' for k in META_FIELDS},
}
d_m2 = {
    'usable': True, 'file_name': 'm2.csv', 'target_name': 'brix',
    'preview': {'wavelengths': [900.0, 910.0, 920.0], 'intensities': []},
    'calibration_samples': [[0.52, 0.62, 0.72]] * 10,
    'reference_values': [6.0 + 0.1 * i for i in range(10)],
    'metadata': dict(META_FIELDS),
    'metadata_sources': {k: 'deterministisch' for k in META_FIELDS},
}
c_merged = _bcd([d_m1, d_m2])
check("T8d Merge mit gleichen Quell-Metadaten erfolgreich",
      c_merged is not None)
meta_c = (c_merged.get('metadata') or {}) if c_merged else {}
kept = all(meta_c.get(k) == v for k, v in META_FIELDS.items())
check("T8e ALLE Quell-Metadaten im kombinierten Satz (kein 20%-Verlust)",
      kept, str(meta_c)[:150])
srcs_c = (c_merged.get('metadata_sources') or {}) if c_merged else {}
check("T8f Quellen-Bewertung mitgenommen",
      all(k in srcs_c for k in META_FIELDS))

# Konfliktfall: unterschiedliche Werte -> ehrlich dokumentiert
d_m3 = dict(d_m2, file_name='m3.csv',
            metadata=dict(META_FIELDS, operator_name='Ben'))
c_conf = _bcd([d_m1, d_m3])
meta_conf = (c_conf.get('metadata') or {}) if c_conf else {}
check("T8g Konflikt: beide Werte sichtbar (Anna | Ben)",
      c_conf is not None and 'Anna' in str(meta_conf.get('operator_name', ''))
      and 'Ben' in str(meta_conf.get('operator_name', '')),
      str(meta_conf.get('operator_name', '')))
check("T8h Konflikt als offene Frage dokumentiert",
      any('Metadatenkonflikt' in str(q)
          for q in (c_conf.get('open_questions') or []))
      if c_conf else False)

# ---------------------------------------------------------------------------
# T9: OP87 - Metadaten-Score des Merge: Alias/kanonische Namen zaehlen.
# Der Score zaehlt RECOMMENDED-Kurznamen (operator/instrument/
# acquisition_time), der Merge liefert kanonische Loader-Namen
# (operator_name/instrument_type/timestamp) - Score des Merge war 0-20%
# trotz vollstaendiger Quell-Metadaten. Fix: Alias-Spiegelung im
# kombinierten Satz + kanonische Namen zaehlen mit.
# ---------------------------------------------------------------------------
combine_src2 = (REPO_ROOT / "services" / "fusion_combine.py").read_text("utf-8")
ingest_src3 = (REPO_ROOT / "services" / "project_ingest.py").read_text("utf-8")
check("T9a Alias-Spiegelung im kombinierten Satz (_sync_recommended_aliases)",
      "_sync_recommended_aliases" in combine_src2)
check("T9b Score zaehlt kanonische Namen mit (OP87)",
      "RECOMMENDED_FIELD_ALIASES.get(field)" in ingest_src3)

from services.project_ingest import _assess_metadata  # noqa: E402
from services.fusion_combine import build_combined_dataset as _bcd2  # noqa: E402
META2 = {"operator_name": "Anna", "instrument_type": "diy_matchbox",
         "timestamp": "2026-10-22 07:00:00", "location": "Lab 1"}
d_s1 = {
    'usable': True, 'file_name': 's1.csv', 'target_name': 'brix',
    'preview': {'wavelengths': [900.0, 910.0, 920.0], 'intensities': []},
    'calibration_samples': [[0.5, 0.6, 0.7]] * 12,
    'reference_values': [4.0 + 0.1 * i for i in range(12)],
    'metadata': dict(META2),
    'metadata_sources': {k: 'deterministisch' for k in META2},
}
d_s2 = dict(d_s1, file_name='s2.csv',
            calibration_samples=[[0.52, 0.62, 0.72]] * 12,
            reference_values=[6.0 + 0.1 * i for i in range(12)])
c_op87 = _bcd2([d_s1, d_s2])
check("T9c Merge gebaut", c_op87 is not None)
meta_op87 = (c_op87.get('metadata') or {}) if c_op87 else {}
check("T9d Aliase gespiegelt (operator/instrument/acquisition_time)",
      all(meta_op87.get(a) for a in
          ('operator', 'instrument', 'acquisition_time')),
      str({a: meta_op87.get(a) for a in
           ('operator', 'instrument', 'acquisition_time')}))
assess = _assess_metadata([c_op87])
# OP94: Score zaehlt alle 16 CANONICAL_FIELDS. Der Merge hat 5 kanonische
# Felder (operator_name, instrument_type, timestamp, location, sample_id)
# = 5/16 = 31.2%. Vor OP94 war es 60% (3/5 recommended). Ehrlicher.
check("T9e Score des Merge: 31.2% = 5/16 canonical (OP94, humidity/temperature fehlen real)",
      assess['overall_quality_score'] == 31.2,
      f"score={assess['overall_quality_score']}")

# Vollstaendige Quelle (inkl. humidity/temperature) -> hoeherer Score
d_s3 = dict(d_s1, file_name='s3.csv',
            metadata=dict(META2, humidity='50', temperature='22'))
d_s4 = dict(d_s2, file_name='s4.csv',
            metadata=dict(META2, humidity='50', temperature='22'))
c_full = _bcd2([d_s3, d_s4])
assess_full = _assess_metadata([c_full])
# OP94: 7/16 canonical = 43.8% (operator_name, instrument_type, timestamp,
# location, sample_id, humidity, temperature). Vor OP94: 100% (5/5).
check("T9f vollstaendige Quellen -> Merge-Score 43.8% = 7/16 canonical (OP94)",
      assess_full['overall_quality_score'] == 43.8,
      f"score={assess_full['overall_quality_score']}")

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
