"""S5 verification: spectrum similarity engine and napari integration.

Tests the nearest-neighbour comparison engine (FAISS backend when installed,
exact numpy fallback otherwise) against the unified spectral schema, the
optional Qdrant embedding backend state handling, and the docker-compose
integration of the napari visualization service.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from services.spectrum_similarity import (
    FAISS_AVAILABLE,
    QdrantSimilarityService,
    SpectrumSimilarityEngine,
    create_similarity_service,
)

results = []


def check(name, ok, detail=''):
    results.append((name, ok))
    print(f'[{"PASS" if ok else "FAIL"}] {name} {detail}')


def make_spectrum(wavelengths, intensities, sample_id=None, source_file=None):
    return {
        'data': pd.DataFrame({'wavelength': wavelengths, 'intensity': intensities}),
        'source_file': source_file,
        'format': 'test',
        'wavelength_column': 'wavelength',
        'intensity_column': 'intensity',
        'metadata': {'sample_id': sample_id} if sample_id else {},
    }


# T1: identical spectrum found with distance ~0 as best match
engine = SpectrumSimilarityEngine()
refs = [
    make_spectrum([410, 435, 460], [1.0, 2.0, 3.0], sample_id='ref-a'),
    make_spectrum([410, 435, 460], [10.0, 20.0, 30.0], sample_id='ref-b'),
    make_spectrum([410, 435, 460], [5.0, 5.0, 5.0], sample_id='ref-c'),
]
added = engine.add_references(refs)
check('T1a add_references returns count', added == 3, f'added={added}')
query = make_spectrum([410, 435, 460], [1.0, 2.0, 3.0], sample_id='query')
matches = engine.find_similar(query)
check('T1b identical spectrum -> best match, distance ~0',
      len(matches) >= 1 and matches[0].reference_id == 'ref-a' and matches[0].distance < 1e-6,
      f'best={matches[0].reference_id if matches else None} d={matches[0].distance if matches else None}')

# T2: ranking of multiple references (query closer to ref-b than to ref-c)
query2 = make_spectrum([410, 435, 460], [10.0, 19.0, 29.0])
matches2 = engine.find_similar(query2, top_k=3)
ids = [m.reference_id for m in matches2]
check('T2 ranking: closest reference first', ids[0] == 'ref-b' and ids[1] == 'ref-c' and ids[2] == 'ref-a',
      f'order={ids}')

# T3: cosine metric ordering matches expectation
cos_engine = SpectrumSimilarityEngine(config={'metric': 'cosine'})
cos_engine.add_references([
    make_spectrum([410, 435, 460], [1.0, 2.0, 3.0], sample_id='parallel'),
    make_spectrum([410, 435, 460], [3.0, 2.0, 1.0], sample_id='inverse'),
])
cos_matches = cos_engine.find_similar(make_spectrum([410, 435, 460], [2.0, 4.0, 6.0]))
check('T3 cosine metric: parallel spectrum ranks first',
      cos_matches[0].reference_id == 'parallel' and cos_matches[0].similarity > 0.99,
      f'similarity={cos_matches[0].similarity:.4f}')

# T4: backend status (FAISS preferred when installed, numpy fallback otherwise)
status = engine.status()
check('T4 backend status consistent',
      status['backend'] == ('faiss' if FAISS_AVAILABLE else 'numpy')
      and status['num_references'] == 3 and status['dimension'] == 3,
      f'backend={status["backend"]} faiss_available={FAISS_AVAILABLE}')

# T5: FAISS and numpy backends produce identical rankings when FAISS exists
if FAISS_AVAILABLE:
    e_faiss = SpectrumSimilarityEngine()
    e_faiss.add_references(refs)
    e_numpy = SpectrumSimilarityEngine()
    e_numpy._reference_vectors = None
    numpy_engine = SpectrumSimilarityEngine()
    numpy_engine.add_references(refs)
    # force numpy path by bypassing the faiss index
    saved = numpy_engine._faiss_index
    numpy_engine._faiss_index = None
    m_faiss = e_faiss.find_similar(query2, top_k=3)
    m_numpy = numpy_engine.find_similar(query2, top_k=3)
    same = ([m.reference_id for m in m_faiss] == [m.reference_id for m in m_numpy]
            and all(abs(a.distance - b.distance) < 1e-3 for a, b in zip(m_faiss, m_numpy)))
    check('T5 faiss and numpy backends agree', same)
    numpy_engine._faiss_index = saved
else:
    check('T5 numpy fallback active (faiss not installed in this environment)', True)

# T6: edge cases - empty reference set, dimension mismatch, unusable query
empty_engine = SpectrumSimilarityEngine()
check('T6a empty reference set -> empty result', empty_engine.find_similar(query) == [])
try:
    engine.add_references([make_spectrum([410, 435], [1.0, 2.0])])
    check('T6b inconsistent reference dimensions -> ValueError', False)
except ValueError:
    check('T6b inconsistent reference dimensions -> ValueError', True)
try:
    engine.find_similar({'data': pd.DataFrame({'other': [1, 2, 3]})})
    check('T6c unusable query -> ValueError', False)
except ValueError:
    check('T6c unusable query -> ValueError', True)

# T7: reference ids from metadata/sample_id and explicit list
id_engine = SpectrumSimilarityEngine()
id_engine.add_references([refs[0], refs[1]], reference_ids=['explicit-1', 'explicit-2'])
m = id_engine.find_similar(make_spectrum([410, 435, 460], [10.5, 20.0, 30.0]))
check('T7 explicit reference ids respected', m[0].reference_id == 'explicit-2')

# T8: dict-of-arrays schema (S4 ESP32 adapter form) works too
dict_spectrum = {
    'data': {'wavelength': [410, 435, 460], 'intensity': [1.0, 2.0, 3.0]},
    'wavelength_column': 'wavelength',
    'intensity_column': 'intensity',
}
dict_engine = SpectrumSimilarityEngine()
dict_engine.add_references([dict_spectrum])
dm = dict_engine.find_similar(dict_spectrum)
check('T8 dict-of-arrays schema supported', len(dm) == 1 and dm[0].distance < 1e-6)

# T9: S4 adapter output compatibility - SparkFun Triad 18-channel spectra
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from devices.sparkfun_triad import SparkFunTriadAdapter, TRIAD_WAVELENGTHS

triad = SparkFunTriadAdapter()
triad.connect()
triad_spectrum = triad.acquire_measurement({'channel_payload': {
    'channels': {f'{wl:g}': float(i) for i, wl in enumerate(TRIAD_WAVELENGTHS)},
    'sample_id': 'triad-ref',
}})
triad_engine = SpectrumSimilarityEngine()
triad_engine.add_references([triad_spectrum])
same_again = triad.acquire_measurement({'channel_payload': {
    'channels': {f'{wl:g}': float(i) for i, wl in enumerate(TRIAD_WAVELENGTHS)},
    'sample_id': 'triad-query',
}})
tm = triad_engine.find_similar(same_again)
check('T9 S4 adapter output (SparkFun Triad, 18 channels) comparable',
      len(tm) == 1 and tm[0].reference_id == 'triad-ref' and tm[0].distance < 1e-4)

# T10: Qdrant backend - deferred state without qdrant-client, never crashes
qdrant = QdrantSimilarityService(config={'host': 'localhost', 'port': 6333})
state = qdrant.connect()
check('T10 Qdrant backend graceful (connected or deferred, no crash)',
      isinstance(state, dict) and 'connected' in state,
      f'connected={state.get("connected")} reason={state.get("reason", "-")}')

# T11: factory returns a working engine
factory_engine = create_similarity_service(config={'top_k': 2})
factory_engine.add_references(refs)
fm = factory_engine.find_similar(query)
check('T11 create_similarity_service factory', isinstance(fm, list) and len(fm) <= 2)

# T12: docker-compose napari integration (from HANDHELD/napari_app)
compose_path = Path(__file__).resolve().parent.parent / 'docker-compose.yml'
compose_text = compose_path.read_text()
check('T12a napari service in docker-compose.yml',
      'napari_server:' in compose_text and '8002' in compose_text)
prod_path = Path(__file__).resolve().parent.parent / 'docker-compose.prod.yml'
prod_text = prod_path.read_text() if prod_path.exists() else ''
check('T12b napari service in docker-compose.prod.yml',
      'napari_server:' in prod_text)

failed = [r for r in results if not r[1]]
print(f'\n{len(results) - len(failed)}/{len(results)} tests passed')
sys.exit(1 if failed else 0)
