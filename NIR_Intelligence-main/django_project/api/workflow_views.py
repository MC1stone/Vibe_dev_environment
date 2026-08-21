# NIR Intelligence Platform - Workflow Views
# Django API endpoints for workflow execution and management

import os
import json
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# Import workflow orchestrator
import sys
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from agents.workflow_orchestrator import WorkflowOrchestrator, WorkflowType, WorkflowStatus
    WORKFLOW_AVAILABLE = True
except ImportError as e:
    WORKFLOW_AVAILABLE = False
    logging.getLogger(__name__).error(f"Failed to import workflow orchestrator: {e}")

logger = logging.getLogger(__name__)

# Initialize workflow orchestrator
workflow_orchestrator = None

def get_workflow_orchestrator():
    """Get or initialize the workflow orchestrator"""
    global workflow_orchestrator
    if workflow_orchestrator is None and WORKFLOW_AVAILABLE:
        # Configure directories
        base_dir = getattr(settings, 'BASE_DIR', '/tmp/nir_workflows')
        input_dir = os.path.join(base_dir, 'uploads')
        output_dir = os.path.join(base_dir, 'output')
        temp_dir = os.path.join(base_dir, 'temp')
        report_dir = os.path.join(base_dir, 'reports')
        quarto_dir = os.path.join(base_dir, 'quarto')
        html_dir = os.path.join(base_dir, 'html')
        
        workflow_orchestrator = WorkflowOrchestrator(
            input_directory=input_dir,
            output_directory=output_dir,
            temp_directory=temp_dir,
            report_directory=report_dir,
            quarto_output_dir=quarto_dir,
            html_output_dir=html_dir
        )
    return workflow_orchestrator


