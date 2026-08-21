# NIR Intelligence Platform - Crew AI API Views
# Django REST Framework views for Crew AI integration

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List

from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

# Import path configuration
from path_config import setup_project_paths
setup_project_paths()

# Import NIR Analysis Crew
try:
    from agents.nir_analysis_crew import (
        NIRAnalysisCrew, 
        AnalysisRequest, 
        AnalysisResult,
        AnalysisMode,
        PrivacyLevel,
        ReportType,
        ReportFormat,
        CrewConfiguration,
        analyze_spectral_data,
        nir_analysis_crew
    )
    CREW_AVAILABLE = True
except ImportError as e:
    CREW_AVAILABLE = False
    print(f"Warning: Could not import NIR Analysis Crew: {e}")


# Global crew instance for API
api_crew = None


def get_crew_instance():
    """Get or create the Crew AI instance for API"""
    global api_crew
    if api_crew is None:
        config = CrewConfiguration(
            enable_crewai=True,
            enable_federated_learning=True,
            default_analysis_mode=AnalysisMode.STANDARD,
            default_privacy_level=PrivacyLevel.LOCAL_ONLY,
            default_report_type=ReportType.COMPREHENSIVE,
            default_report_format=ReportFormat.HTML,
            max_batch_size=10,
            temp_dir=str(Path(settings.BASE_DIR) / "temp" / "crewai"),
            output_dir=str(Path(settings.BASE_DIR) / "output" / "analysis")
        )
        api_crew = NIRAnalysisCrew(config)
    return api_crew


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def start_analysis(request):
    """
    Start a new spectral analysis.
    
    Expects JSON payload with:
    {
        "sample_id": "unique_sample_id",
        "spectral_data": {
            "wavelengths": [700, 710, 720, ...],
            "intensities": [100, 120, 110, ...],
            "sample_id": "unique_sample_id"
        },
        "metadata": {
            "instrument_type": "DIY Spectrometer",
            "measurement_date": "2026-08-05T10:00:00Z",
            ...
        },
        "analysis_mode": "standard",  # standard, comprehensive, quick, batch
        "privacy_level": "local_only",  # local_only, public_federated, private_federated
        "report_type": "comprehensive",  # spectral_analysis, metadata_quality, comprehensive, comparison, calibration
        "report_format": "html",  # html, pdf, docx, md, qmd
        "include_calibration": true,
        "include_federated_learning": false,
        "user_id": "optional_user_id"
    }
    """
    if not CREW_AVAILABLE:
        return Response(
            {"error": "NIR Analysis Crew not available", "available": False},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    try:
        # Parse request data
        payload = json.loads(request.body)
        
        # Validate required fields
        if 'sample_id' not in payload:
            return Response(
                {"error": "sample_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if 'spectral_data' not in payload:
            return Response(
                {"error": "spectral_data is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        spectral_data = payload['spectral_data']
        if 'wavelengths' not in spectral_data or 'intensities' not in spectral_data:
            return Response(
                {"error": "spectral_data must contain wavelengths and intensities"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create analysis request
        analysis_request = AnalysisRequest(
            sample_id=payload.get('sample_id'),
            spectral_data=spectral_data,
            metadata=payload.get('metadata', {}),
            file_paths=payload.get('file_paths', []),
            analysis_mode=AnalysisMode(payload.get('analysis_mode', 'standard')),
            privacy_level=PrivacyLevel(payload.get('privacy_level', 'local_only')),
            report_type=ReportType(payload.get('report_type', 'comprehensive')),
            report_format=ReportFormat(payload.get('report_format', 'html')),
            include_calibration=payload.get('include_calibration', True),
            include_federated_learning=payload.get('include_federated_learning', False),
            user_id=payload.get('user_id', None)
        )
        
        # Get crew instance
        crew = get_crew_instance()
        
        # Perform analysis
        result = crew.analyze_sample(analysis_request)
        
        # Generate summary
        summary = crew.get_analysis_summary(result)
        
        # Prepare response
        response_data = {
            "success": len(result.errors) == 0,
            "request_id": result.request_id,
            "sample_id": result.sample_id,
            "timestamp": result.timestamp,
            "overall_quality_score": result.overall_quality_score,
            "processing_time": result.processing_time,
            "privacy_level": result.privacy_level.value,
            "summary": summary,
            "recommendations": result.recommendations,
            "warnings": result.warnings,
            "errors": result.errors,
            "reports": [
                {
                    "report_id": report.report_id,
                    "report_type": report.report_type.value,
                    "format": report.format.value,
                    "status": report.status.value,
                    "file_path": report.file_path,
                    "file_size": report.file_size,
                    "preview_available": report.preview_available
                }
                for report in result.generated_reports
            ]
        }
        
        # Add spectral analysis details if available
        if result.spectral_analysis:
            response_data["spectral_analysis"] = {
                "quality_score": result.spectral_analysis.quality_score,
                "quality_grade": result.spectral_analysis.quality_grade.value,
                "wavelength_range": list(result.spectral_analysis.wavelength_range),
                "data_points": result.spectral_analysis.data_points,
                "issues_detected": [issue.value for issue in result.spectral_analysis.issues_detected],
                "noise_level": result.spectral_analysis.noise_level,
                "signal_to_noise_ratio": result.spectral_analysis.signal_to_noise_ratio,
                "shift_detected": result.spectral_analysis.shift_detected,
                "recommendations": result.spectral_analysis.recommendations
            }
        
        # Add metadata quality details if available
        if result.metadata_quality:
            response_data["metadata_quality"] = {
                "overall_score": result.metadata_quality.overall_quality_score,
                "grade": result.metadata_quality.overall_quality_grade.value,
                "completeness_score": result.metadata_quality.completeness_score,
                "accuracy_score": result.metadata_quality.accuracy_score,
                "consistency_score": result.metadata_quality.consistency_score,
                "missing_required_fields": result.metadata_quality.missing_required_fields,
                "recommendations": result.metadata_quality.recommendations,
                "enhancements": result.metadata_quality.enhancements
            }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except json.JSONDecodeError:
        return Response(
            {"error": "Invalid JSON payload"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Analysis failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
def get_analysis_status(request):
    """
    Get status of a specific analysis by request ID.
    
    Query parameters:
    - request_id: The analysis request ID
    """
    if not CREW_AVAILABLE:
        return Response(
            {"error": "NIR Analysis Crew not available"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    try:
        request_id = request.GET.get('request_id')
        if not request_id:
            return Response(
                {"error": "request_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        crew = get_crew_instance()
        
        # Find the analysis result in history
        for result in crew.analysis_history:
            if result.request_id == request_id:
                summary = crew.get_analysis_summary(result)
                return Response({
                    "found": True,
                    "request_id": result.request_id,
                    "sample_id": result.sample_id,
                    "status": "completed",
                    "timestamp": result.timestamp,
                    "summary": summary
                }, status=status.HTTP_200_OK)
        
        return Response({
            "found": False,
            "error": f"Analysis request {request_id} not found"
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        return Response(
            {"error": f"Failed to get analysis status: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
def get_analysis_history(request):
    """
    Get analysis history.
    
    Query parameters:
    - limit: Maximum number of results to return (default: 100)
    """
    if not CREW_AVAILABLE:
        return Response(
            {"error": "NIR Analysis Crew not available"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    try:
        limit = int(request.GET.get('limit', 100))
        crew = get_crew_instance()
        history = crew.get_analysis_history(limit)
        
        return Response({
            "success": True,
            "count": len(history),
            "limit": limit,
            "history": history
        }, status=status.HTTP_200_OK)
        
    except ValueError:
        return Response(
            {"error": "Invalid limit parameter"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to get analysis history: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
def get_report_preview(request):
    """
    Get preview of a generated report.
    
    Query parameters:
    - report_id: The report ID
    """
    if not CREW_AVAILABLE:
        return Response(
            {"error": "NIR Analysis Crew not available"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    try:
        report_id = request.GET.get('report_id')
        if not report_id:
            return Response(
                {"error": "report_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        crew = get_crew_instance()
        
        # Find the report in generated reports
        for result in crew.analysis_history:
            for report in result.generated_reports:
                if report.report_id == report_id:
                    if report.preview_available:
                        preview_html = crew.reporting_agent.generate_html_preview(report)
                        if preview_html:
                            return Response({
                                "success": True,
                                "report_id": report.report_id,
                                "preview": preview_html
                            }, status=status.HTTP_200_OK)
                        else:
                            return Response(
                                {"error": "Preview not available"},
                                status=status.HTTP_404_NOT_FOUND
                            )
        
        return Response({
            "found": False,
            "error": f"Report {report_id} not found"
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        return Response(
            {"error": f"Failed to get report preview: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def batch_analysis(request):
    """
    Perform batch analysis on multiple samples.
    
    Expects JSON payload with:
    {
        "requests": [
            {
                "sample_id": "sample1",
                "spectral_data": {...},
                "metadata": {...}
            },
            {
                "sample_id": "sample2",
                "spectral_data": {...},
                "metadata": {...}
            }
        ],
        "analysis_mode": "standard",
        "privacy_level": "local_only",
        "report_type": "comprehensive",
        "report_format": "html",
        "include_calibration": true,
        "include_federated_learning": false
    }
    """
    if not CREW_AVAILABLE:
        return Response(
            {"error": "NIR Analysis Crew not available"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    try:
        payload = json.loads(request.body)
        
        if 'requests' not in payload or not isinstance(payload['requests'], list):
            return Response(
                {"error": "requests array is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        requests_list = payload['requests']
        if len(requests_list) == 0:
            return Response(
                {"error": "At least one request is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert requests to AnalysisRequest objects
        analysis_requests = []
        for req_data in requests_list:
            analysis_request = AnalysisRequest(
                sample_id=req_data.get('sample_id', f'sample_{len(analysis_requests) + 1}'),
                spectral_data=req_data.get('spectral_data', {}),
                metadata=req_data.get('metadata', {}),
                file_paths=req_data.get('file_paths', []),
                analysis_mode=AnalysisMode(payload.get('analysis_mode', 'standard')),
                privacy_level=PrivacyLevel(payload.get('privacy_level', 'local_only')),
                report_type=ReportType(payload.get('report_type', 'comprehensive')),
                report_format=ReportFormat(payload.get('report_format', 'html')),
                include_calibration=payload.get('include_calibration', True),
                include_federated_learning=payload.get('include_federated_learning', False),
                user_id=payload.get('user_id', None)
            )
            analysis_requests.append(analysis_request)
        
        # Get crew instance
        crew = get_crew_instance()
        
        # Perform batch analysis
        results = crew.analyze_batch(analysis_requests)
        
        # Prepare response
        response_data = {
            "success": True,
            "processed": len(results),
            "successful": sum(1 for r in results if not r.errors),
            "failed": sum(1 for r in results if r.errors),
            "results": []
        }
        
        for result in results:
            summary = crew.get_analysis_summary(result)
            response_data["results"].append({
                "request_id": result.request_id,
                "sample_id": result.sample_id,
                "success": len(result.errors) == 0,
                "overall_quality_score": result.overall_quality_score,
                "processing_time": result.processing_time,
                "errors": result.errors,
                "warnings": result.warnings,
                "summary": summary
            })
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except json.JSONDecodeError:
        return Response(
            {"error": "Invalid JSON payload"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Batch analysis failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
def get_crew_status(request):
    """
    Get status and configuration of the Crew AI system.
    """
    if not CREW_AVAILABLE:
        return Response(
            {"available": False, "error": "NIR Analysis Crew not available"},
            status=status.HTTP_200_OK
        )
    
    try:
        crew = get_crew_instance()
        
        response_data = {
            "available": True,
            "crewai_enabled": crew.config.enable_crewai,
            "federated_learning_enabled": crew.config.enable_federated_learning,
            "max_batch_size": crew.config.max_batch_size,
            "default_analysis_mode": crew.config.default_analysis_mode.value,
            "default_privacy_level": crew.config.default_privacy_level.value,
            "default_report_type": crew.config.default_report_type.value,
            "default_report_format": crew.config.default_report_format.value,
            "analysis_history_count": len(crew.analysis_history),
            "agents": {
                "spectral_analysis": "available",
                "metadata_quality": "available", 
                "reporting": "available",
                "calibration": "available",
                "flower": "available" if crew.flower_agent else "disabled"
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": f"Failed to get crew status: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def cleanup_resources(request):
    """
    Clean up old analysis resources.
    
    Expects JSON payload with:
    {
        "max_age_days": 30  # Optional, default 30
    }
    """
    if not CREW_AVAILABLE:
        return Response(
            {"error": "NIR Analysis Crew not available"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    try:
        payload = json.loads(request.body) if request.body else {}
        max_age_days = payload.get('max_age_days', 30)
        
        crew = get_crew_instance()
        cleanup_results = crew.cleanup_resources(max_age_days)
        
        return Response({
            "success": True,
            "cleanup_results": cleanup_results
        }, status=status.HTTP_200_OK)
        
    except json.JSONDecodeError:
        return Response(
            {"error": "Invalid JSON payload"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Cleanup failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
def get_report_list(request):
    """
    List all generated reports.
    
    Query parameters:
    - limit: Maximum number of reports to return (default: 100)
    """
    if not CREW_AVAILABLE:
        return Response(
            {"error": "NIR Analysis Crew not available"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    try:
        limit = int(request.GET.get('limit', 100))
        crew = get_crew_instance()
        reports = crew.reporting_agent.list_generated_reports(limit)
        
        response_data = {
            "success": True,
            "count": len(reports),
            "limit": limit,
            "reports": [
                {
                    "report_id": report.report_id,
                    "report_type": report.report_type.value,
                    "format": report.format.value,
                    "status": report.status.value,
                    "file_path": report.file_path,
                    "file_size": report.file_size,
                    "created_timestamp": report.created_timestamp,
                    "preview_available": report.preview_available
                }
                for report in reports
            ]
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except ValueError:
        return Response(
            {"error": "Invalid limit parameter"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to list reports: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def federated_learning_contribution(request):
    """
    Contribute data to federated learning (requires authentication).
    
    Expects JSON payload with:
    {
        "sample_id": "unique_sample_id",
        "spectral_data": {...},
        "metadata": {...},
        "analysis_results": {...},
        "privacy_level": "public_federated" or "private_federated",
        "consent_given": true
    }
    """
    if not CREW_AVAILABLE:
        return Response(
            {"error": "NIR Analysis Crew not available"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    try:
        payload = json.loads(request.body)
        
        # Check required fields
        if 'consent_given' not in payload or not payload['consent_given']:
            return Response(
                {"error": "User consent is required for federated learning"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if 'privacy_level' not in payload:
            return Response(
                {"error": "privacy_level is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        privacy_level = payload['privacy_level']
        if privacy_level not in ['public_federated', 'private_federated']:
            return Response(
                {"error": "privacy_level must be 'public_federated' or 'private_federated'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        crew = get_crew_instance()
        
        # Check if federated learning is enabled
        if not crew.config.enable_federated_learning or not crew.flower_agent:
            return Response(
                {"error": "Federated learning is not enabled"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # Process federated learning contribution
        fl_context = {
            'spectral_data': payload.get('spectral_data', {}),
            'metadata': payload.get('metadata', {}),
            'analysis_results': payload.get('analysis_results', {}),
            'user_id': request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
            'sample_id': payload.get('sample_id', 'unknown'),
            'privacy_level': privacy_level,
            'consent_given': True
        }
        
        fl_output = crew.flower_agent.execute(fl_context)
        
        if fl_output.status.name == 'COMPLETED':
            return Response({
                "success": True,
                "message": "Data successfully contributed to federated learning",
                "contribution_id": fl_output.data.get('contribution_id', 'unknown')
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success": False,
                "error": "Federated learning contribution failed",
                "details": fl_output.errors
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except json.JSONDecodeError:
        return Response(
            {"error": "Invalid JSON payload"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Federated learning contribution failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Simple function-based views for compatibility
@csrf_exempt
def crewai_analysis(request):
    """Legacy endpoint for Crew AI analysis"""
    if request.method == 'POST':
        return start_analysis(request)
    else:
        return Response(
            {"error": "Method not allowed"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )


@csrf_exempt
def crewai_status(request):
    """Legacy endpoint for Crew AI status"""
    if request.method == 'GET':
        return get_crew_status(request)
    else:
        return Response(
            {"error": "Method not allowed"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )


@csrf_exempt
def crewai_history(request):
    """Legacy endpoint for Crew AI history"""
    if request.method == 'GET':
        return get_analysis_history(request)
    else:
        return Response(
            {"error": "Method not allowed"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )