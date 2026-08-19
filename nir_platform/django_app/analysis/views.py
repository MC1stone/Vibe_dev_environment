"""
Views for the Analysis app in NIR Intelligence Platform.
"""

import os
import json
import logging
import uuid
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, FileResponse
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import SpectralData, AnalysisProject, Report, ChatSession, SystemLog
from .forms import UploadFileForm, AnalysisForm, ChatForm
from agents.spectral_analysis_agent import SpectralAnalysisAgent
from agents.metadata_quality_agent import MetadataQualityAgent
from agents.calibration_agent import CalibrationAgent
from agents.reporting_agent import ReportingAgent
from agents.quality_assurance_agent import QualityAssuranceAgent

# Configure logging
logger = logging.getLogger(__name__)


# Initialize agents (singleton instances)
spectral_agent = SpectralAnalysisAgent()
metadata_agent = MetadataQualityAgent()
calibration_agent = CalibrationAgent()
reporting_agent = ReportingAgent()
qa_agent = QualityAssuranceAgent()


def home(request):
    """Home page view."""
    recent_analyses = SpectralData.objects.filter(user=request.user if request.user.is_authenticated else None).order_by('-upload_date')[:5]
    
    context = {
        'page_title': 'NIR Intelligence Platform',
        'recent_analyses': recent_analyses,
        'app_description': 'Open Science NIR Spectral Analysis System',
        'features': [
            {'title': 'Spectral Analysis', 'description': 'Analyze NIR spectra from any spectrometer'},
            {'title': 'Metadata Quality', 'description': 'Evaluate metadata against international standards'},
            {'title': 'Calibration', 'description': 'Generate and apply spectrometer calibration'},
            {'title': 'Reporting', 'description': 'Generate comprehensive Quarto reports'},
            {'title': 'Federated Learning', 'description': 'Share data with the federated learning network'},
        ]
    }
    
    return render(request, 'analysis/home.html', context)


