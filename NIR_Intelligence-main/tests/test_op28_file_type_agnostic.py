"""OP28 verification: file-type agnostic data loading (MO 1).

Every file type must be accepted and every file must be searched for
measurement values and metadata - no extension whitelists anywhere in
the upload -> ingest path. Offline test matrix (repo check() style):

T1  loader accepts structured formats without a dedicated parser entry
    (.hdf5 alias, YAML, XML)
T2  loader accepts tabular formats that never had a loader (.xlsx,
    .parquet, .feather)
T3  archives (ZIP) are extracted and scanned recursively
T4  unknown extensions and files without an extension load by content
T5  metadata is found in ANY text file (aliases map to canonical fields)
T6  the batch discovery no longer skips unknown extensions
T7  honest None for a file with no extractable measurements
T8  MCP ingest: spectral pair extraction (regression) + plausibility
T9  MCP ingest: wide measurement matrix (channel columns, no axis)
T10 the Django upload view has no extension whitelist anymore
"""
import json
import os
import struct
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

PASS = 0
FAIL = 0
FAILED = []


def check(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'[PASS] {name}')
    else:
        FAIL += 1
        FAILED.append(name)
        print(f'[FAIL] {name} {detail}')


def skip(name, reason):
    """Optional-dependency guard: the loaders degrade gracefully without
    h5py/openpyxl/pyarrow (the content-driven chain just skips the stage),
    so the matrix skips those checks instead of failing on import."""
    print(f'[SKIP] {name} ({reason})')


import numpy as np
import pandas as pd

from agents.data_preparation_agent import EnhancedDataPreparationAgent

tmp = tempfile.mkdtemp(prefix='op28_agnostic_')
agent = EnhancedDataPreparationAgent(
    input_directory=tmp, output_directory=tmp, temp_directory=tmp)

wl = [float(w) for w in np.linspace(900, 1300, 10)]
it = [float(v) for v in np.linspace(1000, 5000, 10)]


def load(path):
    return agent._load_spectral_data(str(path))


def has_pair(result, n=10):
    if not result or result.get('data') is None:
        return False
    df = result['data']
    wc = result.get('wavelength_column')
    ic = result.get('intensity_column')
    if wc not in df.columns or ic not in df.columns:
        return False
    return len(df.dropna(subset=[wc, ic])) >= n


# ---------------------------------------------------------------- T1
try:
    import h5py
except ImportError:
    h5py = None
if h5py is not None:
    hdf5_path = os.path.join(tmp, 's.hdf5')
    with h5py.File(hdf5_path, 'w') as f:
        f.create_dataset('spectra', data=np.column_stack([wl, it]))
    check('T1a .hdf5 alias loads (was rejected before OP28)', has_pair(load(hdf5_path)))
else:
    skip('T1a .hdf5 alias loads (was rejected before OP28)', 'h5py not installed')

yaml_path = os.path.join(tmp, 's.yaml')
with open(yaml_path, 'w', encoding='utf-8') as f:
    f.write('wavelength: %s\nintensity: %s\n' % (wl, it))
check('T1b YAML loads with wavelength/intensity lists', has_pair(load(yaml_path)))

xml_path = os.path.join(tmp, 's.xml')
rows = '\n'.join('<point wavelength="%s" intensity="%s"/>' % (w, i)
                for w, i in zip(wl, it))
with open(xml_path, 'w', encoding='utf-8') as f:
    f.write('<spectrum>\n%s\n</spectrum>\n' % rows)
check('T1c XML (attribute rows) loads', has_pair(load(xml_path)))

# ---------------------------------------------------------------- T2
try:
    import openpyxl  # noqa: F401
except ImportError:
    openpyxl = None
if openpyxl is not None:
    xlsx_path = os.path.join(tmp, 's.xlsx')
    pd.DataFrame({'wavelength': wl, 'intensity': it}).to_excel(xlsx_path, index=False)
    r = load(xlsx_path)
    check('T2a XLSX loads (all sheets scanned)', has_pair(r) and r['metadata'].get('excel_sheet'),
          f"r={bool(r)}")
else:
    skip('T2a XLSX loads (all sheets scanned)', 'openpyxl not installed')

try:
    import pyarrow  # noqa: F401
except ImportError:
    pyarrow = None
if pyarrow is not None:
    parquet_path = os.path.join(tmp, 's.parquet')
    pd.DataFrame({'wavelength': wl, 'intensity': it}).to_parquet(parquet_path)
    check('T2b Parquet loads', has_pair(load(parquet_path)))

    feather_path = os.path.join(tmp, 's.feather')
    pd.DataFrame({'wavelength': wl, 'intensity': it}).to_feather(feather_path)
    check('T2c Feather loads', has_pair(load(feather_path)))
else:
    skip('T2b Parquet loads', 'pyarrow not installed')
    skip('T2c Feather loads', 'pyarrow not installed')

# ---------------------------------------------------------------- T3
zip_path = os.path.join(tmp, 's.zip')
inner_path = os.path.join(tmp, 'inner.csv')
pd.DataFrame({'wavelength': wl, 'intensity': it}).to_csv(inner_path, index=False)
with zipfile.ZipFile(zip_path, 'w') as z:
    z.write(inner_path, 'inner.csv')
r = load(zip_path)
check('T3a ZIP is extracted and the nested CSV loads', has_pair(r) and r.get('extracted_from'),
      f"r={bool(r)} extracted_from={(r or {}).get('extracted_from')}")

