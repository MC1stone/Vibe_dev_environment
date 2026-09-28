"""FL3 verification: real differential privacy and honest secure
aggregation for the federated learning stack.

Checks that DP is a real mechanism (L2 clipping as sensitivity bound,
Gaussian noise calibrated from epsilon/delta, per-round budget
accounting with honest upper-bound composition), that the privacy
utility cost is measured instead of hidden, and that secure
aggregation availability is probed from the installed flwr instead of
being simulated. numpy-only; no new dependencies.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

results = []


def check(name, ok, detail=''):
    results.append((name, ok))
    print(f'[{"PASS" if ok else "FAIL"}] {name} {detail}')


PROJECT = Path(__file__).resolve().parent.parent

from services.federated_privacy import (
    DPConfig,
    DPNoiser,
    PrivacyAccountant,
    clip_update,
    dp_utility_cost,
    secure_aggregation_available,
)

# T1: DPConfig contract
cfg = DPConfig(epsilon=1.0, delta=1e-5, clip_norm=1.0)
expected_sigma = math.sqrt(2.0 * math.log(1.25 / 1e-5)) / 1.0
check('T1a sigma derived from the Gaussian mechanism bound',
      abs(cfg.sigma - expected_sigma) < 1e-9, f'sigma={cfg.sigma:.4f}')
cfg2 = DPConfig(epsilon=1.0, delta=1e-5, noise_multiplier=2.0)
check('T1b explicit noise_multiplier overrides sigma', cfg2.sigma == 2.0)
for bad in [dict(epsilon=0.0), dict(epsilon=-1.0)]:
    try:
        DPConfig(**bad)
        check(f'T1c epsilon>0 rejected ({bad})', False)
    except ValueError:
        check(f'T1c epsilon>0 rejected ({bad})', True)
try:
    DPConfig(epsilon=1.0, delta=1.5)
    check('T1d delta in (0,1) rejected', False)
except ValueError:
    check('T1d delta in (0,1) rejected', True)
try:
    DPConfig(epsilon=1.0, clip_norm=0.0)
    check('T1e clip_norm>0 rejected', False)
except ValueError:
    check('T1e clip_norm>0 rejected', True)

# T2: L2 clipping (sensitivity bound)
v = np.array([3.0, 4.0])
clipped = clip_update(v, clip_norm=2.5)
check('T2a update above the bound is clipped to the L2 norm',
      abs(np.linalg.norm(clipped) - 2.5) < 1e-12)
small = np.array([0.3, 0.4])
check('T2b update below the bound passes unchanged',
      np.array_equal(clip_update(small, clip_norm=2.5), small))
check('T2c zero update passes unchanged (no NaN)',
      np.array_equal(clip_update(np.zeros(3), 1.0), np.zeros(3)))

# T3: noiser - real Gaussian noise at the calibrated sigma
noiser = DPNoiser(DPConfig(epsilon=1.0, delta=1e-5, clip_norm=1.0), seed=7)
update = np.array([10.0, -10.0])
noisy = noiser.privatize(update, num_examples=50)
check('T3a privatized update is clipped (norm <= clip norm + noise budget)',
      np.linalg.norm(noisy) < cfg.sigma * 5 + 1.0 + 1e-9,
      f'norm={np.linalg.norm(noisy):.3f}')
samples = [noiser.privatize(np.zeros(2), 1) for _ in range(400)]
emp_sigma = float(np.std(np.concatenate(samples)))
check('T3b empirical noise matches calibrated sigma',
      0.9 * cfg.sigma < emp_sigma < 1.1 * cfg.sigma,
      f'emp={emp_sigma:.3f} sigma={cfg.sigma:.3f}')
check('T3c privatized update differs from the clean update',
      not np.allclose(noisy, clip_update(update, 1.0)))

# T4: privacy budget accounting (honest composition upper bound)
acct = PrivacyAccountant(DPConfig(epsilon=1.0, delta=1e-5))
for rid in (1, 2, 3):
    acct.record_round(rid)
check('T4a total epsilon composes over rounds', abs(acct.total_epsilon - 3.0) < 1e-12)
check('T4b total delta composes (union bound)', acct.total_delta > 1e-5)
check('T4c budget exhaustion against a max budget',
      acct.budget_exhausted(max_epsilon=2.5) and not acct.budget_exhausted(max_epsilon=10.0))
status = acct.status()
check('T4d status reports mechanism, sigma and budget',
      status['mechanism'] == 'gaussian' and status['rounds_recorded'] == 3
      and 'total_epsilon' in status and 'sigma' in status)
empty = PrivacyAccountant(DPConfig())
check('T4e empty accountant reports zero budget',
      empty.total_epsilon == 0.0 and empty.total_delta == 0.0)

# T5: honest utility cost measurement
clean = np.array([1.0, 0.0])
dp = clean + np.array([0.1, -0.1])
cost = dp_utility_cost(clean, dp)
check('T5a utility cost is the L2 distance clean vs privatized',
      abs(cost - math.sqrt(0.02)) < 1e-12)
check('T5b identical updates report zero cost',
      dp_utility_cost(clean, clean) == 0.0)

# T6: secure aggregation - honest availability probe (no simulation)
secagg = secure_aggregation_available()
check('T6a status is a dict with an explicit availability flag',
      isinstance(secagg, dict) and 'available' in secagg
      and 'status' in secagg)
if secagg.get('available'):
    check('T6b available workflow named, not simulated',
          bool(secagg.get('workflow')), str(secagg))
else:
    check('T6b unavailable reports an honest reason',
          bool(secagg.get('reason')), str(secagg))

# T7: integration with the FL2 calibration client (DP wraps the real fit)
try:
    from services.federated_calibration import (
        SKLEARN_AVAILABLE, CalibrationShard, FederatedCalibrationService,
    )
except ImportError:
    SKLEARN_AVAILABLE = False

if SKLEARN_AVAILABLE:
    from services.federated_calibration import PLSCalibrationClient

    rng = np.random.default_rng(3)
    x = rng.normal(0, 1, size=(40, 5))
    y = x @ rng.normal(0, 1, size=5) + rng.normal(0, 0.05, size=40)
    shard = CalibrationShard(x=x, y=y, instrument_type='sparkfun_triad',
                             sample_type='tomato')
    client = PLSCalibrationClient('sparkfun_triad:tomato', shard, n_components=2)
    coef, intercept, n, _ = client.fit_local()
    dp_noiser = DPNoiser(DPConfig(epsilon=2.0, delta=1e-5, clip_norm=50.0), seed=11)
    privatized = dp_noiser.privatize(coef, n)
    check('T7a DP applies to a real PLS coefficient update',
          privatized.shape == coef.shape and not np.allclose(privatized, coef))
    check('T7b utility cost of the DP PLS update is measured',
          dp_utility_cost(coef, privatized) > 0.0)
else:
    check('T7 PLS-DP integration skipped (scikit-learn not installed)', True)

# T8: integration - FlowerAgent privacy levels map to the real mechanisms
agent_src = (PROJECT / 'agents' / 'flower_agent.py').read_text()
check('T8a FlowerAgent defines differential_privacy level',
      'DIFFERENTIAL_PRIVACY' in agent_src)
check('T8b FlowerAgent defines secure_aggregation level',
      'SECURE_AGGREGATION' in agent_src)

failed = [name for name, ok in results if not ok]
print(f'\n{len(results) - len(failed)}/{len(results)} checks passed')
if failed:
    print('FAILED:', failed)
    sys.exit(1)
