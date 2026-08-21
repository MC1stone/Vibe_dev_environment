# Spectral IoT Platform

This project is a starter Dockerized architecture for integrating a napari-based spectral analysis module into a Django platform with an MCP server and MQTT-driven orchestration through Node-RED.

## Architecture overview

- Django web platform: dashboard and management UI
- MCP server: protocol bridge and tool execution endpoint
- Napari instance: spectral data visualization and analysis module
- MQTT broker: telemetry and command exchange
- Node-RED: flow orchestration and facilitation layer

## Services

- Django: http://localhost:8000
- Node-RED: http://localhost:1880
- MQTT broker: localhost:1883
- MCP server: http://localhost:8001

## Quick start

```bash
docker compose up --build
```

## Typical workflow

1. Define the hardware interface and measurement data contract.
2. Start a raw acquisition session and store its metadata.
3. Analysis and calibration are deferred and intentionally not yet implemented.

## Container notes

- The napari service runs with Xvfb to provide a headless display.
- Node-RED is configured to act as the orchestration facilitator between MQTT and application logic.
- MQTT is the preferred protocol for lightweight command/data exchange.

## Future extensions

- add a PostgreSQL database
- add authentication for Django
- implement signal processing and calibration modules for spectral data
- persist analysis results to SQLite or Postgres
- expose MCP tools for spectrum extraction and reference comparison
