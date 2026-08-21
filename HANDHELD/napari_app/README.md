# Napari server container

This service is designed to be a standalone Napari container for easy integration into an existing Django + MCP project.

## Purpose
- expose Napari as a dedicated service
- accept trigger commands from MQTT or REST
- remain separate from the analytical pipeline during the early phase
- support later linking to a Django platform and MCP orchestrator

## Endpoints
- GET /health
- GET /viewer/status
- POST /viewer/open
- POST /analysis/trigger

## Integration notes
- Use MQTT topic `spectral/#` for event-driven orchestration.
- Use Django or MCP to call this service when a raw acquisition is ready.
- Keep the true calibration and analysis logic out of this container until the integration contract is stable.
