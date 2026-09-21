# NIR Intelligence Platform - Task Definition

## Overview

This document defines the current task for the NIR Intelligence Platform development.

## Current Task: Federated Learning for Distributed Spectrometer Setups (Roadmap Step S9)

### Objective

Extend federated learning for distributed spectrometer setups with a
privacy guarantee (only model parameter updates are shared, never raw
spectra) and a non-IID strategy (spectra sharded per spectrometer/sample
group).

### Predecessors

- S1-S8: COMPLETED (steering, Qdrant, format-agnostic import, spectrometer
  adapters, similarity + napari, chatbot, update monitoring, ILIAS container)

### Scope

- `services/federated_learning_service.py`: framework-independent core
  (NonIIDSharder, FedAvgAggregator with fedavg/fedprox, PrivacyAuditor,
  FederatedLearningService round orchestration, ModelUpdate/LocalDataset)
- Test matrix `tests/test_s9_federated_learning.py`
- Flower framework remains the production transport (services/flower_server.py,
  agents/flower_agent.py, compose service flower_server, flwr>=1.4.0)

### Out of Scope

- Live flwr client-server operation (requires running containers)
- Real calibration model integration (follows with S7 optimization protocol)
- Differential privacy / secure aggregation (future hardening step)

### Deliverables

1. `services/federated_learning_service.py`
2. Test matrix 28/28 green + regressions S3-S8 green

### Success Criteria

- Non-IID shards per spectrometer group (one client = one setup)
- Client updates carry parameters only; privacy audit per round
- FedAvg weights by example count; FedProx blends toward global params
- Global model converges over multiple rounds toward the pooled optimum
- Shape/strategy/empty-data error cases rejected with ValueError
- Existing Flower stack untouched and verified (compose, requirements, agent)

### Timeline

- S1-S8: COMPLETED
- Federated learning core: COMPLETED
- Verification (28/28 + regressions): COMPLETED

### Dependencies

- Python 3.12+, numpy
- flwr (optional in this core; required for the Flower transport, already
  in requirements.txt)

### Notes

- Privacy contract: ModelUpdate = params + counts + group + metrics only
- The core is transport-agnostic and fully testable without flwr installed
