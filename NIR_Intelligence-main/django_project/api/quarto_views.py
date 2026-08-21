# NIR_Mistral Quarto Report Views
# API endpoints for generating and accessing Quarto reports

import json
import os
from datetime import datetime
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from core.utils.quarto_renderer import quarto_renderer
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


@csrf_exempt
@require_http_methods(["POST"])
def generate_spectral_report(request):
    """
    Generate a Quarto report from spectral analysis data.
    
    Expects JSON data with spectral analysis results.
    Returns the URL to access the generated report.
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
        
        # Generate a unique filename
        sample_id = data.get('sample_id', 'unknown')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"spectral_report_{sample_id}_{timestamp}"
        
        # Render the report
        success, output_path, error = quarto_renderer.render_spectral_analysis_report(
            analysis_data=data,
            output_filename=output_filename
        )
        
        if success:
            # Create URL for accessing the report
            report_url = quarto_renderer.create_report_url(output_path)
            
            return JsonResponse({
                'success': True,
                'report_url': report_url,
                'output_path': output_path,
                'message': 'Report generated successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': error or 'Failed to generate report'
            }, status=500)
            
    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid JSON data: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error generating report: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def generate_metadata_report(request):
    """
    Generate a Quarto report from metadata analysis data.
    """
    try:
        data = json.loads(request.body)
        
        if not data:
            return JsonResponse({
                'success': False,
                'error': 'No data provided'
            }, status=400)
        
        # Generate a unique filename
        sample_id = data.get('sample_id', 'unknown')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"metadata_report_{sample_id}_{timestamp}"
        
        # Render the report
        success, output_path, error = quarto_renderer.render_metadata_report(
            metadata_data=data,
            output_filename=output_filename
        )
        
        if success:
            report_url = quarto_renderer.create_report_url(output_path)
            
            return JsonResponse({
                'success': True,
                'report_url': report_url,
                'output_path': output_path,
                'message': 'Metadata report generated successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': error or 'Failed to generate metadata report'
            }, status=500)
            
    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid JSON data: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error generating metadata report: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_report_templates(request):
    """
    Get list of available Quarto report templates.
    """
    try:
        templates = quarto_renderer.get_available_templates()
        return JsonResponse({
            'success': True,
            'templates': templates,
            'count': len(templates)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def check_quarto_status(request):
    """
    Check if Quarto is properly installed and configured.
    """
    try:
        installed, version = quarto_renderer.check_quarto_installation()
        return JsonResponse({
            'success': True,
            'installed': installed,
            'version': version,
            'quarto_path': quarto_renderer.quarto_path,
            'enabled': quarto_renderer.enabled,
            'reports_dir': str(quarto_renderer.reports_dir),
            'output_dir': str(quarto_renderer.output_dir)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def serve_report(request, report_name):
    """
    Serve a generated report file.
    """
    try:
        report_path = os.path.join(settings.QUARTO_OUTPUT_DIR, report_name)
        
        if not os.path.exists(report_path):
            return JsonResponse({
                'success': False,
                'error': 'Report not found'
            }, status=404)
        
        # Determine content type based on file extension
        content_type = 'text/html'
        if report_name.endswith('.pdf'):
            content_type = 'application/pdf'
        elif report_name.endswith('.docx'):
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        # Serve the file
        with open(report_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=content_type)
            response['Content-Disposition'] = f'inline; filename="{report_name}"'
            return response
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def generate_report_from_analysis(request, analysis_id):
    """
    Generate a Quarto report from a stored spectral analysis.
    """
    try:
        # In a real implementation, you would fetch the analysis data from the database
        # For now, we'll expect the data to be provided in the request body
        data = json.loads(request.body)
        
        if not data:
            return JsonResponse({
                'success': False,
                'error': 'No analysis data provided'
            }, status=400)
        
        # Generate report
        sample_id = data.get('sample_id', analysis_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"analysis_report_{sample_id}_{timestamp}"
        
        success, output_path, error = quarto_renderer.render_spectral_analysis_report(
            analysis_data=data,
            output_filename=output_filename
        )
        
        if success:
            report_url = quarto_renderer.create_report_url(output_path)
            
            return JsonResponse({
                'success': True,
                'report_url': report_url,
                'analysis_id': analysis_id,
                'output_path': output_path,
                'message': 'Report generated from analysis'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': error or 'Failed to generate report from analysis'
            }, status=500)
            
    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid JSON data: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error generating report from analysis: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def render_custom_report(request):
    """
    Render a custom Quarto report with provided template and data.
    """
    try:
        data = json.loads(request.body)
        
        template_name = data.get('template', 'spectral_analysis')
        output_filename = data.get('output_filename')
        report_data = data.get('data', {})
        output_format = data.get('format', 'html')
        
        if not template_name:
            return JsonResponse({
                'success': False,
                'error': 'Template name is required'
            }, status=400)
        
        success, output_path, error = quarto_renderer.render_report(
            template_name=template_name,
            output_filename=output_filename,
            data=report_data,
            format=output_format
        )
        
        if success:
            report_url = quarto_renderer.create_report_url(output_path)
            
            return JsonResponse({
                'success': True,
                'report_url': report_url,
                'output_path': output_path,
                'template': template_name,
                'format': output_format,
                'message': 'Custom report rendered successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': error or 'Failed to render custom report'
            }, status=500)
            
    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid JSON data: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error rendering custom report: {str(e)}'
        }, status=500)