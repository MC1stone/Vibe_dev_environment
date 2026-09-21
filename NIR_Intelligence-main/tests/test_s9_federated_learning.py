"""S9 verification: federated learning core for distributed spectrometer setups.

Tests non-IID sharding, privacy-safe client updates (parameter-only payloads),
FedAvg/FedProx aggregation semantics, multi-round convergence, integration
with the existing FlowerAgent configuration surface, and the compose Flower
service. No flwr installation required (framework-independent core).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import yaml

from services.federated_learning_service import (
    FLWR_AVAILABLE,
    AggregationResult,
    FedAvgAggregator,
    FederatedLearningService,
    LocalDataset,
    ModelUpdate,
    NonIIDSharder,
    PrivacyAuditor,
    create_federated_learning_service,
)

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


# T1: non-IID sharding - each group becomes its own local dataset
x_a, y_a = make_group_data(20, 5, 0.0, 1)
x_b, y_b = make_group_data(30, 5, 3.0, 2)
x_c, y_c = make_group_data(10, 5, -2.0, 3)
x = np.vstack([x_a, x_b, x_c])
y = np.concatenate([y_a, y_b, y_c])
groups = ['sparkfun_triad'] * 20 + ['esp32_s3_camera'] * 30 + ['diy_matchbox'] * 10

sharder = NonIIDSharder()
shards = sharder.shard(x, y, groups)
check('T1a shards per spectrometer group',
      set(shards) == {'sparkfun_triad', 'esp32_s3_camera', 'diy_matchbox'}
      and shards['esp32_s3_camera'].size() == 30
      and shards['sparkfun_triad'].x.shape == (20, 5))
check('T1b shards are non-IID (different group offsets)',
      abs(shards['esp32_s3_camera'].x.mean() - shards['diy_matchbox'].x.mean()) > 2.0)
try:
    sharder.shard(x, y, ['only_one_group'])
    check('T1c mismatched group labels rejected', False)
except ValueError:
    check('T1c mismatched group labels rejected', True)

client_map = sharder.shards_for_clients(x, y, groups,
                                        ['client-1', 'client-2', 'client-3'])
check('T1d client-shard assignment (one spectrometer setup per client)',
      set(client_map) == {'client-1', 'client-2', 'client-3'}
      and client_map['client-2'].group == 'esp32_s3_camera')


# T2: client updates carry parameters only (privacy contract)
service = FederatedLearningService()
service.initialize_global_model(dim=5)
update_a = service.client_update('client-1', client_map['client-1'])
check('T2a client update is parameter vector, not data matrix',
      update_a.params.shape == (5,) and update_a.num_examples == 20
      and update_a.group == 'sparkfun_triad')
check('T2b update dict exposes no raw data',
      set(update_a.to_dict()) == {'client_id', 'num_examples', 'group', 'metrics', 'param_shape'}
      and update_a.to_dict()['param_shape'] == [5])
audit = PrivacyAuditor.audit_update(update_a, reference_x=x)
check('T2c privacy audit passes for parameter-only update',
      audit['private'] is True and audit['payload'] == 'params_only')


# T3: FedAvg weighted aggregation
agg = FedAvgAggregator(strategy='fedavg')
u1 = ModelUpdate('c1', np.array([1.0, 1.0]), num_examples=30, group='g1')
u2 = ModelUpdate('c2', np.array([3.0, 3.0]), num_examples=10, group='g2')
merged = agg.aggregate([u1, u2])
check('T3a fedavg weights by example count (0.75/0.25)',
      np.allclose(merged, [1.5, 1.5]), f'merged={merged}')
check('T3b empty update list -> None', agg.aggregate([]) is None)
try:
    agg.aggregate([ModelUpdate('c1', np.array([1.0]), 1, 'g'),
                   ModelUpdate('c2', np.array([1.0, 2.0]), 1, 'g')])
    check('T3c shape mismatch rejected', False)
except ValueError:
    check('T3c shape mismatch rejected', True)
try:
    FedAvgAggregator(strategy='unknown')
    check('T3d unknown strategy rejected', False)
except ValueError:
    check('T3d unknown strategy rejected', True)


# T4: FedProx blending toward global parameters
agg_prox = FedAvgAggregator(strategy='fedprox', proximal_mu=0.4)
global_p = np.array([0.0, 0.0])
prox_merged = agg_prox.aggregate([u1], global_params=global_p)
check('T4 fedprox blends client params toward global (mu=0.4)',
      np.allclose(prox_merged, 0.6 * np.array([1.0, 1.0])))


# T5: full round via service (local training + aggregation + audit)
result, audits = service.run_round(client_map, reference_x=x)
check('T5a round aggregates all clients',
      result.participating_clients == ['client-1', 'client-2', 'client-3']
      and result.total_examples == 60 and result.round_id == 1)
check('T5b groups recorded per round',
      result.groups == ['diy_matchbox', 'esp32_s3_camera', 'sparkfun_triad'])
check('T5c privacy audits all clean',
      all(a['private'] for a in audits) and len(audits) == 3)
check('T5d global params updated after round',
      service.global_params is not None and service.global_params.shape == (5,))
check('T5e round history kept',
      len(service.history) == 1 and isinstance(service.history[0], AggregationResult))


# T6: multi-round convergence - global model moves toward joint optimum
# Ground truth: pooled ridge solution over all data
x_all = x.copy()
gram = x_all.T @ x_all + 1e-6 * np.eye(5)
w_pooled = np.linalg.solve(gram, x_all.T @ y)

service2 = FederatedLearningService()
service2.initialize_global_model(dim=5)
dists = []
for round_i in range(5):
    res, _ = service2.run_round(client_map, learning_rate=0.5)
    dists.append(np.linalg.norm(service2.global_params - w_pooled))
check('T6 global model converges over 5 rounds (distance decreases)',
      dists[-1] < dists[0], f'd0={dists[0]:.3f} d4={dists[-1]:.3f}')
check('T6b rounds counted', service2.status()['rounds_completed'] == 5)


# T7: empty client dataset rejected
try:
    service.client_update('empty-client', LocalDataset(x=np.empty((0, 5)), y=np.empty(0), group='g'))
    check('T7 empty local dataset rejected', False)
except ValueError:
    check('T7 empty local dataset rejected', True)


# T8: status and factory
status = FederatedLearningService().status()
check('T8a status reports strategy, flwr availability, round count',
      status['strategy'] in ('fedavg', 'fedprox') and 'flwr_available' in status
      and status['flwr_available'] == FLWR_AVAILABLE)
factory = create_federated_learning_service(config={'strategy': 'fedprox', 'proximal_mu': 0.2})
check('T8b factory applies config',
      factory.strategy == 'fedprox' and factory.proximal_mu == 0.2)


# T9: integration with existing Flower stack (compose + agent config + requirements)
compose = yaml.safe_load((PROJECT / 'docker-compose.yml').read_text())
check('T9a flower_server service present in compose',
      'flower_server' in compose['services']
      and '5555' in compose['services']['flower_server']['ports'][0])
req = (PROJECT / 'requirements.txt').read_text()
check('T9b flwr dependency declared', 'flwr>=' in req)
agent_src = (PROJECT / 'agents' / 'flower_agent.py').read_text()
check('T9c FlowerAgent supports FedAvg and FedProx strategies',
      'FedAvg' in agent_src and 'FedProx' in agent_src)


# T10: regression spot checks
import pandas as pd
from services.spectrum_similarity import SpectrumSimilarityEngine
engine = SpectrumSimilarityEngine()
engine.add_references([{'data': pd.DataFrame({'wavelength': [1, 2], 'intensity': [1.0, 2.0]}),
                        'wavelength_column': 'wavelength', 'intensity_column': 'intensity'}])
m = engine.find_similar({'data': pd.DataFrame({'wavelength': [1, 2], 'intensity': [1.0, 2.0]}),
                         'wavelength_column': 'wavelength', 'intensity_column': 'intensity'})
check('T10a S5 similarity regression spot check', len(m) == 1 and m[0].distance < 1e-6)
from devices.sparkfun_triad import SparkFunTriadAdapter, TRIAD_WAVELENGTHS
triad = SparkFunTriadAdapter()
triad.connect()
spec = triad.acquire_measurement({'channel_payload': {
    'channels': {f'{wl:g}': float(i) for i, wl in enumerate(TRIAD_WAVELENGTHS)}}})
check('T10b S4 triad adapter regression spot check',
      spec is not None and len(spec['data']) == 18)
from services.ilias_learning_service import LearningPath, LearningModule, LearningObjective
lp = LearningPath(title='t', modules=[LearningModule(title='m', objectives=[LearningObjective(title='o')])])
check('T10c S8 learning path regression spot check', lp.total_objectives() == 1)


failed = [r for r in results if not r[1]]
print(f'\n{len(results) - len(failed)}/{len(results)} tests passed')
sys.exit(1 if failed else 0)