# ---------------------------------------------------------------- T4
unknown_path = os.path.join(tmp, 's.xyz')
with open(unknown_path, 'w', encoding='utf-8') as f:
    f.write('wavelength,intensity\n'
            + '\n'.join('%s,%s' % (w, i) for w, i in zip(wl, it)))
check('T4a unknown extension loads by content', has_pair(load(unknown_path)))

noext_path = os.path.join(tmp, 'noext')
with open(noext_path, 'w', encoding='utf-8') as f:
    f.write('wavelength,intensity\n'
            + '\n'.join('%s,%s' % (w, i) for w, i in zip(wl, it)))
check('T4b file without extension loads by content', has_pair(load(noext_path)))

# ---------------------------------------------------------------- T5
meta_path = os.path.join(tmp, 'meta.dat')
with open(meta_path, 'w', encoding='utf-8') as f:
    f.write('# Sample: Tomate T4\n# Operator: Martin\ndevice=SpectroMark1\n'
            '900,15200\n925,18450\n950,22100\n')
r = load(meta_path)
meta = (r or {}).get('metadata') or {}
check('T5a measurements found in an unknown text file', has_pair(r, n=3), f'r={bool(r)}')
check('T5b sample metadata maps to the canonical sample_id',
      meta.get('sample_id') == 'Tomate T4', f'meta={meta}')
check('T5c device metadata maps to the canonical instrument_type',
      meta.get('instrument_type') == 'SpectroMark1', f'meta={meta}')
check('T5d operator metadata maps to the canonical operator_name',
      meta.get('operator_name') == 'Martin', f'meta={meta}')

# ---------------------------------------------------------------- T6
check('T6a _get_file_type returns UNKNOWN instead of None',
      agent._get_file_type(unknown_path) is not None,
      f"value={agent._get_file_type(unknown_path)}")

# ---------------------------------------------------------------- T7
garbage_path = os.path.join(tmp, 'garbage.bin')
with open(garbage_path, 'wb') as f:
    f.write(os.urandom(4096))
check('T7a binary noise returns None (honest, no invented values)',
      load(garbage_path) is None)

# ---------------------------------------------------------------- T8 (MCP ingest)
from agents.mcp_agent import MCPAgent

mcp = MCPAgent()

german_csv = os.path.join(tmp, 'diy.csv')
with open(german_csv, 'w', encoding='utf-8') as f:
    f.write('Messung;Intensität (counts, ADU)\nDaten;Rohwerte\n'
            '900;15.200,00\n925;18.450,00\n950;22.100,00\n1000;29.400,00\n')
out = mcp.execute({'operation': 'ingest', 'file_path': german_csv})
d = out.data
check('T8a MCP ingest regression (German DIY CSV)',
      d.get('status') == 'ok' and d['prepared_dataset']['num_points'] == 4
      and d['prepared_dataset']['intensities'][0] == 15200.0,
      f"status={d.get('status')} err={d.get('error')}")

json_path = os.path.join(tmp, 's.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump({'wavelength': [900, 925], 'intensity': [15200, 18450]}, f)
out = mcp.execute({'operation': 'ingest', 'file_path': json_path})
check('T8b MCP ingest regression (JSON, short spectrum)',
      out.data.get('status') == 'ok'
      and out.data['prepared_dataset']['num_points'] == 2,
      f"status={out.data.get('status')} err={out.data.get('error')}")

# ---------------------------------------------------------------- T9 (wide matrix)
wide_path = os.path.join(tmp, 'wide.csv')
pd.DataFrame({
    'Brix': [4.3, 5.1, 6.2, 8.1],
    'ch_410': [152, 184, 221, 258],
    'ch_500': [294, 331, 368, 402],
    'ch_600': [435, 448, 429, 391],
}).to_csv(wide_path, index=False)
out = mcp.execute({'operation': 'ingest', 'file_path': wide_path})
d = out.data
prep = d.get('prepared_dataset') or {}
check('T9a MCP ingest extracts the wide measurement matrix',
      d.get('status') == 'ok' and prep.get('num_channels') == 4
      and prep.get('num_measurements') == 4,
      f"prep={ {k: v for k, v in prep.items() if k != 'measurements'} }")
check('T9b wide layout is flagged in the metadata',
      (d.get('metadata') or {}).get('dataset_layout') == 'wide_measurement_matrix',
      f"meta={d.get('metadata')}")
check('T9c Brix is not misread as a wavelength axis',
      prep.get('wavelength_unit') == 'channel_index', f"prep={prep.get('wavelength_unit')}")

# ---------------------------------------------------------------- T10 (upload whitelist removed)
views = (PROJECT / 'django_project' / 'api' / 'views.py').read_text(encoding='utf-8')
check('T10a no extension whitelist in the upload view',
      'valid_extensions' not in views and 'Invalid file type' not in views)

analysis_js = (PROJECT / 'django_project' / 'static' / 'js' / 'analysis.js').read_text(encoding='utf-8')
check('T10b analysis page accepts any file type',
      'any file type' in analysis_js and '.json, .csv or .txt' not in analysis_js)

spectra_tpl = (PROJECT / 'django_project' / 'templates' / 'spectra.html').read_text(encoding='utf-8')
check('T10c spectra page no longer restricts the file input',
      'accept=".csv' not in spectra_tpl)

# ---------------------------------------------------------------- summary
print()
print(f'OP28 file-type agnostic matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED:', FAILED)
    sys.exit(1)
sys.exit(0)