def upload_file(request):
    """File upload view."""
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Save uploaded file
                uploaded_file = request.FILES['file']
                
                # Create unique filename
                file_ext = os.path.splitext(uploaded_file.name)[1]
                unique_id = uuid.uuid4().hex
                filename = f"{unique_id}{file_ext}"
                file_path = os.path.join(settings.UPLOAD_DIR, filename)
                
                # Save file
                with open(file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                # Create SpectralData record
                spectral_data = SpectralData(
                    user=request.user if request.user.is_authenticated else None,
                    original_filename=uploaded_file.name,
                    file_path=file_path,
                    file_type=file_ext.lower(),
                    metadata=form.cleaned_data.get('metadata', {}),
                    spectrometer_type=form.cleaned_data.get('spectrometer_type', None)
                )
                spectral_data.save()
                
                # Log the upload
                SystemLog.objects.create(
                    level='INFO',
                    message=f'File uploaded: {uploaded_file.name}',
                    module='analysis.views',
                    function='upload_file',
                    context={'file_id': str(spectral_data.id), 'user': str(request.user)}
                )
                
                messages.success(request, f'File "{uploaded_file.name}" uploaded successfully!')
                return redirect('analysis_detail', analysis_id=spectral_data.id)
                
            except Exception as e:
                logger.error(f'Error uploading file: {e}')
                messages.error(request, f'Error uploading file: {str(e)}')
        else:
            messages.error(request, 'Invalid form data')
    else:
        form = UploadFileForm()
    
    context = {
        'page_title': 'Upload Spectral Data',
        'form': form,
        'allowed_extensions': settings.NIR_PLATFORM['allowed_extensions'],
        'max_upload_size': settings.NIR_PLATFORM['max_upload_size'] // (1024 * 1024)  # MB
    }
    
    return render(request, 'analysis/upload.html', context)


async def analyze_spectral_data(spectral_data: SpectralData):
    """Analyze spectral data using agents."""
    try:
        # Load spectral data
        import asyncio
        
        # Convert to dict for agent
        data_dict = {
            'wavelengths': spectral_data.wavelengths,
            'intensities': spectral_data.intensities,
            'metadata': spectral_data.metadata,
            'spectrometer_type': spectral_data.spectrometer_type,
            'file_path': spectral_data.file_path
        }
        
        # Run spectral analysis
        spectral_result = await spectral_agent.analyze_spectral_data(data=data_dict)
        
        # Run metadata quality assessment
        metadata_result = await metadata_agent.evaluate_metadata_quality(
            spectral_data.metadata or {}
        )
        
        # Run calibration
        calibration_result = await calibration_agent.generate_calibration(data_dict)
        
        # Run QA check
        qa_result = await qa_agent.perform_qa_check(
            spectral_result.to_dict(),
            metadata_result.to_dict(),
            calibration_result.to_dict()
        )
        
        # Generate report
        report = await reporting_agent.generate_spectral_analysis_report(
            spectral_result.to_dict(),
            metadata_result.to_dict(),
            calibration_result.to_dict()
        )
        
        return {
            'spectral_result': spectral_result.to_dict(),
            'metadata_result': metadata_result.to_dict(),
            'calibration_result': calibration_result.to_dict(),
            'qa_result': qa_result.to_dict(),
            'report': report.to_dict()
        }
        
    except Exception as e:
        logger.error(f'Error analyzing spectral data: {e}')
        raise


def analysis_detail(request, analysis_id):
    """Analysis detail view."""
    spectral_data = get_object_or_404(SpectralData, pk=analysis_id)
    
    # Check if analysis has been performed
    if not spectral_data.is_processed:
        # Perform analysis
        try:
            import asyncio
            
            async def perform_analysis():
                return await analyze_spectral_data(spectral_data)
            
            results = asyncio.run(perform_analysis())
            
            # Save results
            spectral_data.analysis_results = results.get('spectral_result', {})
            spectral_data.calibration_results = results.get('calibration_result', {})
            spectral_data.metadata_quality_results = results.get('metadata_result', {})
            spectral_data.data_quality_score = results.get('spectral_result', {}).get('quality_score', 0)
            spectral_data.metadata_quality_score = results.get('metadata_result', {}).get('overall_score', 0)
            spectral_data.calibration_quality_score = results.get('calibration_result', {}).get('calibration_quality', {}).get('overall_quality', 0)
            spectral_data.overall_quality_score = (
                spectral_data.data_quality_score * 0.4 +
                spectral_data.metadata_quality_score * 0.3 +
                spectral_data.calibration_quality_score * 0.3
            )
            spectral_data.is_processed = True
            spectral_data.processing_date = datetime.now()
            spectral_data.save()
            
            # Generate and save report
            report_content = results.get('report', {})
            report = Report(
                spectral_data=spectral_data,
                report_type='spectral_analysis',
                title=f"Analysis Report - {spectral_data.original_filename}",
                file_path=os.path.join(settings.REPORT_DIR, f"{spectral_data.id}.html"),
                quarto_content=json.dumps(report_content, indent=2),
                python_source=json.dumps(report_content.get('python_source', []), indent=2),
                is_generated=True,
                generation_date=datetime.now()
            )
            report.save()
            
            # Log the analysis
            SystemLog.objects.create(
                level='INFO',
                message=f'Analysis completed for {spectral_data.original_filename}',
                module='analysis.views',
                function='analysis_detail',
                context={'analysis_id': str(spectral_data.id)}
            )
            
            messages.success(request, 'Analysis completed successfully!')
            
        except Exception as e:
            logger.error(f'Error performing analysis: {e}')
            messages.error(request, f'Error performing analysis: {str(e)}')
            spectral_data.is_processed = False
            spectral_data.save()
    
    # Get analysis results
    analysis_results = spectral_data.analysis_results
    calibration_results = spectral_data.calibration_results
    metadata_quality = spectral_data.metadata_quality_results
    
    # Get report
    report = Report.objects.filter(spectral_data=spectral_data).first()
    
    context = {
        'page_title': f'Analysis: {spectral_data.original_filename}',
        'spectral_data': spectral_data,
        'analysis_results': analysis_results,
        'calibration_results': calibration_results,
        'metadata_quality': metadata_quality,
        'report': report,
        'quality_grade': spectral_data.get_quality_grade(),
        'is_owner': request.user == spectral_data.user or not spectral_data.user
    }
    
    return render(request, 'analysis/detail.html', context)


def analysis_report(request, analysis_id):
    """Analysis report view."""
    spectral_data = get_object_or_404(SpectralData, pk=analysis_id)
    report = get_object_or_404(Report, spectral_data=spectral_data)
    
    context = {
        'page_title': f'Report: {report.title}',
        'spectral_data': spectral_data,
        'report': report
    }
    
    return render(request, 'analysis/report.html', context)


def download_analysis(request, analysis_id):
    """Download analysis results."""
    spectral_data = get_object_or_404(SpectralData, pk=analysis_id)
    
    # Create download package
    import zipfile
    import io
    
    # Create in-memory zip file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add original file
        if os.path.exists(spectral_data.file_path):
            zip_file.write(spectral_data.file_path, 
                          os.path.basename(spectral_data.original_filename))
        
        # Add processed data
        processed_data = {
            'wavelengths': spectral_data.analysis_results.get('processed_data', {}).get('wavelengths', []),
            'intensities': spectral_data.analysis_results.get('processed_data', {}).get('intensities', []),
            'metadata': spectral_data.metadata
        }
        zip_file.writestr('processed_data.json', json.dumps(processed_data, indent=2))
        
        # Add analysis results
        zip_file.writestr('analysis_results.json', 
                         json.dumps(spectral_data.analysis_results, indent=2))
        
        # Add calibration results
        zip_file.writestr('calibration_results.json', 
                         json.dumps(spectral_data.calibration_results, indent=2))
        
        # Add metadata quality results
        zip_file.writestr('metadata_quality.json', 
                         json.dumps(spectral_data.metadata_quality_results, indent=2))
        
        # Add report
        report = Report.objects.filter(spectral_data=spectral_data).first()
        if report:
            zip_file.writestr('report.html', report.html_content or '')
            zip_file.writestr('report.qmd', report.quarto_content)
            zip_file.writestr('python_source.py', report.python_source or '')
    
    # Return zip file
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="analysis_{spectral_data.id}.zip"'
    return response


def chat_interface(request, analysis_id=None):
    """Chat interface with AI agents."""
    spectral_data = None
    if analysis_id:
        spectral_data = get_object_or_404(SpectralData, pk=analysis_id)
    
    # Get or create chat session
    session_id = request.session.get('chat_session_id')
    chat_session = None
    
    if session_id:
        try:
            chat_session = ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            pass
    
    if not chat_session:
        chat_session = ChatSession(
            user=request.user if request.user.is_authenticated else None,
            spectral_data=spectral_data,
            session_name=f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            agent_type='analysis'
        )
        chat_session.save()
        request.session['chat_session_id'] = str(chat_session.id)
    
    if request.method == 'POST':
        form = ChatForm(request.POST)
        if form.is_valid():
            message = form.cleaned_data['message']
            
            # Add user message
            chat_session.messages.append({
                'sender': 'user',
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
            chat_session.save()
            
            # Generate AI response
            try:
                import asyncio
                
                async def get_ai_response():
                    # Use Ollama via MCP server or direct API
                    # For now, return a mock response
                    return "I'm the NIR Intelligence AI assistant. I can help you analyze your spectral data, interpret results, and provide recommendations for improving your measurements."
                
                ai_response = asyncio.run(get_ai_response())
                
                # Add AI response
                chat_session.messages.append({
                    'sender': 'ai',
                    'message': ai_response,
                    'timestamp': datetime.now().isoformat()
                })
                chat_session.save()
                
            except Exception as e:
                logger.error(f'Error getting AI response: {e}')
                chat_session.messages.append({
                    'sender': 'system',
                    'message': f'Error: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
                chat_session.save()
            
            return redirect('chat_interface', analysis_id=analysis_id)
    else:
        form = ChatForm()
    
    context = {
        'page_title': 'Chat with AI Agents',
        'chat_session': chat_session,
        'form': form,
        'spectral_data': spectral_data
    }
    
    return render(request, 'analysis/chat.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def api_analyze(request):
    """API endpoint for spectral analysis."""
    try:
        data = json.loads(request.body)
        
        # Validate data
        if 'wavelengths' not in data or 'intensities' not in data:
            return JsonResponse({'error': 'Missing wavelengths or intensities'}, status=400)
        
        # Perform analysis
        import asyncio
        
        async def perform_analysis():
            spectral_result = await spectral_agent.analyze_spectral_data(data=data)
            metadata_result = await metadata_agent.evaluate_metadata_quality(
                data.get('metadata', {})
            )
            calibration_result = await calibration_agent.generate_calibration(data)
            
            return {
                'spectral': spectral_result.to_dict(),
                'metadata': metadata_result.to_dict(),
                'calibration': calibration_result.to_dict()
            }
        
        results = asyncio.run(perform_analysis())
        
        return JsonResponse({'status': 'success', 'results': results})
        
    except Exception as e:
        logger.error(f'API analysis error: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_chat(request):
    """API endpoint for chat with AI agents."""
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # For now, return mock response
        # In production, this would call the MCP server or Ollama directly
        response = {
            'message': f"I received your message: {message[:50]}...",
            'sender': 'ai',
            'timestamp': datetime.now().isoformat()
        }
        
        return JsonResponse({'status': 'success', 'response': response})
        
    except Exception as e:
        logger.error(f'API chat error: {e}')
        return JsonResponse({'error': str(e)}, status=500)


def about(request):
    """About page view."""
    context = {
        'page_title': 'About NIR Intelligence Platform',
        'app_name': settings.NIR_PLATFORM['app_name'],
        'version': settings.NIR_PLATFORM['version'],
        'description': settings.NIR_PLATFORM['description']
    }
    
    return render(request, 'analysis/about.html', context)


def documentation(request):
    """Documentation page view."""
    context = {
        'page_title': 'Documentation',
        'docs': [
            {
                'title': 'Getting Started',
                'content': 'Learn how to use the NIR Intelligence Platform for spectral analysis.',
                'sections': [
                    'Installation',
                    'Uploading Data',
                    'Running Analysis',
                    'Viewing Reports'
                ]
            },
            {
                'title': 'User Guide',
                'content': 'Detailed guide on all platform features and capabilities.',
                'sections': [
                    'Spectral Analysis',
                    'Metadata Quality',
                    'Calibration',
                    'Reporting',
                    'Federated Learning'
                ]
            },
            {
                'title': 'API Reference',
                'content': 'Technical documentation for developers.',
                'sections': [
                    'REST API',
                    'WebSocket API',
                    'Integration Examples'
                ]
            },
            {
                'title': 'DIY Spectrometer Guide',
                'content': 'Build your own NIR spectrometer for Open Science.',
                'sections': [
                    'Components',
                    'Assembly Instructions',
                    'Calibration',
                    'Usage Tips'
                ]
            }
        ]
    }
    
    return render(request, 'analysis/docs.html', context)
