"""Wide-format spectrum table loader verification (real-world OEL_MK data).

Covers: channel-wavelength detection from column names (A_610/L_940),
expansion to the unified long schema (one row per sample*channel),
reference-column preservation (Brix), sample-id column detection,
metadata flags, and the guard against false positives on XY tables."""

import os
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from agents.data_preparation_agent import EnhancedDataPreparationAgent


def _agent(tmp):
    return EnhancedDataPreparationAgent(
        input_directory=tmp, output_directory=tmp, temp_directory=tmp)


def _make_wide_csv(tmp, name='wide.csv', n_samples=5):
    path = os.path.join(tmp, name)
    channels = ['A_610', 'B_680', 'C_730', 'D_760', 'E_810',
                'F_860', 'G_560', 'H_585', 'I_645', 'J_705', 'K_900', 'L_940']
    header = 'Probe;Brix;' + ';'.join(channels)
    lines = [header]
    for i in range(n_samples):
        brix = 10.0 + 0.3 * i
        values = [1000.0 + 37.0 * j + 2.5 * i for j in range(len(channels))]
        lines.append(f'Oel_{i};{brix:.1f};' + ';'.join(f'{v:.1f}' for v in values))
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return path, channels


def test_channel_wavelength_detection():
    with tempfile.TemporaryDirectory() as tmp:
        agent = _agent(tmp)
        df = pd.DataFrame({'Probe': ['a', 'b'], 'Brix': [1.0, 2.0],
                           'A_610': [1, 2], 'K_900': [3, 4],
                           'note': ['x', 'y']})
        mapping = agent._extract_channel_wavelengths(df)
        assert mapping == {'A_610': 610.0, 'K_900': 900.0}


def test_no_false_positive_on_xy_table():
    with tempfile.TemporaryDirectory() as tmp:
        agent = _agent(tmp)
        df = pd.DataFrame({'wavelength': [1000.0, 1100.0],
                           'intensity': [0.1, 0.2]})
        assert agent._extract_channel_wavelengths(df) is None


def test_wide_csv_expands_to_long_schema():
    with tempfile.TemporaryDirectory() as tmp:
        agent = _agent(tmp)
        path, channels = _make_wide_csv(tmp)
        result = agent._load_spectral_data(path)
        assert result is not None
        df = result['data']
        assert len(df) == 5 * 12
        assert set(['probe', 'wavelength', 'intensity', 'Brix']).issubset(df.columns)
        assert sorted(df['wavelength'].unique()) == sorted(
            [560.0, 585.0, 610.0, 645.0, 680.0, 705.0,
             730.0, 760.0, 810.0, 860.0, 900.0, 940.0])
        assert abs(df['Brix'].iloc[0] - 10.0) < 1e-9
        assert abs(df['intensity'].iloc[0] - 1000.0) < 1e-9
        meta = result['metadata']
        assert meta['wide_format'] is True
        assert meta['channel_count'] == 12
        assert meta['sample_count'] == 5
        assert 'Brix' in meta['reference_columns']


def test_wide_format_inside_zip_real_data():
    """The real OEL_MK dataset (uploaded zip): data + metadata txt."""
    zip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                            'django_project', 'media', 'files', 'OEL_MK.zip')
    if not os.path.exists(zip_path):
        print('  [SKIP] OEL_MK.zip not in media/files')
        return
    import zipfile
    with tempfile.TemporaryDirectory() as tmp:
        zipfile.ZipFile(zip_path).extractall(tmp)
        agent = _agent(tmp)
        train = agent._load_spectral_data(
            os.path.join(tmp, 'OEL-MK_Train(1).csv'))
        assert train is not None and len(train['data']) == 240
        assert 'Brix' in train['data'].columns
        test = agent._load_spectral_data(os.path.join(tmp, 'OEL_MK_Test.csv'))
        assert test is not None and len(test['data']) == 144


def test_metadata_txt_prose_extraction_real_data():
    zip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                            'django_project', 'media', 'files', 'OEL_MK.zip')
    if not os.path.exists(zip_path):
        print('  [SKIP] OEL_MK.zip not in media/files')
        return
    import zipfile
    with tempfile.TemporaryDirectory() as tmp:
        zipfile.ZipFile(zip_path).extractall(tmp)
        agent = _agent(tmp)
        meta_path = os.path.join(tmp, 'Öl_Meta.txt')
        lines = open(meta_path, encoding='utf-8', errors='replace').read().splitlines()
        prose = agent._extract_prose_metadata(lines)
        assert prose.get('operator_name') == 'Yvonne'
        assert prose.get('instrument_type') == 'Triadsensor'
        assert prose.get('temperature') == '25'
        assert prose.get('humidity') == '88'


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
