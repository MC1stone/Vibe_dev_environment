# NIR Intelligence Platform - Metadata Agent
# Handles metadata extraction and validation for NIR spectroscopy data (MO 7).
# Real implementation: validation and quality assessment are delegated to
# the MetadataQualityAgent (services layer, S3) - no simulated scores.

from typing import Any, Dict, List, Optional

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class MetadataAgent(BaseAgent):
    """Agent for managing metadata extraction and validation.

    context keys:
    - metadata: metadata dict to assess
    - sample_id: sample identifier (default 'unknown')
    - file_paths: files to extract additional metadata from
    """

    def __init__(self, **kwargs):
        super().__init__(name="MetadataAgent", version="2.0.0", **kwargs)
        self.dependencies = ["pandas", "numpy"]
        self.required_fields = kwargs.get(
            "required_fields", ["spectrum", "wavelength", "instrument", "acquisition_time"]
        )
        self.optional_fields = kwargs.get(
            "optional_fields", ["operator", "humidity", "temperature", "notes", "location"]
        )
        self.validation_strictness = kwargs.get("validation_strictness", "high")

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute metadata agent workflow."""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting metadata agent execution")

            context = context or {}
            metadata = context.get("metadata", {})
            if not isinstance(metadata, dict):
                return self._handle_error(ValueError("metadata must be a dict"))
            sample_id = context.get("sample_id", "unknown")
            file_paths = context.get("file_paths", []) or []

            from .metadata_quality_agent import MetadataQualityAgent

            quality_agent = MetadataQualityAgent()
            quality_output = quality_agent.execute({
                "metadata": metadata,
                "sample_id": sample_id,
                "file_paths": file_paths,
            })
            if quality_output.status != AgentStatus.COMPLETED:
                return self._handle_error(RuntimeError(
                    f"metadata quality assessment failed: "
                    f"{[e.message for e in quality_output.errors] or 'unknown error'}"))

            quality_data = quality_output.data
            quality_result = quality_data.get("metadata_quality_result", {})

            required_present = sum(
                1 for field in self.required_fields
                if metadata.get(field) is not None or self._field_present(metadata, field)
            )
            optional_present = sum(
                1 for field in self.optional_fields
                if metadata.get(field) is not None or self._field_present(metadata, field)
            )

            metadata_results = {
                "sample_id": sample_id,
                "required_fields_validated": len(self.required_fields),
                "required_fields_present": required_present,
                "missing_required_fields": [
                    field for field in self.required_fields
                    if not (metadata.get(field) is not None or self._field_present(metadata, field))
                ],
                "optional_fields_checked": len(self.optional_fields),
                "optional_fields_present": optional_present,
                "validation_strictness": self.validation_strictness,
                "metadata_quality_score": quality_result.get("overall_quality_score", 0.0),
                "quality_grade": (
                    quality_result.get("overall_quality_grade", "")
                    if isinstance(quality_result.get("overall_quality_grade"), str)
                    else getattr(quality_result.get("overall_quality_grade", ""), "value", "")
                ),
                "validation_errors": quality_data.get("validation_errors", []),
                "recommendations": quality_result.get("recommendations", []),
                "files_extracted": len(file_paths),
                "status": "ok",
            }

            self.status = AgentStatus.COMPLETED
            return self._create_success_output(metadata_results)
        except Exception as e:
            return self._handle_error(e)

    @staticmethod
    def _field_present(metadata: Dict[str, Any], field: str) -> bool:
        """Check a field including common aliases (acquisition_time etc.)."""
        aliases = {
            "acquisition_time": ["measurement_date", "timestamp", "acquisition_date"],
            "instrument": ["instrument_type", "instrument_model", "device"],
            "wavelength": ["wavelength_range", "wavelengths", "wavelength_unit"],
            "spectrum": ["spectral_resolution", "spectral_data"],
        }
        for alias in aliases.get(field, []):
            if metadata.get(alias) is not None:
                return True
        return False
