# -*- coding: utf-8 -*-
"""Validierung Stufe 0 (2026-10-09): Kaffee-Befunde behoben.

Covers: classification_samples ueber ALLE Zeilen (nicht nur Replica-
Block), zeilensynchrone class_labels, Konfusionsmatrix-Rendering im
Report (HTML + MD), Ausreisser-Fallback auf alle Messreihen."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import numpy as np


def _make_coffee_csv(tmp, n=120, n_classes=4):
    path = os.path.join(tmp, 'coffee.csv')
    channels = [f'{ch}_{wl}' for ch, wl in
                zip('ABCDEFGH', [610, 635, 660, 685, 710, 735, 760, 900])]
    sorten = [f'Sorte_{i}' for i in range(n_classes)]
    rows = ['Messobjekt;Counter;' + ';'.join(channels)]
    for i in range(n):
        import random as _rnd
        _rng = _rnd.Random(i)
        vals = [800 + 25 * j + (i % n_classes) * 60
                + _rng.randint(-4, 4) for j in range(8)]
        rows.append(f'{sorten[i % n_classes]};{i};' +
                    ';'.join(str(v) for v in vals))
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(rows))
    return path


def test_classification_samples_all_rows():
    """Nicht nur der Replica-Block: ALLE Zeilen werden Klassifikations-
    Samples mit zeilensynchronen Labels (Vorfall 2026-10-08)."""
    import logging
    logging.disable(logging.WARNING)
    from services.project_ingest import (_detect_wide_format,
                                         _ingest_wide_format)
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_coffee_csv(tmp, n=120)
        wide = _detect_wide_format(path)

        class Rec:
            id = 't'; name = 'c.csv'
            file_extension = '.csv'; file_category = 'spectral'
        entry = _ingest_wide_format(Rec(), path, wide)
        assert entry['metadata']['analysis_mode'] == 'classification'
        assert entry['metadata']['class_label_column'] == 'Messobjekt'
        samples = entry.get('classification_samples') or []
        labels = entry.get('classification_labels') or []
        assert len(samples) == 120, len(samples)
        assert len(labels) == 120, len(labels)
        assert labels[0] == 'Sorte_0' and labels[1] == 'Sorte_1'
        assert len(set(labels)) == 4


def test_classification_e2e_confusion_matrix():
    """LDA liefert Konfusionsmatrix ueber alle Klassen."""
    import logging
    logging.disable(logging.WARNING)
    from services.project_ingest import (_detect_wide_format,
                                         _ingest_wide_format)
    from agents.statistical_analysis_agent import StatisticalAnalysisAgent
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_coffee_csv(tmp, n=120)
        wide = _detect_wide_format(path)

        class Rec:
            id = 't'; name = 'c.csv'
            file_extension = '.csv'; file_category = 'spectral'
        entry = _ingest_wide_format(Rec(), path, wide)
        agent = StatisticalAnalysisAgent()
        agent.journal = []
        out = agent.execute({
            'spectra': {'data': entry['classification_samples']},
            'analysis_mode': 'classification',
            'class_labels': entry['classification_labels'],
        })
        assert out.data['analysis_mode'] == 'classification'
        lda = out.data['method_results']['LDA']
        cm = lda['confusion_matrix']
        assert len(cm) == 4 and len(cm[0]) == 4
        assert lda['cv_accuracy_mean'] >= 0.9
        assert set(lda['classes']) == {'Sorte_0', 'Sorte_1',
                                       'Sorte_2', 'Sorte_3'}


def test_confusion_matrix_rendering():
    """Konfusionsmatrix erscheint im HTML- und Markdown-Report."""
    import logging
    logging.disable(logging.WARNING)
    from services.project_report import (_confusion_matrix_html,
                                         _confusion_matrix_md)
    data = {
        'confusion_matrix': [[30, 0, 0], [1, 28, 1], [0, 2, 28]],
        'confusion_labels': ['Arabica', 'Robusta', 'Liberica'],
    }
    html = _confusion_matrix_html(data)
    assert 'Konfusionsmatrix' in html and 'Arabica' in html
    assert '<table' in html and '30' in html
    md = _confusion_matrix_md(data)
    assert any('Konfusionsmatrix' in l for l in md)
    assert any('Arabica' in l for l in md)
    assert any('| 30 |' in l or '| 30 |' in l.replace('  ', ' ')
               for l in md)
    # Ohne Matrix: kein Crash, keine Ausgabe
    assert _confusion_matrix_html({}) == ''
    assert _confusion_matrix_md({}) == []


def test_outlier_fallback_all_rows():
    """Wenn der Replica-Block nicht bewertbar ist, bewertet die
    Ausreisser-Analyse ALLE Messreihen (statt 'zu wenige Messungen')."""
    import logging
    logging.disable(logging.WARNING)
    from services.outlier_analysis import detect_outliers
    # 451 artige Messreihen, alle unterschiedlich (kein Replica-Block)
    rng = np.random.RandomState(0)
    rows = (1000 + rng.normal(0, 8, (60, 6))).tolist()
    verdict = detect_outliers(rows)
    assert verdict['assessable'] is True
    assert verdict['measurement_count'] == 60


def test_scree_beschriftung():
    """Der Scree-Plot erklaert den Eigenwert (Vorfall 'Was ist Eigen?')."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '..', 'services', 'pca_charts.py'),
               encoding='utf-8').read()
    assert 'erkl\u00e4rte Varianz je Hauptkomponente' in src
    student = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'services', 'student_report.py'),
                   encoding='utf-8').read()
    assert 'erkl\u00e4rte Varianz' in student


