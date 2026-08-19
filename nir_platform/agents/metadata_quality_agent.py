"""
Metadata Quality Agent for NIR Intelligence Platform

This agent specializes in evaluating the quality of metadata associated with
spectral data. It checks compliance with international standards, assesses
completeness, and provides grading and enhancement recommendations.
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import httpx

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class MetadataField:
    """Represents a metadata field with its properties."""
    name: str
    display_name: str
    description: str
    data_type: str
    required: bool = False
    standard: str = ""  # Which standard this field belongs to
    unit: str = ""
    format: str = ""
    validation_regex: Optional[str] = None
    possible_values: List[str] = field(default_factory=list)
    
    def validate(self, value: Any) -> Tuple[bool, str]:
        """Validate a value against this field's requirements."""
        if value is None:
            if self.required:
                return False, f"Required field '{self.display_name}' is missing"
            return True, ""
        
        # Check data type
        if self.data_type == "string" and not isinstance(value, str):
            return False, f"Field '{self.display_name}' must be a string"
        elif self.data_type == "number" and not isinstance(value, (int, float)):
            return False, f"Field '{self.display_name}' must be a number"
        elif self.data_type == "date" and not self._is_date(value):
            return False, f"Field '{self.display_name}' must be a valid date"
        elif self.data_type == "boolean" and not isinstance(value, bool):
            return False, f"Field '{self.display_name}' must be a boolean"
        
        # Check format
        if self.format and isinstance(value, str):
            if self.format == "email" and not self._is_email(value):
                return False, f"Field '{self.display_name}' must be a valid email"
            elif self.format == "url" and not self._is_url(value):
                return False, f"Field '{self.display_name}' must be a valid URL"
        
        # Check regex pattern
        if self.validation_regex and isinstance(value, str):
            if not re.match(self.validation_regex, value):
                return False, f"Field '{self.display_name}' does not match required pattern"
        
        # Check possible values
        if self.possible_values and value not in self.possible_values:
            return False, f"Field '{self.display_name}' must be one of: {', '.join(self.possible_values)}"
        
        return True, ""
    
    def _is_date(self, value: Any) -> bool:
        """Check if value is a valid date."""
        if isinstance(value, datetime):
            return True
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value)
                return True
            except:
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                    return True
                except:
                    return False
        return False
    
    def _is_email(self, value: str) -> bool:
        """Check if value is a valid email."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, value) is not None
    
    def _is_url(self, value: str) -> bool:
        """Check if value is a valid URL."""
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return re.match(pattern, value) is not None


@dataclass
class MetadataQualityResult:
    """Container for metadata quality analysis results."""
    metadata: Dict[str, Any]
    compliance_scores: Dict[str, float]  # Scores by standard
    field_scores: Dict[str, Dict[str, Any]]  # Scores by field
    overall_score: float
    grade: str
    missing_fields: List[str]
    invalid_fields: List[Dict[str, Any]]
    enhancement_recommendations: List[Dict[str, Any]]
    standards_compliance: Dict[str, Dict[str, Any]]
    
    def to_dict(self) -> Dict:
        return {
            "metadata": self.metadata,
            "compliance_scores": self.compliance_scores,
            "field_scores": self.field_scores,
            "overall_score": self.overall_score,
            "grade": self.grade,
            "missing_fields": self.missing_fields,
            "invalid_fields": self.invalid_fields,
            "enhancement_recommendations": self.enhancement_recommendations,
            "standards_compliance": self.standards_compliance
        }


class MetadataQualityAgent:
    """
    Agent for evaluating metadata quality against international standards.
    
    Capabilities:
    - Validate metadata against multiple standards (ISO, ASTM, etc.)
    - Assess completeness and accuracy
    - Calculate quality scores and grades
    - Provide enhancement recommendations
    - Generate compliance reports
    """
    
    def __init__(self, 
                 agent_id: str = "metadata_quality_agent",
                 mcp_server_url: str = "http://localhost:8000",
                 ollama_url: str = "http://localhost:11434"):
        """
        Initialize Metadata Quality Agent.
        
        Args:
            agent_id: Unique identifier for this agent
            mcp_server_url: URL for MCP server
            ollama_url: URL for Ollama (Mistral model)
        """
        self.agent_id = agent_id
        self.mcp_server_url = mcp_server_url
        self.ollama_url = ollama_url
        
        # Load metadata standards
        self.standards = self._load_metadata_standards()
        
        # Load field definitions
        self.field_definitions = self._load_field_definitions()
        
        # Register with MCP server
        self._register_with_mcp()
        
        logger.info(f"Metadata Quality Agent {self.agent_id} initialized")
    
    def _load_metadata_standards(self) -> Dict:
        """Load metadata standards definitions."""
        return {
            "ISO_19115": {
                "name": "ISO 19115:2003 - Geographic Information - Metadata",
                "description": "International standard for describing geographic information and services",
                "category": "geospatial",
                "required_fields": [
                    "title", "abstract", "date", "identifier", 
                    "topic_category", "spatial_representation_type", 
                    "reference_system_info", "metadata_contact"
                ],
                "optional_fields": [
                    "keywords", "access_constraints", "use_constraints",
                    "data_quality_info", "lineage", "extent"
                ],
                "weight": 0.3  # Weight in overall score
            },
            "ASTM_E131": {
                "name": "ASTM E131 - Standard Terminology Relating to Molecular Spectroscopy",
                "description": "Standard terminology for molecular spectroscopy",
                "category": "spectroscopy",
                "required_fields": [
                    "spectrometer_type", "wavelength_range", "resolution",
                    "scan_speed", "apodization", "detector_type"
                ],
                "optional_fields": [
                    "beam_splitter", "light_source", "sample_preparation",
                    "atmospheric_compensation", "reference_material"
                ],
                "weight": 0.25
            },
            "ASTM_E1421": {
                "name": "ASTM E1421 - Standard Guide for Data Fields for Computerized IR Spectroscopy",
                "description": "Guide for data fields in computerized IR spectroscopy",
                "category": "spectroscopy",
                "required_fields": [
                    "spectrum_type", "x_units", "y_units", "x_first", "x_last",
                    "n_points", "first_x_value", "last_x_value"
                ],
                "optional_fields": [
                    "x_increment", "y_units_type", "source_reference",
                    "comments", "data_processing"
                ],
                "weight": 0.25
            },
            "NIR_Specific": {
                "name": "NIR-Specific Standards",
                "description": "Standards specific to Near-Infrared spectroscopy",
                "category": "nir",
                "required_fields": [
                    "sample_type", "sample_preparation", "measurement_geometry",
                    "temperature", "humidity", "measurement_date"
                ],
                "optional_fields": [
                    "sample_thickness", "sample_orientation", "reference_measurement",
                    "dark_measurement", "integration_time", "scans_averaged",
                    "spectrometer_serial_number", "calibration_date"
                ],
                "weight": 0.2
            },
            "Open_Science": {
                "name": "Open Science Metadata Standards",
                "description": "Standards for open science data sharing",
                "category": "open_science",
                "required_fields": [
                    "license", "creator", "contributor", "funding",
                    "data_availability", "repository", "version"
                ],
                "optional_fields": [
                    "doi", "citation", "keywords", "related_publications",
                    "data_quality", "ethics_approval", "anonymization"
                ],
                "weight": 0.15
            },
            "Federated_Learning": {
                "name": "Federated Learning Metadata Standards",
                "description": "Standards for federated learning data sharing",
                "category": "federated",
                "required_fields": [
                    "data_owner", "consent_status", "data_hash", 
                    "federation_id", "access_control"
                ],
                "optional_fields": [
                    "data_signature", "encryption_method", "retention_policy",
                    "usage_restrictions", "audit_trail"
                ],
                "weight": 0.05
            }
        }
    
    def _load_field_definitions(self) -> Dict[str, MetadataField]:
        """Load field definitions for metadata validation."""
        fields = {}
        
        # Basic fields
        fields["title"] = MetadataField(
            name="title",
            display_name="Title",
            description="Descriptive title of the dataset or measurement",
            data_type="string",
            required=True,
            standard="ISO_19115,Open_Science"
        )
        
        fields["description"] = MetadataField(
            name="description",
            display_name="Description",
            description="Detailed description of the dataset or measurement",
            data_type="string",
            required=True,
            standard="ISO_19115,Open_Science"
        )
        
        fields["date"] = MetadataField(
            name="date",
            display_name="Date",
            description="Date of measurement or data collection",
            data_type="date",
            required=True,
            standard="ISO_19115"
        )
        
        fields["identifier"] = MetadataField(
            name="identifier",
            display_name="Identifier",
            description="Unique identifier for the dataset",
            data_type="string",
            required=True,
            standard="ISO_19115"
        )
        
        # Spectroscopy-specific fields
        fields["spectrometer_type"] = MetadataField(
            name="spectrometer_type",
            display_name="Spectrometer Type",
            description="Type or model of the spectrometer used",
            data_type="string",
            required=True,
            standard="ASTM_E131,ASTM_E1421",
            possible_values=["Ocean Optics", "ASD FieldSpec", "Bruker", "DIY Raspberry", "DIY Arduino", "Other"]
        )
        
        fields["wavelength_range"] = MetadataField(
            name="wavelength_range",
            display_name="Wavelength Range",
            description="Wavelength range of the measurement in nm",
            data_type="string",
            required=True,
            standard="ASTM_E131,ASTM_E1421",
            format="range"  # e.g., "700-1100"
        )
        
        fields["resolution"] = MetadataField(
            name="resolution",
            display_name="Resolution",
            description="Spectral resolution in nm",
            data_type="number",
            required=True,
            standard="ASTM_E131",
            unit="nm"
        )
        
        fields["scan_speed"] = MetadataField(
            name="scan_speed",
            display_name="Scan Speed",
            description="Speed of the scan in scans per second",
            data_type="number",
            required=False,
            standard="ASTM_E131",
            unit="scans/s"
        )
        
        fields["detector_type"] = MetadataField(
            name="detector_type",
            display_name="Detector Type",
            description="Type of detector used",
            data_type="string",
            required=False,
            standard="ASTM_E131",
            possible_values=["InGaAs", "PbS", "Si", "MCT", "Other"]
        )
        
        fields["light_source"] = MetadataField(
            name="light_source",
            display_name="Light Source",
            description="Type of light source used",
            data_type="string",
            required=False,
            standard="ASTM_E131",
            possible_values=["Tungsten", "Halogen", "LED", "Laser", "Deuterium", "Other"]
        )
        
        # NIR-specific fields
        fields["sample_type"] = MetadataField(
            name="sample_type",
            display_name="Sample Type",
            description="Type of sample being measured",
            data_type="string",
            required=True,
            standard="NIR_Specific",
            possible_values=["Solid", "Liquid", "Gas", "Powder", "Film", "Other"]
        )
        
        fields["sample_preparation"] = MetadataField(
            name="sample_preparation",
            display_name="Sample Preparation",
            description="How the sample was prepared for measurement",
            data_type="string",
            required=True,
            standard="NIR_Specific"
        )
        
        fields["measurement_geometry"] = MetadataField(
            name="measurement_geometry",
            display_name="Measurement Geometry",
            description="Geometry of the measurement (reflectance, transmittance, etc.)",
            data_type="string",
            required=True,
            standard="NIR_Specific",
            possible_values=["Reflectance", "Transmittance", "Absorbance", "Emission", "Other"]
        )
        
        fields["temperature"] = MetadataField(
            name="temperature",
            display_name="Temperature",
            description="Temperature during measurement in Celsius",
            data_type="number",
            required=True,
            standard="NIR_Specific",
            unit="°C"
        )
        
        fields["humidity"] = MetadataField(
            name="humidity",
            display_name="Humidity",
            description="Relative humidity during measurement in %",
            data_type="number",
            required=True,
            standard="NIR_Specific",
            unit="%"
        )
        
        fields["integration_time"] = MetadataField(
            name="integration_time",
            display_name="Integration Time",
            description="Integration time for each scan in milliseconds",
            data_type="number",
            required=False,
            standard="NIR_Specific",
            unit="ms"
        )
        
        fields["scans_averaged"] = MetadataField(
            name="scans_averaged",
            display_name="Scans Averaged",
            description="Number of scans that were averaged",
            data_type="number",
            required=False,
            standard="NIR_Specific"
        )
        
        # Open Science fields
        fields["license"] = MetadataField(
            name="license",
            display_name="License",
            description="License under which the data is shared",
            data_type="string",
            required=True,
            standard="Open_Science",
            possible_values=["CC-BY", "CC-BY-SA", "CC-BY-NC", "MIT", "Apache-2.0", "GPL-3.0", "Other"]
        )
        
        fields["creator"] = MetadataField(
            name="creator",
            display_name="Creator",
            description="Person or organization who created the data",
            data_type="string",
            required=True,
            standard="Open_Science"
        )
        
        fields["contributor"] = MetadataField(
            name="contributor",
            display_name="Contributor",
            description="Other contributors to the data",
            data_type="string",
            required=False,
            standard="Open_Science"
        )
        
        fields["data_availability"] = MetadataField(
            name="data_availability",
            display_name="Data Availability",
            description="Where and how the data can be accessed",
            data_type="string",
            required=True,
            standard="Open_Science"
        )
        
        # Federated Learning fields
        fields["data_owner"] = MetadataField(
            name="data_owner",
            display_name="Data Owner",
            description="Owner of the data",
            data_type="string",
            required=True,
            standard="Federated_Learning"
        )
        
        fields["consent_status"] = MetadataField(
            name="consent_status",
            display_name="Consent Status",
            description="User consent status for federated learning",
            data_type="string",
            required=True,
            standard="Federated_Learning",
            possible_values=["granted", "denied", "pending"]
        )
        
        fields["data_hash"] = MetadataField(
            name="data_hash",
            display_name="Data Hash",
            description="Hash of the data for integrity verification",
            data_type="string",
            required=True,
            standard="Federated_Learning"
        )
        
        return fields
    
    def _register_with_mcp(self):
        """Register this agent with the MCP server."""
        agent_data = {
            "id": self.agent_id,
            "name": "Metadata Quality Agent",
            "description": "Evaluates metadata quality against international standards and provides grading",
            "capabilities": [
                "validate_metadata",
                "assess_completeness",
                "check_standards_compliance",
                "calculate_quality_score",
                "generate_grade",
                "provide_enhancement_recommendations",
                "generate_compliance_report"
            ],
            "version": "1.0.0",
            "endpoints": [
                "/analysis/metadata",
                "/analysis/quality",
                "/analysis/compliance"
            ]
        }
        
        logger.info(f"Registering agent with MCP server: {agent_data}")
    
    async def evaluate_metadata_quality(self, 
                                       metadata: Dict[str, Any],
                                       spectral_data: Optional[Dict] = None) -> MetadataQualityResult:
        """
        Evaluate the quality of metadata against all supported standards.
        
        Args:
            metadata: Dictionary containing metadata to evaluate
            spectral_data: Optional spectral data for context
            
        Returns:
            MetadataQualityResult with full analysis
        """
        logger.info("Starting metadata quality evaluation")
        
        # Step 1: Normalize metadata (convert to lowercase keys, etc.)
        normalized_metadata = self._normalize_metadata(metadata)
        
        # Step 2: Validate individual fields
        field_scores, missing_fields, invalid_fields = self._validate_fields(normalized_metadata)
        
        # Step 3: Check compliance with each standard
        compliance_scores, standards_compliance = self._check_standards_compliance(normalized_metadata)
        
        # Step 4: Generate enhancement recommendations
        enhancement_recommendations = self._generate_enhancement_recommendations(
            normalized_metadata, missing_fields, invalid_fields, standards_compliance
        )
        
        # Step 5: Calculate overall score
        overall_score = self._calculate_overall_score(
            field_scores, compliance_scores, missing_fields, invalid_fields
        )
        
        # Step 6: Determine grade
        grade = self._determine_grade(overall_score)
        
        # Create result
        result = MetadataQualityResult(
            metadata=normalized_metadata,
            compliance_scores=compliance_scores,
            field_scores=field_scores,
            overall_score=overall_score,
            grade=grade,
            missing_fields=missing_fields,
            invalid_fields=invalid_fields,
            enhancement_recommendations=enhancement_recommendations,
            standards_compliance=standards_compliance
        )
        
        logger.info(f"Metadata quality evaluation complete. Score: {overall_score:.2f}, Grade: {grade}")
        
        return result
    
    def _normalize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize metadata keys and values."""
        normalized = {}
        
        # Create mapping of common variations to standard names
        key_mapping = {
            "name": "title",
            "desc": "description",
            "desc": "description",
            "date_created": "date",
            "creation_date": "date",
            "measurement_date": "date",
            "id": "identifier",
            "sample": "sample_type",
            "sample_type": "sample_type",
            "type": "sample_type",
            "prep": "sample_preparation",
            "preparation": "sample_preparation",
            "temp": "temperature",
            "temperature_c": "temperature",
            "hum": "humidity",
            "rh": "humidity",
            "res": "resolution",
            "spectral_resolution": "resolution",
            "wl_range": "wavelength_range",
            "wavelengths": "wavelength_range",
            "spec_type": "spectrometer_type",
            "spectrometer": "spectrometer_type",
            "model": "spectrometer_type"
        }
        
        # Normalize keys
        for key, value in metadata.items():
            key_lower = key.lower().strip()
            
            # Map to standard key
            standard_key = key_mapping.get(key_lower, key_lower)
            
            # Convert value based on expected type
            normalized_value = self._normalize_value(standard_key, value)
            
            normalized[standard_key] = normalized_value
        
        return normalized
    
    def _normalize_value(self, key: str, value: Any) -> Any:
        """Normalize a metadata value based on its key."""
        if value is None:
            return None
        
        # Convert string numbers to actual numbers
        if isinstance(value, str):
            # Try to convert to number
            try:
                if '.' in value:
                    return float(value)
                else:
                    return int(value)
            except ValueError:
                pass
            
            # Clean up strings
            value = value.strip()
            
            # Convert common date formats
            if key in ['date', 'measurement_date', 'creation_date', 'calibration_date']:
                try:
                    return datetime.fromisoformat(value)
                except:
                    try:
                        return datetime.strptime(value, "%Y-%m-%d")
                    except:
                        try:
                            return datetime.strptime(value, "%d/%m/%Y")
                        except:
                            pass
        
        return value
    
    def _validate_fields(self, metadata: Dict[str, Any]) -> Tuple[Dict[str, Dict], List[str], List[Dict]]:
        """Validate all metadata fields against definitions."""
        field_scores = {}
        missing_fields = []
        invalid_fields = []
        
        # Check all defined fields
        for field_name, field_def in self.field_definitions.items():
            value = metadata.get(field_name)
            is_valid, error_message = field_def.validate(value)
            
            # Calculate score for this field
            if field_def.required:
                if value is None:
                    score = 0.0
                    missing_fields.append(field_name)
                elif not is_valid:
                    score = 0.3  # Partial credit for present but invalid
                    invalid_fields.append({
                        "field": field_name,
                        "error": error_message,
                        "value": value
                    })
                else:
                    score = 1.0
            else:
                if value is None:
                    score = 0.5  # Optional field not present
                elif not is_valid:
                    score = 0.7  # Optional field present but invalid
                    invalid_fields.append({
                        "field": field_name,
                        "error": error_message,
                        "value": value
                    })
                else:
                    score = 1.0
            
            field_scores[field_name] = {
                "score": score,
                "valid": is_valid,
                "required": field_def.required,
                "standard": field_def.standard,
                "error": error_message if not is_valid else None
            }
        
        # Check for unknown fields (not in definitions)
        for field_name in metadata:
            if field_name not in self.field_definitions:
                # This is an extra field, give partial credit
                field_scores[field_name] = {
                    "score": 0.3,
                    "valid": True,
                    "required": False,
                    "standard": "extra",
                    "error": None
                }
        
        return field_scores, missing_fields, invalid_fields
    
    def _check_standards_compliance(self, metadata: Dict[str, Any]) -> Tuple[Dict[str, float], Dict[str, Dict]]:
        """Check compliance with each metadata standard."""
        compliance_scores = {}
        standards_compliance = {}
        
        for standard_name, standard_info in self.standards.items():
            required_fields = standard_info.get("required_fields", [])
            optional_fields = standard_info.get("optional_fields", [])
            
            # Check required fields
            required_present = 0
            for field in required_fields:
                if field in metadata and metadata[field] is not None:
                    required_present += 1
            
            required_score = required_present / len(required_fields) if required_fields else 1.0
            
            # Check optional fields
            optional_present = 0
            for field in optional_fields:
                if field in metadata and metadata[field] is not None:
                    optional_present += 1
            
            optional_score = optional_present / len(optional_fields) if optional_fields else 0.0
            
            # Calculate overall compliance score for this standard
            compliance_score = (required_score * 0.7 + optional_score * 0.3) * 100
            compliance_scores[standard_name] = round(compliance_score, 2)
            
            # Store detailed compliance info
            standards_compliance[standard_name] = {
                "required_fields_present": required_present,
                "required_fields_total": len(required_fields),
                "optional_fields_present": optional_present,
                "optional_fields_total": len(optional_fields),
                "required_score": round(required_score, 4),
                "optional_score": round(optional_score, 4),
                "compliance_score": compliance_score,
                "missing_required": [f for f in required_fields if f not in metadata or metadata[f] is None],
                "missing_optional": [f for f in optional_fields if f not in metadata or metadata[f] is None]
            }
        
        return compliance_scores, standards_compliance
    
    def _generate_enhancement_recommendations(self, 
                                              metadata: Dict[str, Any],
                                              missing_fields: List[str],
                                              invalid_fields: List[Dict],
                                              standards_compliance: Dict[str, Dict]) -> List[Dict]:
        """Generate recommendations for improving metadata quality."""
        recommendations = []
        
        # Recommendations for missing required fields
        for field in missing_fields:
            if field in self.field_definitions:
                field_def = self.field_definitions[field]
                recommendations.append({
                    "type": "missing_field",
                    "priority": "high",
                    "field": field,
                    "display_name": field_def.display_name,
                    "description": field_def.description,
                    "standard": field_def.standard,
                    "recommendation": f"Add {field_def.display_name} to your metadata. {field_def.description}"
                })
        
        # Recommendations for invalid fields
        for invalid in invalid_fields:
            field = invalid["field"]
            if field in self.field_definitions:
                field_def = self.field_definitions[field]
                recommendations.append({
                    "type": "invalid_field",
                    "priority": "high",
                    "field": field,
                    "display_name": field_def.display_name,
                    "error": invalid["error"],
                    "current_value": invalid["value"],
                    "recommendation": f"Fix the {field_def.display_name} field. {invalid['error']}"
                })
        
        # Recommendations for standards compliance
        for standard_name, compliance in standards_compliance.items():
            if compliance["compliance_score"] < 70:
                missing_required = compliance["missing_required"]
                if missing_required:
                    recommendations.append({
                        "type": "standard_compliance",
                        "priority": "medium",
                        "standard": standard_name,
                        "current_score": compliance["compliance_score"],
                        "missing_required_fields": missing_required,
                        "recommendation": f"Improve compliance with {standard_name}. Add missing required fields: {', '.join(missing_required)}"
                    })
        
        # General recommendations
        if len(missing_fields) > 5:
            recommendations.append({
                "type": "general",
                "priority": "high",
                "description": "Many required fields are missing",
                "recommendation": "Consider using a metadata template to ensure all required fields are included"
            })
        
        if len(invalid_fields) > 3:
            recommendations.append({
                "type": "general",
                "priority": "medium",
                "description": "Multiple field validation errors",
                "recommendation": "Review your metadata values for correct formats and data types"
            })
        
        # Recommend adding open science metadata if missing
        open_science_fields = ["license", "creator", "data_availability"]
        missing_open_science = [f for f in open_science_fields if f not in metadata or metadata[f] is None]
        if missing_open_science:
            recommendations.append({
                "type": "open_science",
                "priority": "medium",
                "missing_fields": missing_open_science,
                "recommendation": "Add open science metadata to enable data sharing and reuse"
            })
        
        # Sort recommendations by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2))
        
        return recommendations
    
    def _calculate_overall_score(self, 
                                  field_scores: Dict[str, Dict],
                                  compliance_scores: Dict[str, float],
                                  missing_fields: List[str],
                                  invalid_fields: List[Dict]) -> float:
        """Calculate overall metadata quality score (0-100)."""
        # Calculate field score component
        total_fields = len(field_scores)
        if total_fields > 0:
            field_score = sum(f["score"] for f in field_scores.values()) / total_fields * 100
        else:
            field_score = 0.0
        
        # Calculate compliance score component
        total_standards = len(compliance_scores)
        if total_standards > 0:
            compliance_score = sum(compliance_scores.values()) / total_standards
        else:
            compliance_score = 0.0
        
        # Penalize for missing required fields
        missing_penalty = len(missing_fields) * 2.0
        
        # Penalize for invalid fields
        invalid_penalty = len(invalid_fields) * 1.5
        
        # Calculate weighted score
        # Field score: 40%, Compliance: 40%, Penalties: 20%
        overall_score = (field_score * 0.4 + compliance_score * 0.4) - (missing_penalty + invalid_penalty) * 0.2
        
        # Ensure score is between 0 and 100
        overall_score = max(0, min(100, overall_score))
        
        return round(overall_score, 2)
    
    def _determine_grade(self, score: float) -> str:
        """Determine letter grade based on score."""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "A-"
        elif score >= 80:
            return "B+"
        elif score >= 75:
            return "B"
        elif score >= 70:
            return "B-"
        elif score >= 65:
            return "C+"
        elif score >= 60:
            return "C"
        elif score >= 55:
            return "C-"
        elif score >= 50:
            return "D+"
        elif score >= 45:
            return "D"
        else:
            return "F"
    
    async def generate_compliance_report(self, 
                                         metadata: Dict[str, Any],
                                         spectral_data: Optional[Dict] = None) -> Dict:
        """Generate a comprehensive compliance report."""
        # First evaluate quality
        result = await self.evaluate_metadata_quality(metadata, spectral_data)
        
        # Generate report
        report = {
            "metadata": metadata,
            "quality_assessment": {
                "overall_score": result.overall_score,
                "grade": result.grade,
                "compliance_scores": result.compliance_scores,
                "missing_fields": result.missing_fields,
                "invalid_fields": result.invalid_fields
            },
            "standards_compliance": result.standards_compliance,
            "enhancement_recommendations": result.enhancement_recommendations,
            "summary": self._generate_summary(result),
            "timestamp": datetime.now().isoformat()
        }
        
        return report
    
    def _generate_summary(self, result: MetadataQualityResult) -> Dict:
        """Generate a summary of the quality assessment."""
        summary = {
            "total_fields_checked": len(result.field_scores),
            "fields_present": len([f for f in result.field_scores.values() if f["score"] > 0]),
            "required_fields_missing": len(result.missing_fields),
            "fields_invalid": len(result.invalid_fields),
            "standards_checked": len(result.compliance_scores),
            "average_compliance_score": np.mean(list(result.compliance_scores.values())) if result.compliance_scores else 0,
            "highest_compliance": max(result.compliance_scores.values()) if result.compliance_scores else 0,
            "lowest_compliance": min(result.compliance_scores.values()) if result.compliance_scores else 0,
            "recommendations_count": len(result.enhancement_recommendations),
            "high_priority_recommendations": len([r for r in result.enhancement_recommendations if r.get("priority") == "high"]),
            "medium_priority_recommendations": len([r for r in result.enhancement_recommendations if r.get("priority") == "medium"])
        }
        
        # Add narrative summary
        if result.overall_score >= 90:
            summary["narrative"] = "Excellent metadata quality. All required fields are present and valid. Data is well-documented and compliant with major standards."
        elif result.overall_score >= 70:
            summary["narrative"] = "Good metadata quality. Most required fields are present, but some improvements could be made for better compliance with standards."
        elif result.overall_score >= 50:
            summary["narrative"] = "Fair metadata quality. Several required fields are missing or invalid. Significant improvements are needed for data reuse."
        else:
            summary["narrative"] = "Poor metadata quality. Many required fields are missing or invalid. Data may not be reusable without significant additional documentation."
        
        return summary
    
    async def suggest_metadata_template(self, 
                                       metadata: Dict[str, Any],
                                       standard: str = "NIR_Specific") -> Dict:
        """Suggest a metadata template based on existing metadata and selected standard."""
        if standard not in self.standards:
            raise ValueError(f"Unknown standard: {standard}")
        
        standard_info = self.standards[standard]
        required_fields = standard_info.get("required_fields", [])
        optional_fields = standard_info.get("optional_fields", [])
        
        # Create template
        template = {
            "standard": standard,
            "standard_name": standard_info.get("name", standard),
            "required_fields": {},
            "optional_fields": {},
            "current_values": {}
        }
        
        # Add required fields with descriptions
        for field in required_fields:
            if field in self.field_definitions:
                field_def = self.field_definitions[field]
                template["required_fields"][field] = {
                    "display_name": field_def.display_name,
                    "description": field_def.description,
                    "data_type": field_def.data_type,
                    "unit": field_def.unit,
                    "format": field_def.format,
                    "possible_values": field_def.possible_values,
                    "current_value": metadata.get(field)
                }
        
        # Add optional fields
        for field in optional_fields:
            if field in self.field_definitions:
                field_def = self.field_definitions[field]
                template["optional_fields"][field] = {
                    "display_name": field_def.display_name,
                    "description": field_def.description,
                    "data_type": field_def.data_type,
                    "unit": field_def.unit,
                    "format": field_def.format,
                    "possible_values": field_def.possible_values,
                    "current_value": metadata.get(field)
                }
        
        # Add current values for fields not in standard
        for field, value in metadata.items():
            if field not in required_fields and field not in optional_fields:
                template["current_values"][field] = value
        
        return template
    
    async def validate_for_federated_learning(self, 
                                             metadata: Dict[str, Any]) -> Dict:
        """Validate metadata for federated learning compatibility."""
        # Check for federated learning specific fields
        fl_standard = self.standards.get("Federated_Learning", {})
        fl_required = fl_standard.get("required_fields", [])
        
        validation = {
            "federated_learning_compatible": True,
            "missing_required_fields": [],
            "issues": [],
            "recommendations": []
        }
        
        # Check required fields
        for field in fl_required:
            if field not in metadata or metadata[field] is None:
                validation["federated_learning_compatible"] = False
                validation["missing_required_fields"].append(field)
                
                if field in self.field_definitions:
                    field_def = self.field_definitions[field]
                    validation["issues"].append({
                        "field": field,
                        "display_name": field_def.display_name,
                        "description": field_def.description,
                        "severity": "high"
                    })
        
        # Check consent status
        consent = metadata.get("consent_status")
        if consent != "granted":
            validation["federated_learning_compatible"] = False
            validation["issues"].append({
                "field": "consent_status",
                "display_name": "Consent Status",
                "description": "User consent for federated learning",
                "severity": "high",
                "current_value": consent
            })
            
            validation["recommendations"].append({
                "type": "consent",
                "priority": "high",
                "description": "User consent required for federated learning",
                "recommendation": "Obtain explicit user consent before sharing data with federated learning system"
            })
        
        # Check data hash
        data_hash = metadata.get("data_hash")
        if not data_hash:
            validation["recommendations"].append({
                "type": "data_integrity",
                "priority": "medium",
                "description": "Data hash missing",
                "recommendation": "Add data hash for integrity verification in federated learning"
            })
        
        # Check data owner
        data_owner = metadata.get("data_owner")
        if not data_owner:
            validation["recommendations"].append({
                "type": "ownership",
                "priority": "medium",
                "description": "Data owner not specified",
                "recommendation": "Specify data owner for proper attribution and access control"
            })
        
        return validation


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def example_usage():
        # Create agent
        agent = MetadataQualityAgent()
        
        # Example metadata
        metadata = {
            "title": "NIR Spectrum of Wheat Sample",
            "description": "Near-infrared spectrum of wheat grain sample",
            "date": "2024-01-15",
            "spectrometer_type": "Ocean Optics",
            "wavelength_range": "700-1100",
            "resolution": 0.5,
            "sample_type": "Solid",
            "sample_preparation": "Ground and sieved",
            "measurement_geometry": "Reflectance",
            "temperature": 22.5,
            "humidity": 45.0,
            "license": "CC-BY",
            "creator": "John Doe"
        }
        
        # Evaluate quality
        result = await agent.evaluate_metadata_quality(metadata)
        
        print(f"Metadata Quality Score: {result.overall_score}")
        print(f"Grade: {result.grade}")
        print(f"Missing fields: {result.missing_fields}")
        print(f"Invalid fields: {len(result.invalid_fields)}")
        print(f"Recommendations: {len(result.enhancement_recommendations)}")
        
        # Generate compliance report
        report = await agent.generate_compliance_report(metadata)
        print(f"\nCompliance Report Summary:")
        print(f"Narrative: {report['summary']['narrative']}")
        
        # Validate for federated learning
        fl_validation = await agent.validate_for_federated_learning(metadata)
        print(f"\nFederated Learning Compatible: {fl_validation['federated_learning_compatible']}")
        print(f"Missing fields: {fl_validation['missing_required_fields']}")
    
    asyncio.run(example_usage())
