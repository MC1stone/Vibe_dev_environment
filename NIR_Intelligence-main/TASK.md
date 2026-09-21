# NIR Intelligence Platform - Task Definition

## Overview

This document defines the current task for the NIR Intelligence Platform development.

## Current Task: ILIAS Learning Scenarios + Own Docker Container (Roadmap Step S8)

### Objective

Run ILIAS in its own Docker container within the platform topology and
synchronize NIR laboratory learning paths (courses, learning objectives)
to it from the Django platform.

### Predecessors

- S1-S7: COMPLETED (steering, Qdrant, format-agnostic import, spectrometer
  adapters, similarity + napari, chatbot, update monitoring)

### Scope

- docker-compose.yml / docker-compose.prod.yml: `ilias` service
  (srsolutions/ilias:9-php8.2-apache, port 8080->80, ILIAS_AUTO_SETUP,
  env-configured, healthchecks in prod) + dedicated `ilias_db` (mariadb:10.11,
  utf8mb4; ILIAS requires MySQL/MariaDB); volumes ilias_data,
  ilias_extradata, ilias_db_data
- `services/ilias_learning_service.py`: learning path model
  (LearningPath/LearningModule/LearningObjective), ILIASCourseBuilder
  (crs/lobj object types), ILIASLearningService with sync + status
- Django API: `api/ilias_views.py` + `api/ilias_urls.py`, route `api/ilias/`
- Test matrix `tests/test_s8_ilias_integration.py` (stubbed transport)

### Out of Scope

- ILIAS installation debugging/patching (community image used as-is)
- OAuth2 token flow against a running ILIAS (target environment)
- User synchronization / SAML SSO against a running ILIAS
- Didactic learning content creation (e-learning specialist's domain)

### Deliverables

1. ILIAS + MariaDB containers in both compose files
2. `services/ilias_learning_service.py`
3. `django_project/api/ilias_views.py` + `ilias_urls.py` + route
4. Test matrix 26/26 green + regressions S3-S7 green

### Success Criteria

- ILIAS runs as its own container with a pinned image tag (no 'latest')
- ILIAS uses a dedicated MariaDB on nir_network
- Learning paths map to ILIAS course (crs) + learning objective (lobj) objects
- Sync reports course ref id and per-module results; failures are graceful
- Django route api/ilias/ registered with 400/201/502 semantics
- Update monitor (S7) automatically covers the new images

### Timeline

- S1-S7: COMPLETED
- ILIAS containers: COMPLETED
- Learning service + Django API: COMPLETED
- Verification (26/26 + regressions): COMPLETED

### Dependencies

- Docker (for the ILIAS topology); srsolutions/ilias image, mariadb image
- requests (already a platform dependency)
- No new Python dependencies

### Notes

- ILIAS image: srsolutions/ilias (community-maintained, ILIAS_AUTO_SETUP
  support), pinned tag per S7 pinning recommendation
- ILIAS requires MySQL/MariaDB - hence the dedicated ilias_db container
  instead of the platform PostgreSQL
