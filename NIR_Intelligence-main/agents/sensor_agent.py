# NIR Intelligence Platform - Sensor Agent (OP29)
# Collects all information about the sensors used in analyses: registered
# adapter profiles, the settings/parameters recorded with the measurements
# (existing database - SpectrumRecord.metadata / instrument_type, project
# preparation reports) and the optimization suggestions produced by the
# platform's three existing recommendation sources, deduplicated into one
# prioritized list. Offline, CI-safe, no new tables, honest about unknowns.

from typing import Any, Dict, List, Optional

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class SensorAgent(BaseAgent):
    """Aggregates sensor knowledge for analyses and the /sensors/ web pages.

    Operations (context key 'operation', default 'collect'):
    - collect: full catalog - registered adapters, setting options and the
      usage recorded in the existing database (per-user if 'user_id' given)
    - usage: only the database usage statistics
    """

    def __init__(self, **kwargs):
        super().__init__(name="SensorAgent", version="1.0.0", **kwargs)
        self.dependencies = ["numpy", "django"]

    def _collect(self, context: Dict[str, Any]) -> Dict[str, Any]:
        from services.sensor_catalog import (
            assess_settings,
            get_sensor_profiles,
            merge_recommendations,
        )
        user_id = context.get("user_id")
        profiles = get_sensor_profiles(user_id=user_id)
        parameter_recommendations = context.get("parameter_recommendations") or []
        sensor_results = context.get("sensor_quality_results")
        crew_recommendations = context.get("crew_recommendations") or []

        from services.sensor_catalog import get_optimization_suggestions
        suggestions = get_optimization_suggestions(
            sensor_results=sensor_results,
            parameter_recommendations=parameter_recommendations,
            crew_recommendations=crew_recommendations,
        )

        metadata = context.get("metadata") or {}
        setting_assessment = assess_settings(
            metadata, profiles.get("setting_options"))
        return {
            "operation": "collect",
            "registered_sensors": profiles["registered_sensors"],
            "setting_options": profiles["setting_options"],
            "usage": profiles["usage"],
            "unmatched_usage": profiles["unmatched_usage"],
            "setting_assessment": setting_assessment,
            "optimization_suggestions": suggestions,
        }

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute the sensor agent workflow."""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting sensor agent execution")
            context = context or {}
            operation = str(context.get("operation", "collect"))
            if operation == "collect":
                results = self._collect(context)
            elif operation == "usage":
                from services.sensor_catalog import _usage_from_database
                results = {
                    "operation": "usage",
                    "usage": _usage_from_database(
                        user_id=context.get("user_id")),
                }
            else:
                return self._handle_error(
                    ValueError(f"unknown operation '{operation}'"))
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(results)
        except Exception as exc:
            return self._handle_error(exc)

    def validate(self) -> list:
        return []