@csrf_exempt
@require_http_methods(["POST"])
def start_workflow(request):
    """
    Start a new workflow execution.
    
    Expects JSON data with:
    - file_paths: List of file paths to process
    - workflow_type: Type of workflow (standard, comprehensive, quick, etc.)
    
    Returns workflow ID and status.
    """
    try:
        # Parse JSON data from request
        data = json.loads(request.body)
        
        # Validate required fields
        if not data:
            return JsonResponse({
                'success': False,
                'error': 'No data provided'
            }, status=400)
        
        file_paths = data.get('file_paths', [])
        workflow_type_str = data.get('workflow_type', 'standard_analysis')
        
        if not file_paths:
            return JsonResponse({
                'success': False,
                'error': 'No file paths provided'
            }, status=400)
        
        # Convert workflow type string to enum
        workflow_type_map = {
            'standard': WorkflowType.STANDARD_ANALYSIS,
            'standard_analysis': WorkflowType.STANDARD_ANALYSIS,
            'comprehensive': WorkflowType.COMPREHENSIVE_ANALYSIS,
            'comprehensive_analysis': WorkflowType.COMPREHENSIVE_ANALYSIS,
            'quick': WorkflowType.QUICK_ANALYSIS,
            'quick_analysis': WorkflowType.QUICK_ANALYSIS,
            'metadata_only': WorkflowType.METADATA_ONLY,
            'batch': WorkflowType.BATCH_PROCESSING,
            'batch_processing': WorkflowType.BATCH_PROCESSING
        }
        
        workflow_type = workflow_type_map.get(workflow_type_str.lower(), WorkflowType.STANDARD_ANALYSIS)
        
        # Get workflow orchestrator
        orchestrator = get_workflow_orchestrator()
        if not orchestrator:
            return JsonResponse({
                'success': False,
                'error': 'Workflow orchestrator not available'
            }, status=500)
        
        # Execute workflow
        logger.info(f"Starting workflow for files: {file_paths}")
        workflow_result = orchestrator.execute_workflow(file_paths, workflow_type)
        
        # Prepare response
        response_data = {
            'success': workflow_result.status == WorkflowStatus.COMPLETED,
            'workflow_id': workflow_result.workflow_id,
            'workflow_type': workflow_result.workflow_type.value,
            'status': workflow_result.status.value,
            'start_time': workflow_result.start_time,
            'end_time': workflow_result.end_time,
            'processing_time': workflow_result.processing_time,
            'total_samples': len(workflow_result.analysis_results),
            'successful_analyses': len([r for r in workflow_result.analysis_results if not r.errors]),
            'failed_analyses': len([r for r in workflow_result.analysis_results if r.errors]),
            'generated_reports': len(workflow_result.generated_reports),
            'quarto_files': workflow_result.quarto_files,
            'html_files': workflow_result.html_files,
            'errors': workflow_result.errors,
            'warnings': workflow_result.warnings,
            'sample_results': []
        }
        
        # Add sample results summary
        for analysis_result in workflow_result.analysis_results:
            sample_summary = {
                'sample_id': analysis_result.sample_id,
                'request_id': analysis_result.request_id,
                'overall_quality_score': analysis_result.overall_quality_score,
                'processing_time': analysis_result.processing_time,
                'spectral_quality': (analysis_result.spectral_analysis.quality_grade.value 
                                   if analysis_result.spectral_analysis else "N/A"),
                'metadata_quality': (analysis_result.metadata_quality.overall_quality_grade.value 
                                    if analysis_result.metadata_quality else "N/A"),
                'recommendations_count': len(analysis_result.recommendations),
                'warnings_count': len(analysis_result.warnings),
                'errors_count': len(analysis_result.errors),
                'reports_generated': len(analysis_result.generated_reports)
            }
            response_data['sample_results'].append(sample_summary)
        
        # Add report URLs if files are accessible
        if workflow_result.html_files:
            response_data['report_urls'] = []
            for html_file in workflow_result.html_files:
                try:
                    # Create URL for accessing the report
                    file_path = Path(html_file)
                    relative_path = file_path.relative_to(Path(settings.BASE_DIR) if hasattr(settings, 'BASE_DIR') else file_path.parent)
                    report_url = f"/reports/{relative_path}"
                    response_data['report_urls'].append({
                        'file': file_path.name,
                        'url': report_url,
                        'path': str(html_file)
                    })
                except Exception as e:
                    logger.error(f"Error creating report URL for {html_file}: {e}")
                    continue
        
        logger.info(f"Workflow {workflow_result.workflow_id} completed with status {workflow_result.status.value}")
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid JSON data: {str(e)}'
        }, status=400)
    except Exception as e:
        logger.error(f"Error starting workflow: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error starting workflow: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_workflow_status(request, workflow_id):
    """
    Get the status of a specific workflow.
    
    Args:
        workflow_id: The ID of the workflow to check
        
    Returns:
        Workflow status and results
    """
    try:
        orchestrator = get_workflow_orchestrator()
        if not orchestrator:
            return JsonResponse({
                'success': False,
                'error': 'Workflow orchestrator not available'
            }, status=500)
        
        workflow_result = orchestrator.get_workflow_status(workflow_id)
        
        if not workflow_result:
            return JsonResponse({
                'success': False,
                'error': f'Workflow {workflow_id} not found'
            }, status=404)
        
        # Prepare response
        response_data = {
            'success': True,
            'workflow_id': workflow_result.workflow_id,
            'workflow_type': workflow_result.workflow_type.value,
            'status': workflow_result.status.value,
            'start_time': workflow_result.start_time,
            'end_time': workflow_result.end_time,
            'processing_time': workflow_result.processing_time,
            'total_samples': len(workflow_result.analysis_results),
            'successful_analyses': len([r for r in workflow_result.analysis_results if not r.errors]),
            'failed_analyses': len([r for r in workflow_result.analysis_results if r.errors]),
            'generated_reports': len(workflow_result.generated_reports),
            'quarto_files': workflow_result.quarto_files,
            'html_files': workflow_result.html_files,
            'errors': workflow_result.errors,
            'warnings': workflow_result.warnings
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error getting workflow status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error getting workflow status: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_all_workflows(request):
    """
    Get a list of all workflows.
    
    Returns:
        List of all workflow summaries
    """
    try:
        orchestrator = get_workflow_orchestrator()
        if not orchestrator:
            return JsonResponse({
                'success': False,
                'error': 'Workflow orchestrator not available'
            }, status=500)
        
        workflows = orchestrator.get_all_workflows()
        
        # Prepare response
        workflow_summaries = []
        for workflow in workflows:
            summary = {
                'workflow_id': workflow.workflow_id,
                'workflow_type': workflow.workflow_type.value,
                'status': workflow.status.value,
                'start_time': workflow.start_time,
                'end_time': workflow.end_time,
                'processing_time': workflow.processing_time,
                'total_samples': len(workflow.analysis_results),
                'successful_analyses': len([r for r in workflow.analysis_results if not r.errors]),
                'generated_reports': len(workflow.generated_reports)
            }
            workflow_summaries.append(summary)
        
        return JsonResponse({
            'success': True,
            'workflows': workflow_summaries,
            'count': len(workflow_summaries)
        })
        
    except Exception as e:
        logger.error(f"Error getting all workflows: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error getting workflows: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def upload_and_analyze(request):
    """
    Upload files and automatically start analysis workflow.
    
    Expects multipart form data with files to upload.
    
    Returns workflow ID and analysis results.
    """
    try:
        if not request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No files uploaded'
            }, status=400)
        
        # Save uploaded files temporarily
        temp_dir = tempfile.mkdtemp()
        file_paths = []
        
        try:
            for filename, file in request.FILES.items():
                # Save file to temporary directory
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)
                file_paths.append(file_path)
                logger.info(f"Saved uploaded file: {file_path}")
            
            # Start workflow with uploaded files
            workflow_type_str = request.POST.get('workflow_type', 'standard_analysis')
            
            # Convert workflow type string to enum
            workflow_type_map = {
                'standard': WorkflowType.STANDARD_ANALYSIS,
                'standard_analysis': WorkflowType.STANDARD_ANALYSIS,
                'comprehensive': WorkflowType.COMPREHENSIVE_ANALYSIS,
                'comprehensive_analysis': WorkflowType.COMPREHENSIVE_ANALYSIS,
                'quick': WorkflowType.QUICK_ANALYSIS,
                'quick_analysis': WorkflowType.QUICK_ANALYSIS
            }
            
            workflow_type = workflow_type_map.get(workflow_type_str.lower(), WorkflowType.STANDARD_ANALYSIS)
            
            orchestrator = get_workflow_orchestrator()
            if not orchestrator:
                return JsonResponse({
                    'success': False,
                    'error': 'Workflow orchestrator not available'
                }, status=500)
            
            # Execute workflow
            workflow_result = orchestrator.execute_workflow(file_paths, workflow_type)
            
            # Prepare response
            response_data = {
                'success': workflow_result.status == WorkflowStatus.COMPLETED,
                'workflow_id': workflow_result.workflow_id,
                'workflow_type': workflow_result.workflow_type.value,
                'status': workflow_result.status.value,
                'start_time': workflow_result.start_time,
                'end_time': workflow_result.end_time,
                'processing_time': workflow_result.processing_time,
                'total_samples': len(workflow_result.analysis_results),
                'successful_analyses': len([r for r in workflow_result.analysis_results if not r.errors]),
                'generated_reports': len(workflow_result.generated_reports),
                'quarto_files': workflow_result.quarto_files,
                'html_files': workflow_result.html_files,
                'errors': workflow_result.errors,
                'warnings': workflow_result.warnings,
                'uploaded_files': [os.path.basename(f) for f in file_paths]
            }
            
            # Add report URLs
            if workflow_result.html_files:
                response_data['report_urls'] = []
                for html_file in workflow_result.html_files:
                    try:
                        file_path = Path(html_file)
                        report_url = f"/reports/{file_path.name}"
                        response_data['report_urls'].append({
                            'file': file_path.name,
                            'url': report_url
                        })
                    except Exception:
                        continue
            
            return JsonResponse(response_data)
            
        finally:
            # Clean up temporary files
            import shutil
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory: {e}")
        
    except Exception as e:
        logger.error(f"Error uploading and analyzing files: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error uploading and analyzing files: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_report(request, report_filename):
    """
    Serve a generated report file.
    
    Args:
        report_filename: Name of the report file to serve
        
    Returns:
        The report file as a downloadable response
    """
    try:
        # Try to find the report in various locations
        possible_locations = [
            os.path.join(settings.BASE_DIR, 'html', report_filename) if hasattr(settings, 'BASE_DIR') else None,
            os.path.join(settings.BASE_DIR, 'reports', report_filename) if hasattr(settings, 'BASE_DIR') else None,
            os.path.join(settings.BASE_DIR, 'output', 'html', report_filename) if hasattr(settings, 'BASE_DIR') else None,
            os.path.join('output', 'html', report_filename),
            os.path.join('reports', report_filename),
            os.path.join('html', report_filename)
        ]
        
        report_path = None
        for location in possible_locations:
            if location and os.path.exists(location):
                report_path = location
                break
        
        if not report_path:
            return JsonResponse({
                'success': False,
                'error': f'Report file not found: {report_filename}'
            }, status=404)
        
        # Serve the file
        with open(report_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type='text/html')
            response['Content-Disposition'] = f'inline; filename="{report_filename}"'
            return response
        
    except Exception as e:
        logger.error(f"Error serving report {report_filename}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error serving report: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def list_reports(request):
    """
    List all available reports.
    
    Returns:
        List of available report files
    """
    try:
        # Look for reports in various locations
        report_dirs = [
            os.path.join(settings.BASE_DIR, 'html') if hasattr(settings, 'BASE_DIR') else None,
            os.path.join(settings.BASE_DIR, 'reports') if hasattr(settings, 'BASE_DIR') else None,
            os.path.join(settings.BASE_DIR, 'output', 'html') if hasattr(settings, 'BASE_DIR') else None,
            'output/html',
            'reports',
            'html'
        ]
        
        all_reports = []
        for report_dir in report_dirs:
            if report_dir and os.path.exists(report_dir):
                for filename in os.listdir(report_dir):
                    if filename.endswith(('.html', '.pdf', '.docx')):
                        file_path = os.path.join(report_dir, filename)
                        file_info = {
                            'filename': filename,
                            'path': file_path,
                            'url': f"/reports/{filename}",
                            'size': os.path.getsize(file_path),
                            'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                        }
                        all_reports.append(file_info)
        
        return JsonResponse({
            'success': True,
            'reports': all_reports,
            'count': len(all_reports)
        })
        
    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error listing reports: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def cleanup_workflow(request, workflow_id):
    """
    Clean up files associated with a workflow.
    
    Args:
        workflow_id: The ID of the workflow to clean up
        
    Returns:
        Status of cleanup operation
    """
    try:
        keep_reports = request.POST.get('keep_reports', 'true').lower() == 'true'
        
        orchestrator = get_workflow_orchestrator()
        if not orchestrator:
            return JsonResponse({
                'success': False,
                'error': 'Workflow orchestrator not available'
            }, status=500)
        
        success = orchestrator.cleanup_workflow_files(workflow_id, keep_reports)
        
        return JsonResponse({
            'success': success,
            'workflow_id': workflow_id,
            'keep_reports': keep_reports,
            'message': f'Workflow {workflow_id} cleanup {"completed" if success else "failed"}'
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up workflow {workflow_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error cleaning up workflow: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_workflow_summary(request, workflow_id):
    """
    Get a summary of workflow results.
    
    Args:
        workflow_id: The ID of the workflow
        
    Returns:
        Summary data for the workflow
    """
    try:
        orchestrator = get_workflow_orchestrator()
        if not orchestrator:
            return JsonResponse({
                'success': False,
                'error': 'Workflow orchestrator not available'
            }, status=500)
        
        workflow_result = orchestrator.get_workflow_status(workflow_id)
        
        if not workflow_result:
            return JsonResponse({
                'success': False,
                'error': f'Workflow {workflow_id} not found'
            }, status=404)
        
        # Prepare comprehensive summary
        summary_data = {
            'workflow_id': workflow_result.workflow_id,
            'workflow_type': workflow_result.workflow_type.value,
            'status': workflow_result.status.value,
            'start_time': workflow_result.start_time,
            'end_time': workflow_result.end_time,
            'processing_time': workflow_result.processing_time,
            'input_files': workflow_result.input_files,
            'total_samples': len(workflow_result.analysis_results),
            'successful_analyses': len([r for r in workflow_result.analysis_results if not r.errors]),
            'failed_analyses': len([r for r in workflow_result.analysis_results if r.errors]),
            'generated_reports': len(workflow_result.generated_reports),
            'quarto_files': workflow_result.quarto_files,
            'html_files': workflow_result.html_files,
            'errors': workflow_result.errors,
            'warnings': workflow_result.warnings,
            'sample_results': []
        }
        
        # Add detailed sample results
        for analysis_result in workflow_result.analysis_results:
            sample_summary = {
                'sample_id': analysis_result.sample_id,
                'request_id': analysis_result.request_id,
                'overall_quality_score': analysis_result.overall_quality_score,
                'processing_time': analysis_result.processing_time,
                'spectral_quality': (analysis_result.spectral_analysis.quality_grade.value 
                                   if analysis_result.spectral_analysis else "N/A"),
                'metadata_quality': (analysis_result.metadata_quality.overall_quality_grade.value 
                                    if analysis_result.metadata_quality else "N/A"),
                'recommendations': analysis_result.recommendations,
                'warnings': analysis_result.warnings,
                'errors': analysis_result.errors,
                'reports_generated': len(analysis_result.generated_reports)
            }
            summary_data['sample_results'].append(sample_summary)
        
        return JsonResponse(summary_data)
        
    except Exception as e:
        logger.error(f"Error getting workflow summary: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error getting workflow summary: {str(e)}'
        }, status=500)