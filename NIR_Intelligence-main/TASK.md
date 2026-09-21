# NIR Intelligence Platform - Task Definition

## Overview

This document defines the current task for the NIR Intelligence Platform development.

## Current Task: Spectrum Similarity & napari Integration (Roadmap Step S5)

### Objective

Compare incoming spectra against a reference set (nearest-neighbour search)
and integrate the napari headless visualization server into the platform
topology, fulfilling Master Objectives 11, 13 and 14.

### Predecessors

- S1 (Consolidation & Steering): COMPLETED
- S2 (Qdrant Migration, G1): COMPLETED
- S3 (Format-agnostic Import, G4): COMPLETED - unified spectral data schema
- S4 (Spectrometer Abstraction, G5): COMPLETED - device adapters
  (DIY matchbox, ESP32-S3, SparkFun Triad) emit the unified schema

### Scope

- `services/spectrum_similarity.py`: SpectrumSimilarityEngine with FAISS
  backend (when installed) and exact numpy fallback; QdrantSimilarityService
  as optional embedding backend (operational with S6)
- `services/napari_server/`: headless napari server integrated from
  `HANDHELD/napari_app` (integration, not further development of HANDHELD)
- `docker-compose.yml` / `docker-compose.prod.yml`: napari_server service
  (port 8002, MQTT environment, nir_network)
- `agents/faiss_agent.py` / `agents/qdrant_agent.py`: wired to the real
  similarity engine instead of placeholder simulation
- Test matrix `tests/test_s5_spectrum_similarity.py`

### Out of Scope

- Text/embedding model pipeline (follows in S6 with the Ollama chatbot)
- GUI development for napari (headless server only, per HANDHELD source)
- Changes to `HANDHELD/` itself (source only, per G3 consolidation rule)
- Django frontend visualization UI (follows with S6/Django integration)

### Deliverables

1. `services/spectrum_similarity.py`: similarity engine + Qdrant service
2. `services/napari_server/` (app.py, Dockerfile, requirements.txt)
3. Compose integration (both files) with napari_server on port 8002
4. FAISS/Qdrant agents executing real operations via the engine
5. Test matrix 16/16 green + S3/S4 regressions green

### Success Criteria

- Identical spectrum is found with distance ~0 as best match
- Ranking of references is correct for L2 and cosine metrics
- Engine works without FAISS installed (numpy fallback, same results)
- Qdrant connection state is reported gracefully (never crashes)
- S4 adapter output (SparkFun Triad 18-channel spectra) is directly comparable
- napari_server present in both compose files and joins nir_network
- docker compose config parses as valid YAML

### Timeline

- S1-S4: COMPLETED
- Similarity engine: COMPLETED
- napari integration (service + compose): COMPLETED
- Agent wiring: COMPLETED
- Verification (16/16 + regressions): COMPLETED

### Dependencies

- Python 3.12+, numpy, pandas
- faiss-cpu (optional; exact numpy fallback when absent)
- qdrant-client (optional in S5; required for S6 embedding pipeline)
- Docker (optional for testing the compose topology)

### Notes

- All engine inputs/outputs use the unified spectral schema from S3
- HANDHELD/napari_app remains untouched; the integrated copy lives in
  services/napari_server (G3: integrate instead of duplicate development)
- Agents use simulated data for testing purposes
