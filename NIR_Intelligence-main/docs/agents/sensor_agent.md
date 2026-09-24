# SensorAgent

**Version**: 1.0.0  
**Author**: NIR Development Team  
**Created**: 2026  
**Type**: knowledge aggregation Agent

## Overview

SensorAgent (OP29) collects everything the platform knows about the
spectrometers used in analyses: registered adapter profiles, the setting
options the platform understands, the usage recorded in the existing
database (SpectrumRecord.instrument_type + project preparation reports) and
deduplicated optimization suggestions from the analyses.

## Responsibilities

- Sensor catalog for the /projects/sensors/ web pages
- Setting assessment (completeness + plausibility of recorded values)
- Optimization suggestion deduplication (analytical > heuristic > generic)

## Operations

| Operation | Context keys | Result |
|-----------|--------------|--------|
| `collect` (default) | `user_id`, `metadata`, `sensor_quality_results`, `parameter_recommendations`, `crew_recommendations` | registered_sensors, setting_options, usage, setting_assessment, optimization_suggestions |
| `usage` | `user_id` | usage statistics from the existing database |

## Configuration

### Required Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| operation | str | collect | Catalog operation to run |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| user_id | int | None | Restrict database usage statistics to one user |

## Dependencies

- django (existing database access; degrades gracefully offline)
- devices registry (adapter profiles)
- ParameterRecommenderAgent (parameter ranges)
