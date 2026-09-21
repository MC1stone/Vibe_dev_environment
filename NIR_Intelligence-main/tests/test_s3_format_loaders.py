"""S3 verification: loader test matrix for format-agnostic spectral import.

Creates synthetic files (SPC binary, MATLAB .mat, CSV, TXT, JSON) and verifies
that EnhancedDataPreparationAgent._load_spectral_data loads each one into the
unified spectral data schema (data/metadata/format/wavelength_column/intensity_column).
"""
import json
import os
import struct
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from agents.data_preparation_agent import EnhancedDataPreparationAgent


def make_spc(path, x_start, x_end, y_values):
    """Write a minimal single-file SPC (Galactic format, little-endian).
    Fields are written at the fixed offsets the loader reads."""
    n = len(y_values)
    with open(path, 'wb') as f:
        def put(offset, fmt, value):
            f.seek(offset)
            f.write(struct.pack(fmt, value))

        f.truncate(0)
        f.write(b'\x00' * 512)
        put(0, '<B', 0)          # flag word
        f.seek(2)
        f.write(b'SP')           # version magic
        put(34, '<h', -1)         # subheader: evenly spaced X (single file)
        put(176, '<B', 3)         # x units: nanometers
        put(177, '<B', 0)         # y units: arbitrary
        put(190, '<l', 0)         # wplanes
        put(224, '<d', x_start)
        put(236, '<d', x_end)
        put(244, '<l', n)         # number of points
        f.seek(512)
        f.write(np.asarray(y_values, dtype='<f4').tobytes())


def main():
    agent = EnhancedDataPreparationAgent(
        input_directory=tempfile.gettempdir(),
        output_directory=tempfile.gettempdir(),
        temp_directory=tempfile.gettempdir(),
    )

    tmp = tempfile.mkdtemp(prefix='s3_loader_tests_')
    results = []

    def check(name, loaded, expect_n, expect_x=None, tol=1e-6):
        ok = loaded is not None
        detail = {}
        if ok and expect_n > 0:
            df = loaded['data']
            ok = len(df) == expect_n and set(['wavelength', 'intensity']).issubset(df.columns)
            if ok and expect_x is not None:
                ok = abs(float(df['wavelength'].iloc[0]) - expect_x) < tol
            detail = {'format': loaded.get('format'),
                      'n': len(df),
                      'metadata_keys': sorted(loaded.get('metadata', {}).keys())[:5]}
        results.append((name, ok, detail))
        status = 'PASS' if ok else 'FAIL'
        print(f'[{status}] {name} {detail if detail else ""}')

    # T1: SPC binary loader
    y = np.linspace(0.1, 0.9, 50)
    spc_path = os.path.join(tmp, 'test_spectrum.spc')
    make_spc(spc_path, 400.0, 2500.0, y)
    check('T1 SPC (binary Galactic)', agent._load_spectral_data(spc_path), 50, expect_x=400.0)

    # T2: SPC invalid magic rejected gracefully
    bad_path = os.path.join(tmp, 'bad.spc')
    with open(bad_path, 'wb') as f:
        f.write(b'\x00XX\x00' + b'\x00' * 600)
    bad_loaded = agent._load_spectral_data(bad_path)
    ok = bad_loaded is None
    print(f'[{"PASS" if ok else "FAIL"}] T2 SPC invalid magic -> None')
    results.append(('T2 SPC invalid magic -> None', ok, {}))

    # T3: MATLAB loader (named arrays)
    from scipy.io import savemat
    mat_path = os.path.join(tmp, 'test.mat')
    savemat(mat_path, {'wavelength_nm': np.linspace(1000, 2500, 40),
                       'absorbance': np.linspace(0.2, 0.8, 40)})
    check('T3 MAT named arrays', agent._load_spectral_data(mat_path), 40, expect_x=1000.0)

    # T4: MATLAB loader (single 2-column array)
    mat2_path = os.path.join(tmp, 'test2.mat')
    combined = np.column_stack([np.linspace(800, 1200, 30), np.linspace(0.1, 0.5, 30)])
    savemat(mat2_path, {'spectrum': combined})
    check('T4 MAT 2-column array', agent._load_spectral_data(mat2_path), 30, expect_x=800.0)

    # T5: CSV regression
    csv_path = os.path.join(tmp, 'test.csv')
    pd.DataFrame({'wavelength': np.linspace(400, 700, 20),
                  'intensity': np.linspace(0, 1, 20)}).to_csv(csv_path, index=False)
    check('T5 CSV regression', agent._load_spectral_data(csv_path), 20, expect_x=400.0)

    # T6: TXT regression
    txt_path = os.path.join(tmp, 'test.txt')
    with open(txt_path, 'w') as f:
        for w, i in zip(np.linspace(500, 900, 15), np.linspace(0, 0.5, 15)):
            f.write(f'{w} {i}\n')
    check('T6 TXT regression', agent._load_spectral_data(txt_path), 15, expect_x=500.0)

    # T7: JSON regression
    json_path = os.path.join(tmp, 'test.json')
    with open(json_path, 'w') as f:
        json.dump({'wavelength': list(np.linspace(1100, 1400, 25)),
                   'intensity': list(np.linspace(0.1, 0.9, 25))}, f)
    loaded = agent._load_spectral_data(json_path)
    ok = loaded is not None and len(loaded['data']) == 25
    print(f'[{"PASS" if ok else "FAIL"}] T7 JSON regression')
    results.append(('T7 JSON regression', ok, {}))

    failed = [r for r in results if not r[1]]
    print(f'\n{len(results) - len(failed)}/{len(results)} tests passed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
