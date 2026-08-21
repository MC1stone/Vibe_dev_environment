# NIR Intelligence Platform - Workflow Display Views
# Django views for displaying workflow results in the web interface

import os
import json
import logging
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.urls import reverse

from .workflow_views import get_workflow_orchestrator

logger = logging.getLogger(__name__)


def workflow_results_view(request, workflow_id):
    """
    Display the results of a specific workflow.
    
    Args:
        request: Django request object
        workflow_id: The ID of the workflow to display
        
    Returns:
        Rendered template with workflow results
    """
    try:
        orchestrator = get_workflow_orchestrator()
        if not orchestrator:
            return render(request, 'error.html', {
                'error_title': 'Workflow Orchestrator Not Available',
                'error_message': 'The workflow orchestrator is not available. Please try again later.'
            }, status=500)
        
        workflow_result = orchestrator.get_workflow_status(workflow_id)
        
        if not workflow_result:
            return render(request, 'error.html', {
                'error_title': 'Workflow Not Found',
                'error_message': f'Workflow with ID {workflow_id} was not found.'
            }, status=404)
        
        # Prepare data for template
        workflow_data = {
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
            'input_files': workflow_result.input_files,
            'errors': workflow_result.errors,
            'warnings': workflow_result.warnings,
            'sample_results': [],
            'report_urls': []
        }
        
        # Add sample results
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
                'recommendations': analysis_result.recommendations,
                'warnings_count': len(analysis_result.warnings),
                'warnings': analysis_result.warnings,
                'errors_count': len(analysis_result.errors),
                'errors': analysis_result.errors,
                'reports_generated': len(analysis_result.generated_reports)
            }
            workflow_data['sample_results'].append(sample_summary)
        
        # Add report URLs
        if workflow_result.html_files:
            for html_file in workflow_result.html_files:
                try:
                    file_path = Path(html_file)
                    # Create URL for accessing the report
                    report_url = f"/reports/{file_path.name}"
                    workflow_data['report_urls'].append({
                        'file': file_path.name,
                        'url': report_url,
                        'path': str(html_file)
                    })
                except Exception as e:
                    logger.error(f"Error creating report URL for {html_file}: {e}")
                    continue
        
        # Render the template
        return render(request, 'workflow_results.html', {
            'workflow': workflow_data,
            'page_title': f'Workflow Results - {workflow_id}',
            'page_description': f'Results for workflow {workflow_id}'
        })
        
    except Exception as e:
        logger.error(f"Error displaying workflow results: {str(e)}", exc_info=True)
        return render(request, 'error.html', {
            'error_title': 'Error Displaying Workflow Results',
            'error_message': f'An error occurred while displaying workflow results: {str(e)}'
        }, status=500)


def workflow_list_view(request):
    """
    Display a list of all workflows.
    
    Args:
        request: Django request object
        
    Returns:
        Rendered template with list of workflows
    """
    try:
        orchestrator = get_workflow_orchestrator()
        if not orchestrator:
            return render(request, 'error.html', {
                'error_title': 'Workflow Orchestrator Not Available',
                'error_message': 'The workflow orchestrator is not available. Please try again later.'
            }, status=500)
        
        workflows = orchestrator.get_all_workflows()
        
        # Prepare workflow summaries
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
                'failed_analyses': len([r for r in workflow.analysis_results if r.errors]),
                'generated_reports': len(workflow.generated_reports),
                'quarto_files_count': len(workflow.quarto_files),
                'html_files_count': len(workflow.html_files),
                'errors_count': len(workflow.errors),
                'warnings_count': len(workflow.warnings)
            }
            workflow_summaries.append(summary)
        
        # Sort workflows by start time (newest first)
        workflow_summaries.sort(key=lambda x: x['start_time'], reverse=True)
        
        return render(request, 'workflow_list.html', {
            'workflows': workflow_summaries,
            'page_title': 'All Workflows',
            'page_description': 'List of all executed workflows'
        })
        
    except Exception as e:
        logger.error(f"Error displaying workflow list: {str(e)}", exc_info=True)
        return render(request, 'error.html', {
            'error_title': 'Error Displaying Workflow List',
            'error_message': f'An error occurred while displaying workflow list: {str(e)}'
        }, status=500)