def main():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith('test_')]
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


def test_sensor_overflow_sentinels_cleaned():
    """Vorfall 2026-10-09 (Live-Validierung): Werte wie 4294967300.0
    (2**32 + 4, 32-Bit-ADC-Overflow-Sentinel) machten jede Darstellung
    unmoeglich. Der Data Preparation Agent (Datenbereinigung, MO) erkennt
    sie zentral; Ingest, Preview-Median, Klassifikations- und
    Kalibrations-Samples arbeiten nur noch mit bereinigten Werten."""
    import logging
    logging.disable(logging.WARNING)
    import pandas as pd
    from agents.data_preparation_agent import EnhancedDataPreparationAgent
    from services.project_ingest import (_detect_wide_format,
                                         _ingest_wide_format)

    channels = ['A_610', 'B_635', 'C_660', 'D_685', 'E_710', 'F_735',
                'G_760', 'H_900']
    data = {'Messobjekt': ['Sorte_A'] * 6 + ['Sorte_B'] * 6,
            'Counter': list(range(12))}
    for j, ch in enumerate(channels):
        col = [900 + 25 * j + i for i in range(12)]
        col[0 if j % 2 == 0 else 6] = 4294967300.0
        data[ch] = col
    df = pd.DataFrame(data)
    res = EnhancedDataPreparationAgent.detect_sensor_overflow(df, channels)
    assert res['saturated_rows'] == [0, 6]
    assert res['saturated_values'] == 8
    assert 4294967300.0 not in res['clean']['A_610'].tolist()

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'coffee_overflow.csv')
        df.to_csv(path, index=False, sep=';')
        wide = _detect_wide_format(path)

        class Rec:
            id = 't'; name = 'c.csv'
            file_extension = '.csv'; file_category = 'spectral'
        entry = _ingest_wide_format(Rec(), path, wide)
        assert entry['metadata']['saturated_values'] == 8
        assert entry['metadata']['overflow_rows_total'] == 2
        assert max(entry['preview']['intensities']) < 2 ** 31
        for sample in (entry.get('classification_samples') or []):
            assert max(sample) < 2 ** 31
        labels = entry.get('classification_labels') or []
        assert len(labels) == len(entry['classification_samples'])
