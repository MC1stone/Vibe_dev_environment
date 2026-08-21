# NIR Intelligence Platform - Metadata Quality Agent
# Handles metadata extraction, validation, and quality assessment for spectral data

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class MetadataStandard(Enum):
    """Metadata standards for comparison"""

    ISO_19115 = "ISO 19115"
    DUBLIN_CORE = "Dublin Core"
    JSON_LD = "JSON-LD"
    SCHEMA_ORG = "Schema.org"
    CUSTOM_NIR = "NIR Custom"


class MetadataQualityGrade(Enum):
    """Quality grades for metadata"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    MISSING = "missing"


class MetadataFieldCategory(Enum):
    """Categories of metadata fields"""

    IDENTIFICATION = "identification"
    TECHNICAL = "technical"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    QUALITY = "quality"
    PROVENANCE = "provenance"
    LICENSE = "license"


@dataclass
class MetadataField:
    """Individual metadata field with quality assessment"""

    name: str
    value: Any
    category: MetadataFieldCategory
    required: bool = False
    present: bool = True
    quality_score: float = 1.0  # 0-1
    issues: List[str] = field(default_factory=list)
    standard_compliance: Dict[str, bool] = field(default_factory=dict)


@dataclass
class MetadataQualityResult:
    """Complete metadata quality assessment result"""

    sample_id: str
    overall_quality_score: float  # 0-100
    overall_quality_grade: MetadataQualityGrade
    completeness_score: float  # 0-100
    accuracy_score: float  # 0-100
    consistency_score: float  # 0-100
    standards_compliance: Dict[str, float]  # Standard -> compliance score (0-100)
    fields_assessed: List[MetadataField]
    missing_required_fields: List[str]
    recommendations: List[str]
    enhancements: List[str]
    metadata_summary: Dict[str, Any]


@dataclass
class MetadataEnhancement:
    """Suggested enhancement for metadata"""

    field: str
    current_value: Any
    suggested_value: Any
    reason: str
    standard: str
    impact: str  # "low", "medium", "high"


class MetadataQualityAgent(BaseAgent):
    """Agent for metadata extraction, validation, and quality assessment"""

    def __init__(self, **kwargs):
        super().__init__(name="MetadataQualityAgent", version="1.0.0", **kwargs)
        self.dependencies = ["json", "yaml", "pydantic"]

        # Metadata standards and their required fields
        self.standards = {
            MetadataStandard.ISO_19115: {
                "required_fields": ["title", "abstract", "date", "identifier", "pointOfContact", "topicCategory"],
                "optional_fields": [
                    "keywords",
                    "accessConstraints",
                    "useConstraints",
                    "spatialRepresentationType",
                    "referenceSystemInfo",
                ],
            },
            MetadataStandard.DUBLIN_CORE: {
                "required_fields": ["title", "creator", "subject", "description", "date"],
                "optional_fields": [
                    "contributor",
                    "coverage",
                    "format",
                    "identifier",
                    "language",
                    "publisher",
                    "relation",
                    "rights",
                    "source",
                    "type",
                ],
            },
            MetadataStandard.JSON_LD: {
                "required_fields": ["@context", "@type"],
                "optional_fields": ["@id", "name", "description", "dateCreated"],
            },
            MetadataStandard.SCHEMA_ORG: {
                "required_fields": ["@context", "@type"],
                "optional_fields": ["name", "description", "dateCreated", "author"],
            },
            MetadataStandard.CUSTOM_NIR: {
                "required_fields": [
                    "sample_id",
                    "instrument_type",
                    "wavelength_range",
                    "measurement_date",
                    "operator",
                    "location",
                ],
                "optional_fields": [
                    "sample_description",
                    "sample_preparation",
                    "measurement_conditions",
                    "calibration_info",
                    "data_quality",
                    "processing_history",
                ],
            },
        }

        # Field categories mapping
        self.field_categories = {
            "sample_id": MetadataFieldCategory.IDENTIFICATION,
            "title": MetadataFieldCategory.IDENTIFICATION,
            "description": MetadataFieldCategory.IDENTIFICATION,
            "identifier": MetadataFieldCategory.IDENTIFICATION,
            "instrument_type": MetadataFieldCategory.TECHNICAL,
            "instrument_model": MetadataFieldCategory.TECHNICAL,
            "wavelength_range": MetadataFieldCategory.TECHNICAL,
            "spectral_resolution": MetadataFieldCategory.TECHNICAL,
            "integration_time": MetadataFieldCategory.TECHNICAL,
            "detector_type": MetadataFieldCategory.TECHNICAL,
            "light_source": MetadataFieldCategory.TECHNICAL,
            "measurement_date": MetadataFieldCategory.TEMPORAL,
            "measurement_time": MetadataFieldCategory.TEMPORAL,
            "date_created": MetadataFieldCategory.TEMPORAL,
            "location": MetadataFieldCategory.SPATIAL,
            "coordinates": MetadataFieldCategory.SPATIAL,
            "altitude": MetadataFieldCategory.SPATIAL,
            "data_quality": MetadataFieldCategory.QUALITY,
            "calibration_info": MetadataFieldCategory.QUALITY,
            "processing_history": MetadataFieldCategory.QUALITY,
            "operator": MetadataFieldCategory.PROVENANCE,
            "organization": MetadataFieldCategory.PROVENANCE,
            "data_source": MetadataFieldCategory.PROVENANCE,
            "license": MetadataFieldCategory.LICENSE,
            "rights": MetadataFieldCategory.LICENSE,
            "access_constraints": MetadataFieldCategory.LICENSE,
        }

        # Quality thresholds
        self.quality_thresholds = kwargs.get(
            "quality_thresholds", {"excellent": 90, "good": 75, "fair": 50, "poor": 25}
        )

        self.logger.info("MetadataQualityAgent initialized")

    def initialize(self) -> AgentOutput:
        """Initialize the metadata quality agent"""
        self.status = AgentStatus.READY
        self.logger.info("MetadataQualityAgent initialized and ready for metadata assessment")

        return AgentOutput(
            agent_name=self.name,
            status=self.status,
            version=self.version,
            dependencies=self.dependencies,
            data={
                "supported_standards": [s.value for s in self.standards.keys()],
                "field_categories": [c.value for c in MetadataFieldCategory],
                "quality_thresholds": self.quality_thresholds,
            },
        )

    def extract_metadata_from_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Extract metadata from various file types"""
        extracted_metadata = {}

        for file_path in file_paths:
            try:
                path = Path(file_path)
                if not path.exists():
                    continue

                # Extract based on file extension
                if file_path.lower().endswith(".json"):
                    file_metadata = self._extract_json_metadata(path)
                elif file_path.lower().endswith(".yaml") or file_path.lower().endswith(".yml"):
                    file_metadata = self._extract_yaml_metadata(path)
                elif file_path.lower().endswith(".txt") or file_path.lower().endswith(".csv"):
                    file_metadata = self._extract_text_metadata(path)
                else:
                    # Try to extract basic metadata from any file
                    file_metadata = self._extract_basic_metadata(path)

                if file_metadata:
                    extracted_metadata[file_path] = file_metadata

            except Exception as e:
                self.logger.warning(f"Error extracting metadata from {file_path}: {e}")

        return extracted_metadata

    def _extract_json_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from JSON file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Look for metadata in common locations
            if isinstance(data, dict):
                # Check if it's already metadata
                if "metadata" in data:
                    return data["metadata"]
                elif "properties" in data:
                    return data["properties"]
                else:
                    # Return the whole dict as potential metadata
                    return data
            return {}
        except Exception as e:
            self.logger.warning(f"Error reading JSON file {file_path}: {e}")
            return {}

    def _extract_yaml_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from YAML file"""
        try:
            import yaml

            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if isinstance(data, dict):
                if "metadata" in data:
                    return data["metadata"]
                elif "properties" in data:
                    return data["properties"]
                else:
                    return data
            return {}
        except ImportError:
            self.logger.warning("PyYAML not available for YAML parsing")
            return {}
        except Exception as e:
            self.logger.warning(f"Error reading YAML file {file_path}: {e}")
            return {}

    def _extract_text_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from text/CSV files"""
        try:
            metadata = {}
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Look for common metadata patterns
            metadata_patterns = {
                "sample_id": r"sample[_-]?id[\s]*[:=]\s*([^\s,;]+)",
                "instrument": r"instrument[\s]*[:=]\s*([^\s,;]+)",
                "date": r"date[\s]*[:=]\s*([^\s,;]+)",
                "wavelength": r"wavelength[\s]*[:=]\s*([^\s,;]+)",
                "operator": r"operator[\s]*[:=]\s*([^\s,;]+)",
                "location": r"location[\s]*[:=]\s*([^\s,;]+)",
            }

            for field, pattern in metadata_patterns.items():
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    metadata[field] = match.group(1).strip()

            return metadata
        except Exception as e:
            self.logger.warning(f"Error reading text file {file_path}: {e}")
            return {}

    def _extract_basic_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract basic file metadata"""
        try:
            stat = file_path.stat()
            return {
                "file_name": file_path.name,
                "file_size": stat.st_size,
                "file_type": file_path.suffix,
                "created_date": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        except Exception as e:
            self.logger.warning(f"Error getting file stats for {file_path}: {e}")
            return {}

    def merge_metadata(self, metadata_sources: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Merge metadata from multiple sources, with priority to more complete sources"""
        merged_metadata = {}

        # Priority order for merging (higher index = higher priority)
        priority_fields = [
            "sample_id",
            "title",
            "description",
            "instrument_type",
            "measurement_date",
            "operator",
            "location",
            "wavelength_range",
        ]

        # First, collect all metadata
        for source, metadata in metadata_sources.items():
            for key, value in metadata.items():
                if key not in merged_metadata:
                    merged_metadata[key] = value
                elif key in priority_fields:
                    # For priority fields, prefer non-empty values
                    if not merged_metadata[key] and value:
                        merged_metadata[key] = value

        return merged_metadata

    def validate_metadata_structure(self, metadata: Dict[str, Any]) -> List[str]:
        """Validate metadata structure and content"""
        errors = []

        # Check for empty metadata
        if not metadata:
            errors.append("No metadata provided")
            return errors

        # Check for required NIR-specific fields
        required_nir_fields = ["sample_id", "instrument_type", "measurement_date"]
        for field in required_nir_fields:
            if field not in metadata or not metadata[field]:
                errors.append(f"Missing required NIR field: {field}")

        # Check data types for known fields
        date_fields = ["measurement_date", "date_created", "modified_date"]
        for field in date_fields:
            if field in metadata:
                try:
                    # Try to parse as date
                    if isinstance(metadata[field], str):
                        datetime.fromisoformat(metadata[field])
                    elif not isinstance(metadata[field], datetime):
                        errors.append(f"Invalid date format for {field}")
                except ValueError:
                    errors.append(f"Invalid date format for {field}: {metadata[field]}")

        # Check numeric fields
        numeric_fields = ["wavelength_range", "spectral_resolution", "integration_time"]
        for field in numeric_fields:
            if field in metadata and metadata[field]:
                try:
                    if isinstance(metadata[field], str):
                        # Handle range formats for wavelength_range
                        if field == "wavelength_range" and ("-" in metadata[field] or "," in metadata[field]):
                            # This is a range, validate both ends
                            separator = "-" if "-" in metadata[field] else ","
                            parts = metadata[field].split(separator)
                            if len(parts) == 2:
                                float(parts[0].strip())
                                float(parts[1].strip())
                            else:
                                errors.append(f"Invalid range format for {field}: {metadata[field]}")
                        else:
                            # Single numeric value
                            float(metadata[field])
                    elif not isinstance(metadata[field], (int, float)):
                        errors.append(f"Invalid numeric format for {field}")
                except ValueError:
                    errors.append(f"Invalid numeric format for {field}: {metadata[field]}")

        return errors

    def assess_field_quality(self, field_name: str, value: Any, category: MetadataFieldCategory) -> MetadataField:
        """Assess the quality of a single metadata field"""
        field = MetadataField(
            name=field_name,
            value=value,
            category=category,
            present=value is not None and value != "",
            quality_score=1.0,
            issues=[],
            standard_compliance={},
        )

        # Check if field is present
        if not field.present:
            field.quality_score = 0.0
            field.issues.append("Field is missing or empty")
            return field

        # Category-specific quality checks
        if category == MetadataFieldCategory.TEMPORAL:
            # Check if it's a valid date
            if isinstance(value, str):
                try:
                    datetime.fromisoformat(value)
                except ValueError:
                    field.quality_score -= 0.5
                    field.issues.append("Invalid date format")

        elif category == MetadataFieldCategory.TECHNICAL:
            # Check if numeric fields have valid values
            if isinstance(value, str) and field_name in ["wavelength_range", "spectral_resolution"]:
                try:
                    if "-" in value:
                        # Range format like "700-2500"
                        parts = value.split("-")
                        if len(parts) == 2:
                            float(parts[0].strip())
                            float(parts[1].strip())
                        else:
                            field.quality_score -= 0.3
                            field.issues.append("Invalid range format")
                    elif "," in value:
                        # Range format like "700, 2500"
                        parts = value.split(",")
                        if len(parts) == 2:
                            float(parts[0].strip())
                            float(parts[1].strip())
                        else:
                            field.quality_score -= 0.3
                            field.issues.append("Invalid range format")
                    else:
                        float(value)
                except ValueError:
                    field.quality_score -= 0.5
                    field.issues.append("Invalid numeric value")

        elif category == MetadataFieldCategory.SPATIAL:
            # Check coordinate format
            if field_name == "coordinates" and isinstance(value, str):
                if not re.match(r"^\-?\d+\.?\d*,\s*\-?\d+\.?\d*$", value):
                    field.quality_score -= 0.4
                    field.issues.append("Invalid coordinate format")

        # Check for standard compliance
        for standard, config in self.standards.items():
            required_fields = config["required_fields"]
            optional_fields = config["optional_fields"]

            if field_name in required_fields:
                field.standard_compliance[standard.value] = field.present
            elif field_name in optional_fields:
                field.standard_compliance[standard.value] = field.present
            else:
                field.standard_compliance[standard.value] = False

        return field

    def assess_metadata_quality(self, metadata: Dict[str, Any], sample_id: str = "unknown") -> MetadataQualityResult:
        """Assess the overall quality of metadata"""
        try:
            # Initialize result
            result = MetadataQualityResult(
                sample_id=sample_id,
                overall_quality_score=0.0,
                overall_quality_grade=MetadataQualityGrade.MISSING,
                completeness_score=0.0,
                accuracy_score=0.0,
                consistency_score=0.0,
                standards_compliance={},
                fields_assessed=[],
                missing_required_fields=[],
                recommendations=[],
                enhancements=[],
                metadata_summary=metadata,
            )

            if not metadata:
                result.overall_quality_grade = MetadataQualityGrade.MISSING
                result.recommendations.append("No metadata provided. Please add metadata for proper analysis.")
                return result

            # Assess each field
            total_fields = 0
            present_fields = 0
            quality_scores = []

            for field_name, value in metadata.items():
                category = self.field_categories.get(field_name, MetadataFieldCategory.IDENTIFICATION)
                field_assessment = self.assess_field_quality(field_name, value, category)
                result.fields_assessed.append(field_assessment)

                total_fields += 1
                if field_assessment.present:
                    present_fields += 1
                    quality_scores.append(field_assessment.quality_score)
                else:
                    quality_scores.append(0.0)

            # Calculate completeness score
            if total_fields > 0:
                result.completeness_score = (present_fields / total_fields) * 100

            # Calculate accuracy score (average of field quality scores)
            if quality_scores:
                result.accuracy_score = (sum(quality_scores) / len(quality_scores)) * 100

            # Calculate consistency score (based on standard compliance)
            consistency_scores = []
            for field in result.fields_assessed:
                if field.standard_compliance:
                    compliance_count = sum(field.standard_compliance.values())
                    total_standards = len(field.standard_compliance)
                    consistency_scores.append(compliance_count / total_standards if total_standards > 0 else 0)

            if consistency_scores:
                result.consistency_score = (sum(consistency_scores) / len(consistency_scores)) * 100

            # Calculate standards compliance
            for standard in self.standards.keys():
                standard_name = standard.value
                required_fields = self.standards[standard]["required_fields"]
                optional_fields = self.standards[standard]["optional_fields"]

                required_present = 0
                optional_present = 0

                for field in result.fields_assessed:
                    if field.name in required_fields and field.present:
                        required_present += 1
                    elif field.name in optional_fields and field.present:
                        optional_present += 1

                total_required = len(required_fields)
                total_optional = len(optional_fields)

                compliance_score = 0.0
                if total_required > 0:
                    compliance_score = (required_present / total_required) * 100

                # Add partial credit for optional fields
                if total_optional > 0:
                    compliance_score += (optional_present / total_optional) * 20

                result.standards_compliance[standard_name] = min(100, compliance_score)

            # Calculate overall quality score
            weights = {"completeness": 0.4, "accuracy": 0.3, "consistency": 0.3}

            result.overall_quality_score = (
                result.completeness_score * weights["completeness"]
                + result.accuracy_score * weights["accuracy"]
                + result.consistency_score * weights["consistency"]
            )

            # Determine quality grade
            if result.overall_quality_score >= self.quality_thresholds.get("excellent", 90):
                result.overall_quality_grade = MetadataQualityGrade.EXCELLENT
            elif result.overall_quality_score >= self.quality_thresholds.get("good", 75):
                result.overall_quality_grade = MetadataQualityGrade.GOOD
            elif result.overall_quality_score >= self.quality_thresholds.get("fair", 50):
                result.overall_quality_grade = MetadataQualityGrade.FAIR
            elif result.overall_quality_score >= self.quality_thresholds.get("poor", 25):
                result.overall_quality_grade = MetadataQualityGrade.POOR
            else:
                result.overall_quality_grade = MetadataQualityGrade.MISSING

            # Find missing required fields
            for field in result.fields_assessed:
                if not field.present and field.required:
                    result.missing_required_fields.append(field.name)

            # Generate recommendations and enhancements
            result.recommendations = self._generate_recommendations(result)
            result.enhancements = self._generate_enhancements(result)

            return result

        except Exception as e:
            self.logger.error(f"Error assessing metadata quality: {e}")
            return MetadataQualityResult(
                sample_id=sample_id,
                overall_quality_score=0.0,
                overall_quality_grade=MetadataQualityGrade.MISSING,
                completeness_score=0.0,
                accuracy_score=0.0,
                consistency_score=0.0,
                standards_compliance={},
                fields_assessed=[],
                missing_required_fields=[],
                recommendations=[f"Assessment failed: {str(e)}"],
                enhancements=[],
                metadata_summary={},
            )

    def _generate_recommendations(self, result: MetadataQualityResult) -> List[str]:
        """Generate recommendations based on quality assessment"""
        recommendations = []

        # Completeness recommendations
        if result.completeness_score < 75:
            missing_count = len(result.missing_required_fields)
            recommendations.append(
                f"Add missing required fields: {', '.join(result.missing_required_fields[:5])}"
                + ("..." if missing_count > 5 else "")
            )

        # Accuracy recommendations
        if result.accuracy_score < 75:
            recommendations.append(
                "Improve data accuracy by validating field values and formats. "
                "Check date formats, numeric values, and coordinate formats."
            )

        # Consistency recommendations
        if result.consistency_score < 75:
            recommendations.append(
                "Improve consistency by following established metadata standards. "
                "Consider adopting ISO 19115 or Dublin Core standards."
            )

        # Standard-specific recommendations
        for standard, score in result.standards_compliance.items():
            if score < 50:
                recommendations.append(
                    f"Improve {standard} compliance (currently {score:.0f}%). "
                    "Add required fields and follow standard guidelines."
                )

        return recommendations

    def _generate_enhancements(self, result: MetadataQualityResult) -> List[str]:
        """Generate specific enhancement suggestions"""
        enhancements = []

        # Check for common missing fields
        common_fields = [
            "sample_description",
            "sample_preparation",
            "measurement_conditions",
            "calibration_info",
            "data_quality",
            "processing_history",
        ]

        existing_fields = {field.name for field in result.fields_assessed}
        for field in common_fields:
            if field not in existing_fields:
                enhancements.append(f"Add {field} for better data documentation")

        # Check for standard-specific enhancements
        if result.standards_compliance.get(MetadataStandard.ISO_19115.value, 0) < 80:
            enhancements.append(
                "Add ISO 19115 compliant fields: pointOfContact, topicCategory, " "spatialRepresentationType"
            )

        if result.standards_compliance.get(MetadataStandard.DUBLIN_CORE.value, 0) < 80:
            enhancements.append("Add Dublin Core fields: creator, subject, format, language, publisher")

        return enhancements

    def generate_metadata_quality_report(self, metadata: Dict[str, Any], sample_id: str = "unknown") -> Dict[str, Any]:
        """Generate a comprehensive metadata quality report"""
        quality_result = self.assess_metadata_quality(metadata, sample_id)

        report = {
            "sample_id": sample_id,
            "timestamp": datetime.now().isoformat(),
            "overall_quality": {
                "score": quality_result.overall_quality_score,
                "grade": quality_result.overall_quality_grade.value,
                "interpretation": self._get_quality_interpretation(quality_result.overall_quality_grade),
            },
            "detailed_scores": {
                "completeness": {
                    "score": quality_result.completeness_score,
                    "interpretation": self._get_score_interpretation(quality_result.completeness_score),
                },
                "accuracy": {
                    "score": quality_result.accuracy_score,
                    "interpretation": self._get_score_interpretation(quality_result.accuracy_score),
                },
                "consistency": {
                    "score": quality_result.consistency_score,
                    "interpretation": self._get_score_interpretation(quality_result.consistency_score),
                },
            },
            "standards_compliance": {
                standard: {"score": score, "interpretation": self._get_score_interpretation(score)}
                for standard, score in quality_result.standards_compliance.items()
            },
            "field_assessment": {
                field.name: {
                    "value": field.value,
                    "category": field.category.value,
                    "present": field.present,
                    "quality_score": field.quality_score,
                    "issues": field.issues,
                    "standard_compliance": field.standard_compliance,
                }
                for field in quality_result.fields_assessed
            },
            "missing_required_fields": quality_result.missing_required_fields,
            "recommendations": quality_result.recommendations,
            "enhancements": quality_result.enhancements,
            "metadata_summary": quality_result.metadata_summary,
        }

        return report

    def _get_quality_interpretation(self, grade: MetadataQualityGrade) -> str:
        """Get interpretation for quality grade"""
        interpretations = {
            MetadataQualityGrade.EXCELLENT: "Excellent metadata that meets all standards and provides comprehensive information",
            MetadataQualityGrade.GOOD: "Good metadata with minor gaps or issues",
            MetadataQualityGrade.FAIR: "Fair metadata with significant gaps or quality issues",
            MetadataQualityGrade.POOR: "Poor metadata with major gaps or quality problems",
            MetadataQualityGrade.MISSING: "No metadata provided or metadata is completely inadequate",
        }
        return interpretations.get(grade, "Unknown quality grade")

    def _get_score_interpretation(self, score: float) -> str:
        """Get interpretation for numeric score"""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 50:
            return "Fair"
        elif score >= 25:
            return "Poor"
        else:
            return "Very Poor"

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute metadata quality assessment workflow"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting metadata quality assessment")

            # Extract metadata from context
            metadata = context.get("metadata", {})
            sample_id = context.get("sample_id", "unknown")
            file_paths = context.get("file_paths", [])

            # If file paths are provided, extract metadata from files
            if file_paths:
                extracted_metadata = self.extract_metadata_from_files(file_paths)
                if extracted_metadata:
                    # Merge with provided metadata
                    all_metadata = metadata.copy()
                    for source_metadata in extracted_metadata.values():
                        all_metadata.update(source_metadata)
                    metadata = all_metadata

            # Validate metadata structure
            validation_errors = self.validate_metadata_structure(metadata)
            if validation_errors:
                self.logger.warning(f"Metadata validation errors: {validation_errors}")

            # Assess metadata quality
            quality_result = self.assess_metadata_quality(metadata, sample_id)

            # Generate comprehensive report
            quality_report = self.generate_metadata_quality_report(metadata, sample_id)

            # Prepare output
            output_data = {
                "metadata_quality_result": quality_result.__dict__,
                "quality_report": quality_report,
                "validation_errors": validation_errors,
                "extracted_metadata": metadata,
                "summary": {
                    "sample_id": sample_id,
                    "overall_quality_score": quality_result.overall_quality_score,
                    "overall_quality_grade": quality_result.overall_quality_grade.value,
                    "completeness_score": quality_result.completeness_score,
                    "accuracy_score": quality_result.accuracy_score,
                    "consistency_score": quality_result.consistency_score,
                    "recommendations_count": len(quality_result.recommendations),
                    "enhancements_count": len(quality_result.enhancements),
                    "missing_required_fields_count": len(quality_result.missing_required_fields),
                },
            }

            self.status = AgentStatus.COMPLETED
            self.logger.info(f"Metadata quality assessment completed for sample: {sample_id}")

            return self._create_success_output(output_data)

        except Exception as e:
            return self._handle_error(e)
