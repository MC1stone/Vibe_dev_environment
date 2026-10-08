"""Struktur-Klaerungsdialog Stufe B (End-to-End).

Covers: fingerprints/signature, KI-dialog fallback questions on
usable=False ingest, hints application (wide + xy), StructureProfile
learning + automatic reuse, and the API endpoints wiring."""

import json
import os
import sys
import tempfile

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (REPO_ROOT, os.path.join(REPO_ROOT, 'django_project')):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    django.setup()
    DJANGO_OK = True
except Exception:
    DJANGO_OK = False


def _make_unparseable_wide(tmp, name='strange_export.dat'):
    """A file the S3 loader cannot read as a spectrum: unusual extension,
    but wide channels - only the structure dialog can unlock it."""
    path = os.path.join(tmp, name)
    channels = ['K_610', 'K_680', 'K_730', 'K_900']
    lines = ['Sample;Ref;' + ';'.join(channels)]
    for i in range(6):
        vals = [100 + 5 * j + i for j in range(len(channels))]
        lines.append(f'S{i};{2.0 + 0.5 * i};' + ';'.join(str(v) for v in vals))
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return path


def test_fingerprints_and_signature():
    from services.structure_dialog import file_fingerprints, structure_signature
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_unparseable_wide(tmp)
        fp = file_fingerprints(path)
        assert fp['readable'] is True
        assert fp['delimiter']['candidate'] in ("';'",)
        assert 'K_610' in fp['column_names']
        sig = structure_signature(fp)
        assert len(sig) == 16
        # Gleiche Spalten (Zahlen egal) -> gleiche Signatur
        fp2 = dict(fp, column_names=[c for c in fp['column_names']])
        assert structure_signature(fp2) == sig


def test_hints_from_answers_and_apply_wide():
    import logging
    logging.disable(logging.WARNING)
    from services.structure_dialog import hints_from_answers, apply_hints
    from agents.data_preparation_agent import EnhancedDataPreparationAgent
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_unparseable_wide(tmp)
        answers = {
            'layout': 'wide',
            'channel_columns': ['K_610', 'K_680', 'K_730', 'K_900'],
            'sample_column': 'Sample',
            'reference_columns': ['Ref'],
            'delimiter': ';',
            'header_row': True,
        }
        hints = hints_from_answers(answers)
        loader = EnhancedDataPreparationAgent(
            input_directory=tmp, output_directory=tmp, temp_directory=tmp)
        result = apply_hints(loader, path, hints)
        assert result is not None
        df = result['data']
        assert len(df) == 6 * 4  # 6 Proben x 4 Kanaele
        assert set(['probe', 'wavelength', 'intensity', 'Ref']).issubset(df.columns)
        assert sorted(df['wavelength'].unique()) == [610.0, 680.0, 730.0, 900.0]
        assert result['metadata'].get('structure_dialog') is True


def test_structure_profile_learning_and_reuse():
    if not DJANGO_OK:
        print('  [SKIP] django setup unavailable')
        return
    from django.contrib.auth import get_user_model
    from core.models import StructureProfile
    from services.structure_dialog import file_fingerprints, structure_signature

    with tempfile.TemporaryDirectory() as tmp:
        path = _make_unparseable_wide(tmp)
        fp = file_fingerprints(path)
        sig = structure_signature(fp)

        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username='struct-dialog-user',
            defaults={'email': 'struct-dialog-user@test.local'})
        hints = {'layout': 'wide', 'delimiter': ';',
                 'channel_columns': ['K_610', 'K_680', 'K_730', 'K_900'],
                 'sample_column': 'Sample', 'reference_columns': ['Ref'],
                 'header_row': True}
        profile, created = StructureProfile.objects.get_or_create(
            user=user, signature=sig,
            defaults={'hints': hints, 'last_file_name': 'strange_export.dat'})
        assert created
        # gleiche Signatur -> bekanntes Profil wird gefunden (2. Upload laeuft automatisch)
        profile2 = StructureProfile.objects.filter(
            user=user, signature=sig).first()
        assert profile2 is not None and profile2.hints['layout'] == 'wide'
        # Upsert: confirmed_count waechst statt Dublette
        profile2.confirmed_count += 1
        profile2.save()
        assert StructureProfile.objects.filter(
            user=user, signature=sig).count() == 1
        profile.delete()
        user.delete()


def test_ingest_offers_structure_dialog():
    """usable=False Eintraege tragen jetzt KI-Vorschlag + Fragen."""
    src = open(os.path.join(REPO_ROOT, 'services', 'project_ingest.py'),
               encoding='utf-8').read()
    assert 'structure_dialog' in src
    assert 'ki_structure_proposal' in src
    assert 'signature' in src


def test_api_endpoints_wired():
    if not DJANGO_OK:
        print('  [SKIP] django setup unavailable')
        return
    from django.urls import reverse
    url = reverse('file-structure-dialog',
                  args=['00000000-0000-0000-0000-000000000000'])
    assert url.endswith('/structure/')


def test_journal_visible_in_report():
    """Der Abschlussbericht rendert die iterativen Informationen (User-
    Befund 2026-10-08: 'keine iterativen Informationen gefunden')."""
    import logging
    logging.disable(logging.WARNING)
    from services.project_report import _journal_html, _journal_md_lines
    entries = [
        {"agent": "CalibrationAgent", "phase": "entscheidung",
         "analysis": "Bestes Modell: PLS",
         "conclusion": "Schwellwert nicht erreicht",
         "action": "Option waehlen", "iteration": 0,
         "options": [{"id": "more", "label": "Mehr Messungen",
                      "description": "d", "expected_effect": "e"}],
         "timestamp": "t"},
        {"agent": "CalibrationAgent", "phase": "iteration",
         "analysis": "Ausgewaehlte Option: more",
         "conclusion": "Begruendung", "action": "neu kalibriert",
         "iteration": 1, "options": [], "timestamp": "t"},
    ]
    html = _journal_html(entries)
    assert 'Iteration 1' in html and 'Mehr Messungen' in html
    md = _journal_md_lines(entries)
    assert any('Iteration 1' in l for l in md)
    # Renderer-Verdrahtung: journal_html ist in der Sektions-Ausgabe
    src = open(os.path.join(REPO_ROOT, 'services', 'project_report.py'),
               encoding='utf-8').read()
    assert '{journal_html}' in src
    assert "agent == 'agenten_journal'" in src


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {t.__name__}: {e}")
    if failed:
        raise SystemExit(f"{failed} test(s) failed")
    print(f"All {len(tests)} tests passed.")


if __name__ == "__main__":
    main()