def workflow_detail_view(request, workflow_id):
    """
    Display detailed information about a specific workflow.
    
    Args:
        request: Django request object
        workflow_id: The ID of the workflow
        
    Returns:
        Rendered template with workflow details
    """
    try:
        orchestrator = get_workflow_orchestrator()
        if not orchestrator:
            return render(request, 'error.html', {
                'error_title': 'Workflow Orchestrator Not Available',
                'error_message': 'The workflow orchestrator is not available. Please try again later.'
            }, status=500)
        
        workflow_result = orchestrator.get_workflow_status(workflow_id)
        
        if not workflow_result:
            return render(request, 'error.html', {
                'error_title': 'Workflow Not Found',
                'error_message': f'Workflow with ID {workflow_id} was not found.'
            }, status=404)
        
        # Prepare detailed workflow data
        workflow_data = {
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
            sample_data = {
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
                'reports_generated': len(analysis_result.generated_reports),
                'spectral_analysis': analysis_result.spectral_analysis.__dict__ if analysis_result.spectral_analysis else None,
                'metadata_quality': analysis_result.metadata_quality.__dict__ if analysis_result.metadata_quality else None,
                'calibration_results': analysis_result.calibration_results or {}
            }
            workflow_data['sample_results'].append(sample_data)
        
        return render(request, 'workflow_detail.html', {
            'workflow': workflow_data,
            'page_title': f'Workflow Details - {workflow_id}',
            'page_description': f'Detailed information for workflow {workflow_id}'
        })
        
    except Exception as e:
        logger.error(f"Error displaying workflow details: {str(e)}", exc_info=True)
        return render(request, 'error.html', {
            'error_title': 'Error Displaying Workflow Details',
            'error_message': f'An error occurred while displaying workflow details: {str(e)}'
        }, status=500)


def upload_view(request):
    """
    Display the file upload form for starting new workflows.
    
    Args:
        request: Django request object
        
    Returns:
        Rendered template with upload form
    """
    try:
        return render(request, 'upload_files.html', {
            'page_title': 'Upload Files for Analysis',
            'page_description': 'Upload spectral data files to start a new analysis workflow'
        })
        
    except Exception as e:
        logger.error(f"Error displaying upload view: {str(e)}", exc_info=True)
        return render(request, 'error.html', {
            'error_title': 'Error Displaying Upload Form',
            'error_message': f'An error occurred while displaying upload form: {str(e)}'
        }, status=500)


def dashboard_view(request):
    """
    Display the main dashboard with workflow overview.
    
    Args:
        request: Django request object
        
    Returns:
        Rendered template with dashboard
    """
    try:
        orchestrator = get_workflow_orchestrator()
        
        # Get recent workflows
        recent_workflows = []
        if orchestrator:
            all_workflows = orchestrator.get_all_workflows()
            # Sort by start time and get last 5
            all_workflows.sort(key=lambda x: x.start_time, reverse=True)
            recent_workflows = all_workflows[:5]
        
        # Prepare workflow summaries
        workflow_summaries = []
        for workflow in recent_workflows:
            summary = {
                'workflow_id': workflow.workflow_id,
                'workflow_type': workflow.workflow_type.value,
                'status': workflow.status.value,
                'start_time': workflow.start_time,
                'processing_time': workflow.processing_time,
                'total_samples': len(workflow.analysis_results),
                'successful_analyses': len([r for r in workflow.analysis_results if not r.errors]),
                'generated_reports': len(workflow.generated_reports)
            }
            workflow_summaries.append(summary)
        
        # Get system statistics
        system_stats = {
            'total_workflows': len(recent_workflows),
            'recent_success_rate': 0,
            'total_reports': 0,
            'system_status': 'operational'
        }
        
        if recent_workflows:
            total_samples = sum(len(w.analysis_results) for w in recent_workflows)
            successful_samples = sum(len([r for r in w.analysis_results if not r.errors]) for w in recent_workflows)
            system_stats['recent_success_rate'] = round((successful_samples / total_samples * 100) if total_samples > 0 else 0, 1)
            system_stats['total_reports'] = sum(len(w.generated_reports) for w in recent_workflows)
        
        return render(request, 'dashboard.html', {
            'recent_workflows': workflow_summaries,
            'system_stats': system_stats,
            'page_title': 'NIR Intelligence Dashboard',
            'page_description': 'Overview of recent workflows and system status'
        })
        
    except Exception as e:
        logger.error(f"Error displaying dashboard: {str(e)}", exc_info=True)
        return render(request, 'error.html', {
            'error_title': 'Error Displaying Dashboard',
            'error_message': f'An error occurred while displaying dashboard: {str(e)}'
        }, status=500)