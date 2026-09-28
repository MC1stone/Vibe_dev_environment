"""FL2 verification: federated calibration over real PLS models.

Checks that clients train a genuine PLS calibration (scikit-learn) on
their non-IID shards, transmit only hyperplane parameters (coefficients +
intercept - never spectra), aggregate example-weighted (FedAvg), and
converge: the federated global model must beat the average local-only
model on pooled data and approach the pooled (centralised) PLS optimum.
Sharding uses the OP15 provenance dimensions (instrument_type /
sample_type). sklearn-optional: graceful deferral without scikit-learn.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

results = []


def check(name, ok, detail=''):
    results.append((name, ok))
    print(f'[{"PASS" if ok else "FAIL"}] {name} {detail}')


PROJECT = Path(__file__).resolve().parent.parent


def make_group_spectra(n, channels, offset, seed):
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, size=(n, channels)) + offset
    true_w = rng.normal(0, 1, size=channels)
    y = x @ true_w + rng.normal(0, 0.05, size=n)
    return x, y


from services.federated_calibration import (
    SKLEARN_AVAILABLE,
    CalibrationShard,
    FederatedCalibrationService,
    FederatedPLSAggregator,
    PLSCalibrationClient,
    shard_spectra_database,
)

check('T1a sklearn availability flag exposed', isinstance(SKLEARN_AVAILABLE, bool))

# T2: aggregator contract (example-weighted FedAvg of hyperplanes)
agg = FederatedPLSAggregator()
coef, intercept = agg.aggregate([
    {"coefficients": np.array([1.0, 0.0]), "intercept": 2.0, "num_examples": 30},
    {"coefficients": np.array([0.0, 1.0]), "intercept": 4.0, "num_examples": 10},
])
check('T2a example-weighted aggregation (0.75/0.25)',
      np.allclose(coef, [0.75, 0.25]) and abs(intercept - 2.5) < 1e-12)
check('T2b empty aggregation returns None', agg.aggregate([]) is None)
try:
    FederatedPLSAggregator(strategy='unknown')
    check('T2c unknown strategy rejected', False)
except ValueError:
    check('T2c unknown strategy rejected', True)
try:
    agg.aggregate([
        {"coefficients": np.zeros(2), "intercept": 0.0, "num_examples": 1},
        {"coefficients": np.zeros(3), "intercept": 0.0, "num_examples": 1},
    ])
    check('T2d shape mismatch rejected', False)
except ValueError:
    check('T2d shape mismatch rejected', True)

if SKLEARN_AVAILABLE:
    # T3: local PLS client - real fit, parameter-only payload
    x_a, y_a = make_group_spectra(40, 6, 0.0, 1)
    x_b, y_b = make_group_spectra(30, 6, 2.0, 2)
    shard_a = CalibrationShard(x=x_a, y=y_a, instrument_type='sparkfun_triad',
                               sample_type='tomato')
    shard_b = CalibrationShard(x=x_b, y=y_b, instrument_type='esp32_s3_camera',
                               sample_type='oil')
    check('T3a shard group is the provenance pair',
          shard_a.group == 'sparkfun_triad:tomato')

    client = PLSCalibrationClient('sparkfun_triad:tomato', shard_a, n_components=2)
    coef_a, intercept_a, n_a, metrics_a = client.fit_local()
    check('T3b local fit returns coefficient vector of channel dimension',
          coef_a.shape == (6,) and n_a == 40)
    check('T3c local fit reports group and local_rmse',
          metrics_a['group'] == 'sparkfun_triad:tomato'
          and metrics_a['local_rmse'] >= 0)
    check('T3d payload carries no raw spectrum row',
          not any(np.array_equal(coef_a, row) for row in x_a[:5]))

    # T4: federated round - global model beats local-only models on pooled data
    svc = FederatedCalibrationService(n_components=2)
    result = svc.run_round([shard_a, shard_b], reference_x=np.vstack([x_a, x_b]))
    check('T4a round completes with both provenance clients',
          set(result.participating_clients) ==
          {'sparkfun_triad:tomato', 'esp32_s3_camera:oil'})
    check('T4b total examples across shards', result.total_examples == 70)
    check('T4c result dict carries privacy note',
          'parameter updates' in result.to_dict()['privacy_note'])

    x_pool = np.vstack([x_a, x_b])
    y_pool = np.concatenate([y_a, y_b])
    fed_rmse = svc.global_rmse(x_pool, y_pool)

    # local-only baselines evaluated on the POOLED data (non-IID penalty)
    local_only_a = PLSCalibrationClient('a', shard_a, n_components=2)
    coef_la, int_la, _, _ = local_only_a.fit_local()
    rmse_la = float(np.sqrt(np.mean((x_pool @ coef_la + int_la - y_pool) ** 2)))
    check('T4d federated global model beats a local-only model on pooled data',
          fed_rmse < rmse_la, f'fed={fed_rmse:.3f} < local_only={rmse_la:.3f}')

    # T5: convergence toward the pooled (centralised) PLS optimum
    from sklearn.cross_decomposition import PLSRegression
    pooled = PLSRegression(n_components=2).fit(x_pool, y_pool)
    pooled_coef = np.asarray(pooled.coef_).ravel()
    pooled_intercept = float(np.mean(y_pool - x_pool @ pooled_coef))
    pooled_rmse = float(np.sqrt(np.mean(
        (x_pool @ pooled_coef + pooled_intercept - y_pool) ** 2)))
    check('T4e federated model approaches the pooled optimum',
          fed_rmse <= pooled_rmse * 1.5,
          f'fed={fed_rmse:.3f} pooled={pooled_rmse:.3f}')

    # T6: OP15-style database sharding (provenance dimensions)
    records = [
        {'intensities': x_a[0], 'reference_value': float(y_a[0]),
         'instrument_type': 'sparkfun_triad', 'sample_type': 'tomato'},
        {'intensities': x_a[1], 'reference_value': float(y_a[1]),
         'instrument_type': 'sparkfun_triad', 'sample_type': 'tomato'},
        {'intensities': x_b[0], 'reference_value': float(y_b[0]),
         'instrument_type': 'esp32_s3_camera', 'sample_type': 'oil'},
        {'intensities': x_b[1], 'reference_value': float(y_b[1]),
         'instrument_type': 'esp32_s3_camera', 'sample_type': 'oil'},
        {'intensities': x_b[2], 'reference_value': None,
         'instrument_type': 'esp32_s3_camera', 'sample_type': 'oil'},
    ]
    shards = shard_spectra_database(records, dimension='instrument_type')
    groups = sorted(s.group for s in shards)
    sizes = sorted(s.size() for s in shards)
    check('T6a records sharded by instrument provenance (non-IID)',
          groups == ['esp32_s3_camera:oil', 'sparkfun_triad:tomato'])
    check('T6b record without reference value skipped honestly',
          sizes == [2, 2])

    svc2 = FederatedCalibrationService(n_components=2)
    r2 = svc2.run_round(shards)
    check('T6c database shards train a federated calibration',
          r2.total_examples == 4 and r2.round_id == 1)

    check('T6d status reports model and sklearn availability',
          svc2.status()['model'] == 'pls'
          and svc2.status()['sklearn_available'] is True)
else:
    check('T3-T6 PLS checks skipped (scikit-learn not installed)', True)

# T7: privacy audit wiring in the service
if SKLEARN_AVAILABLE:
    svc3 = FederatedCalibrationService(n_components=2)
    try:
        svc3.run_round([shard_a], reference_x=np.vstack(
            [np.concatenate([coef_a, [intercept_a]])]))
        check('T7a privacy audit rejects a payload equal to a raw row', False)
    except RuntimeError:
        check('T7a privacy audit rejects a payload equal to a raw row', True)

# T8: integration - requirements pin scikit-learn (platform dependency)
req = (PROJECT / 'requirements.txt').read_text()
check('T8a scikit-learn pinned in requirements', 'scikit-learn' in req)

failed = [name for name, ok in results if not ok]
print(f'\n{len(results) - len(failed)}/{len(results)} checks passed')
if failed:
    print('FAILED:', failed)
    sys.exit(1)
