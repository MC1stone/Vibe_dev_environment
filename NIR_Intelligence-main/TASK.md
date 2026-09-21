# NIR Intelligence Platform - Task Definition

## Overview

This document defines the current task for the NIR Intelligence Platform development.

## Current Task: Roadmap Complete — Local Environment Setup & Target-Environment Testing

### Objective

All roadmap steps S1-S9 and gaps G1-G8 are completed. The next phase is to
update and verify the platform on the local development machine (real docker
runtime, running Ollama/Mistral, Qdrant, ILIAS) before tackling the remaining
target-environment open points.

### Predecessors

- S1-S9: COMPLETED (steering, Qdrant, format-agnostic import, spectrometer
  adapters, similarity + napari, chatbot, update monitoring, ILIAS container,
  federated learning core)
- G1-G8: CLOSED (G8: `framework/` declared as reference skeleton)

### Scope

- Local setup guide for the development machine (`docs/LOCAL_SETUP.md`)
- Local verification of the full docker-compose stack (dev profile)

### Out of Scope

- Target-environment open points (real flwr operation, Qdrant embedding
  pipeline, ILIAS OAuth2, online update lookups, commercial spectrometer
  adapters, CI workflows) — follow after local verification

### Deliverables

1. `docs/LOCAL_SETUP.md` — step-by-step local setup and verification guide
2. G8 closed in `REPOSITORY_ALIGNMENT_AND_ROADMAP.md`

### Success Criteria

- Setup guide verified against the actual compose services, ports, and
  environment files (no invented paths/ports)
- Guide covers: prerequisites, update, env setup, stack startup, health
  checks, test matrices, first local analysis, shutdown/reset

### Timeline

- S1-S9 + G1-G8: COMPLETED
- Local setup guide: THIS TASK
- Target-environment open points: NEXT (after local verification)

### Dependencies

- Docker Engine + Compose v2 on the target machine
- ~30-50 GB free disk for images/volumes (Ollama Mistral model ~4-8 GB)
- No new Python dependencies
