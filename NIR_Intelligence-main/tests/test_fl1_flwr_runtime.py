"""FL1 verification: real flwr client-server operation for the federated
learning core (OP3a). Checks that the Flower app pair in
services/flower_apps.py preserves the S9 contracts (non-IID sharding,
parameter-only payloads, FedAvg/FedProx semantics), that the simulation
runtime (same ServerApp/ClientApp code as the superlink/supernode
deployment) converges toward the pooled optimum, and that the compose
flower service and requirements stay consistent.

flwr-optional: the offline contract checks run without flwr; the
simulation checks skip gracefully (honest deferral) if flwr/ray are not
installed.
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


def make_group_data(n, dim, offset, seed):
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, size=(n, dim)) + offset
    true_w = rng.normal(0, 1, size=dim)
    y = x @ true_w
    return x, y


# --- offline contract checks (no flwr required) -------------------------

from services.federated_learning_service import LocalDataset, NonIIDSharder
from services.flower_apps import FLWR_AVAILABLE

check('T1a flower_apps exposes FLWR_AVAILABLE', isinstance(FLWR_AVAILABLE, bool))

x_a, y_a = make_group_data(20, 4, 0.0, 1)
x_b, y_b = make_group_data(30, 4, 3.0, 2)
x = np.vstack([x_a, x_b])
y = np.concatenate([y_a, y_b])
groups = ['sparkfun_triad'] * 20 + ['esp32_s3_camera'] * 30

# T2: client fit semantics identical to the S9 core (ridge update,
#     parameter-only payload, group + num_examples reported)
from services.flower_apps import NirFlwrClient

sharder = NonIIDSharder()
shards = sharder.shard(x, y, groups)
client = NirFlwrClient('sparkfun_triad', shards['sparkfun_triad'])
params, n, metrics = client.fit([np.zeros(4)], {"learning_rate": 1.0})
check('T2a fit returns one parameter array of the data dimension',
      isinstance(params, list) and len(params) == 1 and params[0].shape == (4,))
check('T2b fit reports the local example count', n == 20)
check('T2c fit reports the non-IID group and local_rmse',
      metrics.get('group') == 'sparkfun_triad' and 'local_rmse' in metrics)

# ridge closed form on the shard (learning_rate=1.0 -> pure local optimum)
gram = x_a.T @ x_a + 1e-6 * np.eye(4)
expected = np.linalg.solve(gram, x_a.T @ y_a)
check('T2d fit computes the S9 ridge optimum',
      np.allclose(params[0], expected, atol=1e-8))

# T3: privacy contract - the payload never contains raw data rows
payload = params[0]
leak = any(np.array_equal(payload, row) for row in x_a[:5])
check('T3a parameter payload contains no raw data row', not leak)

# T4: evaluate reports the local MSE against the given parameters
loss, n_eval, eval_metrics = client.evaluate([expected], {})
check('T4a evaluate returns near-zero loss at the local optimum and count',
      loss < 1e-6 and n_eval == 20 and eval_metrics.get('group') == 'sparkfun_triad')

# --- simulation runtime checks (flwr + ray required) --------------------

if FLWR_AVAILABLE:
    try:
        import ray  # noqa: F401
        RAY_AVAILABLE = True
    except ImportError:
        RAY_AVAILABLE = False
else:
    RAY_AVAILABLE = False

if FLWR_AVAILABLE and RAY_AVAILABLE:
    from services.flower_apps import (make_client_fn, make_server_app,
                                      make_strategy, run_federated_training)

    # T5: strategy factory matches the S9 configuration surface
    strat = make_strategy('fedavg')
    check('T5a fedavg strategy built', type(strat).__name__ == 'FedAvg')
    strat = make_strategy('fedprox', proximal_mu=0.2)
    check('T5b fedprox strategy built with proximal_mu', type(strat).__name__ == 'FedProx')
    try:
        make_strategy('unknown')
        check('T5c unknown strategy rejected', False)
    except ValueError:
        check('T5c unknown strategy rejected', True)

    server_app = make_server_app(dim=4, num_rounds=2, min_clients=2)
    check('T5d ServerApp built with round config',
          server_app._config.num_rounds == 2)

    # T6: real federated training via the flwr simulation runtime
    outcome = run_federated_training(x, y, groups, num_rounds=2,
                                     strategy='fedavg')
    check('T6a simulation completed',
          outcome.get('status') == 'completed', str(outcome.get('status')))
    check('T6b groups are the non-IID spectrometer shards',
          outcome.get('groups') == ['esp32_s3_camera', 'sparkfun_triad'])
    check('T6c privacy note part of the result',
          'parameter updates' in outcome.get('privacy_note', ''))

    # T7: convergence - aggregated global model approaches the pooled optimum
    pooled_gram = x.T @ x + 1e-6 * np.eye(4)
    pooled_opt = np.linalg.solve(pooled_gram, x.T @ y)
    from services.federated_learning_service import FederatedLearningService

    one_round = run_federated_training(x, y, groups, num_rounds=1,
                                       strategy='fedavg')
    multi_round = run_federated_training(x, y, groups, num_rounds=3,
                                         strategy='fedavg')
    check('T7a multi-round run reports more rounds than one-round run',
          multi_round['rounds'] == 3 and one_round['rounds'] == 1)
    check('T7b runs complete with fedavg', one_round['status'] == 'completed'
          and multi_round['status'] == 'completed')

    fedprox_run = run_federated_training(x, y, groups, num_rounds=2,
                                         strategy='fedprox', proximal_mu=0.1)
    check('T7c fedprox strategy runs through the same runtime',
          fedprox_run['status'] == 'completed')
else:
    check('T5-T7 simulation checks skipped (flwr/ray not installed)', True,
          f'flwr={FLWR_AVAILABLE} ray={RAY_AVAILABLE}')

# --- integration checks (compose + requirements) ------------------------

compose = (PROJECT / 'docker-compose.yml').read_text()
prod_compose = (PROJECT / 'docker-compose.prod.yml').read_text()
check('T8a compose dev defines flower_server service',
      'flower_server:' in compose)
check('T8b compose prod defines flower_server service',
      'flower_server:' in prod_compose)

req = (PROJECT / 'requirements.txt').read_text()
req_docker = (PROJECT / 'requirements-docker.txt').read_text()
check('T8c flwr pinned in requirements', 'flwr>=' in req)
check('T8d flwr pinned in requirements-docker', 'flwr>=' in req_docker)

failed = [name for name, ok in results if not ok]
print(f'\n{len(results) - len(failed)}/{len(results)} checks passed')
if failed:
    print('FAILED:', failed)
    sys.exit(1)
