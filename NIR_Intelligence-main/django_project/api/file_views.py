"""
Views for Generic File Management API
Handles upload, processing, and analysis of any file type
"""

import os
import sys
import json
import logging
import math
import tempfile
import hashlib
import mimetypes
from pathlib import Path
from datetime import datetime
from django.http import Http404, JsonResponse, HttpResponse, FileResponse
from django.shortcuts import redirect, render
from django.views.generic import TemplateView
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, JSONParser
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.models import GenericFile, User
from .serializers import GenericFileSerializer, GenericFileUploadSerializer

# Add framework to path
framework_path = settings.NIR_FRAMEWORK_PATH
if framework_path not in sys.path:
    sys.path.insert(0, framework_path)

logger = logging.getLogger(__name__)


class FileListView(APIView):
    """List all files for the current user"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Get all files for the current user
            files = GenericFile.objects.filter(user=request.user).order_by('-created_at')
            
            # Prepare statistics
            statistics = {
                'total': files.count(),
                'valid': files.filter(is_valid=True).count(),
                'invalid': files.filter(is_valid=False).count(),
                'total_size': sum(file.file_size for file in files if file.file_size),
                'by_category': {}
            }
            
            # Count by category
            for category in GenericFile.FILE_CATEGORIES:
                category_name = category[0]
                count = files.filter(file_category=category_name).count()
                if count > 0:
                    statistics['by_category'][category_name] = count
            
            # Serialize files
            serializer = GenericFileSerializer(files, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'files': serializer.data,
                'statistics': statistics,
                'message': f'Retrieved {files.count()} files'
            })
            
        except Exception as e:
            logger.error(f'Error listing files: {str(e)}', exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error retrieving files'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileDetailView(APIView):
    """Get details for a specific file"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, file_id):
        try:
            file = GenericFile.objects.get(id=file_id, user=request.user)
            serializer = GenericFileSerializer(file, context={'request': request})
            
            return Response({
                'success': True,
                'file': serializer.data,
                'message': 'File details retrieved'
            })
            
        except GenericFile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'File not found',
                'message': 'The requested file does not exist or you do not have permission to access it'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f'Error getting file details: {str(e)}', exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error retrieving file details'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileUploadView(APIView):
    """Upload files for processing"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]
    
    def post(self, request):
        try:
            # Get uploaded files
            uploaded_files = request.FILES.getlist('files')
            
            if not uploaded_files:
                return Response({
                    'success': False,
                    'error': 'No files provided',
                    'message': 'Please select at least one file to upload'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate file sizes (500MB max per file)
            MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
            for uploaded_file in uploaded_files:
                if uploaded_file.size > MAX_FILE_SIZE:
                    return Response({
                        'success': False,
                        'error': f'File {uploaded_file.name} exceeds maximum size of 500MB',
                        'message': 'File size limit exceeded'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get metadata from request
            file_name = request.data.get('file_name', '')
            file_category = request.data.get('file_category', 'auto')
            description = request.data.get('description', '')
            tags = request.data.get('tags', '')
            metadata_author = request.data.get('metadata_author', '')
            metadata_date = request.data.get('metadata_date', '')
            metadata_source = request.data.get('metadata_source', '')
            auto_analyze = request.data.get('auto_analyze', 'true').lower() == 'true'
            
            # Convert tags to list
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []
            
            # Process each file
            uploaded_file_ids = []
            errors = []
            
            for uploaded_file in uploaded_files:
                try:
                    # Create file record
                    file_record = GenericFile(
                        user=request.user,
                        name=file_name or uploaded_file.name,
                        original_filename=uploaded_file.name,
                        description=description,
                        file_size=uploaded_file.size,
                        file_extension=os.path.splitext(uploaded_file.name)[1].lower(),
                        mime_type=uploaded_file.content_type or mimetypes.guess_type(uploaded_file.name)[0] or '',
                        file_category=file_category if file_category != 'auto' else 'unknown',
                        tags=tags_list,
                        custom_metadata={
                            'author': metadata_author,
                            'date': metadata_date,
                            'source': metadata_source
                        } if any([metadata_author, metadata_date, metadata_source]) else {}
                    )
                    
                    # Save the file
                    file_record.file.save(uploaded_file.name, uploaded_file)
                    
                    # Calculate hashes
                    file_path = file_record.get_file_path()
                    if file_path and os.path.exists(file_path):
                        file_record.md5_hash = self._calculate_md5(file_path)
                        file_record.sha1_hash = self._calculate_sha1(file_path)
                    
                    # Save the record
                    file_record.save()
                    
                    # Process the file if auto_analyze is True
                    if auto_analyze:
                        self._process_file(file_record)
                    
                    uploaded_file_ids.append(str(file_record.id))
                    
                except Exception as e:
                    logger.error(f'Error processing file {uploaded_file.name}: {str(e)}', exc_info=True)
                    errors.append(f'File {uploaded_file.name}: {str(e)}')
            
            # Return response
            if uploaded_file_ids:
                return Response({
                    'success': True,
                    'uploaded_files': uploaded_file_ids,
                    'count': len(uploaded_file_ids),
                    'errors': errors,
                    'message': f'Successfully uploaded {len(uploaded_file_ids)} file(s)'
                })
            else:
                return Response({
                    'success': False,
                    'errors': errors,
                    'message': 'Failed to upload any files'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.error(f'Error uploading files: {str(e)}', exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error uploading files'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _calculate_md5(self, file_path):
        """Calculate MD5 hash of a file"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.warning(f'Failed to calculate MD5 hash: {str(e)}')
            return ''
    
    def _calculate_sha1(self, file_path):
        """Calculate SHA1 hash of a file"""
        try:
            hash_sha1 = hashlib.sha1()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha1.update(chunk)
            return hash_sha1.hexdigest()
        except Exception as e:
            logger.warning(f'Failed to calculate SHA1 hash: {str(e)}')
            return ''
    
    def _process_file(self, file_record):
        """Process a file using the GenericFileHandlerAgent"""
        try:
            # Import the agent
            from agents.generic_file_handler_agent import GenericFileHandlerAgent, FileCategory
            
            # Create agent instance
            agent = GenericFileHandlerAgent()
            
            # Get file path
            file_path = file_record.get_file_path()
            if not file_path or not os.path.exists(file_path):
                logger.error(f'File not found: {file_path}')
                file_record.processing_status = 'error'
                file_record.save()
                return
            
            # Set processing status
            file_record.processing_status = 'processing'
            file_record.save()
            
            # Process the file
            result = agent._process_single_file(file_path)
            
            if result.success and result.file_metadata:
                # Update file record with extracted metadata
                quality_grade = getattr(result.file_metadata, 'quality_grade', None)
                metadata_dict = {
                    'file_category': result.file_metadata.file_category.value,
                    'mime_type': result.file_metadata.mime_type,
                    'quality_score': result.file_metadata.quality_score or 0.0,
                    'quality_grade': getattr(quality_grade, 'value', quality_grade) or 'unknown',
                    'quality_issues': result.file_metadata.quality_issues or [],
                    'content_metadata': result.file_metadata.custom_metadata or {}
                }
                
                # Add type-specific metadata
                if result.file_metadata.file_category.value in ['tabular', 'spectral']:
                    metadata_dict.update({
                        'num_rows': result.file_metadata.num_rows,
                        'num_columns': result.file_metadata.num_columns,
                        'column_names': result.file_metadata.column_names or [],
                        'data_types': result.file_metadata.data_types or {}
                    })
                elif result.file_metadata.file_category.value == 'text':
                    metadata_dict.update({
                        'num_lines': result.file_metadata.num_lines,
                        'num_words': result.file_metadata.num_words,
                        'num_characters': result.file_metadata.num_characters
                    })
                elif result.file_metadata.file_category.value == 'image':
                    metadata_dict.update({
                        'image_width': result.file_metadata.image_width,
                        'image_height': result.file_metadata.image_height,
                        'image_channels': result.file_metadata.image_channels,
                        'image_format': result.file_metadata.image_format
                    })
                elif result.file_metadata.file_category.value == 'audio':
                    metadata_dict.update({
                        'audio_duration': result.file_metadata.audio_duration,
                        'audio_sample_rate': result.file_metadata.audio_sample_rate,
                        'audio_channels': result.file_metadata.audio_channels,
                        'audio_bit_rate': result.file_metadata.audio_bit_rate
                    })
                elif result.file_metadata.file_category.value == 'archive':
                    metadata_dict.update({
                        'archive_contents': result.file_metadata.archive_contents or [],
                        'archive_num_files': result.file_metadata.archive_num_files
                    })
                
                # Update processing information
                metadata_dict.update({
                    'processing_results': result.analysis_results or {},
                    'recommendations': result.recommendations or [],
                    'processed_by_agent': 'GenericFileHandlerAgent',
                    'agent_version': agent.version,
                    'processing_parameters': {}
                })
                
                # Save with metadata
                file_record.save_with_metadata(metadata_dict)
                
                # Update analysis results if available
                if result.analysis_results:
                    file_record.analysis_results = result.analysis_results
                    file_record.save()
                
                logger.info(f'Successfully processed file: {file_record.name}')
                
            else:
                # Handle processing failure
                file_record.processing_status = 'error'
                file_record.is_valid = False
                if result.processing_errors:
                    file_record.quality_issues = result.processing_errors
                file_record.save()
                logger.error(f'Failed to process file: {file_record.name}')
                
        except Exception as e:
            logger.error(f'Error processing file {file_record.name}: {str(e)}', exc_info=True)
            file_record.processing_status = 'error'
            file_record.is_valid = False
            file_record.quality_issues = [str(e)]
            file_record.save()


class FileDeleteView(APIView):
    """Delete a file"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, file_id):
        try:
            file = GenericFile.objects.get(id=file_id, user=request.user)
            
            # Delete the file from storage
            if file.file:
                file.file.delete(save=False)
            if file.thumbnail:
                file.thumbnail.delete(save=False)
            if file.preview_file:
                file.preview_file.delete(save=False)
            
            # Delete the record
            file.delete()
            
            return Response({
                'success': True,
                'message': 'File deleted successfully'
            })
            
        except GenericFile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'File not found',
                'message': 'The requested file does not exist or you do not have permission to access it'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f'Error deleting file: {str(e)}', exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error deleting file'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MultipleFileDeleteView(APIView):
    """Delete multiple files"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            file_ids = request.data.get('file_ids', [])
            
            if not file_ids:
                return Response({
                    'success': False,
                    'error': 'No file IDs provided',
                    'message': 'Please provide at least one file ID'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            deleted_count = 0
            errors = []
            
            for file_id in file_ids:
                try:
                    file = GenericFile.objects.get(id=file_id, user=request.user)
                    
                    # Delete the file from storage
                    if file.file:
                        file.file.delete(save=False)
                    if file.thumbnail:
                        file.thumbnail.delete(save=False)
                    if file.preview_file:
                        file.preview_file.delete(save=False)
                    
                    # Delete the record
                    file.delete()
                    deleted_count += 1
                    
                except GenericFile.DoesNotExist:
                    errors.append(f'File {file_id} not found')
                except Exception as e:
                    errors.append(f'File {file_id}: {str(e)}')
            
            return Response({
                'success': True,
                'deleted_count': deleted_count,
                'errors': errors,
                'message': f'Successfully deleted {deleted_count} file(s)'
            })
            
        except Exception as e:
            logger.error(f'Error deleting multiple files: {str(e)}', exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error deleting files'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileDownloadView(APIView):
    """Download a file"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, file_id):
        try:
            file = GenericFile.objects.get(id=file_id, user=request.user)
            
            if not file.file:
                return Response({
                    'success': False,
                    'error': 'File not found',
                    'message': 'The file does not exist on the server'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Return the file
            response = FileResponse(file.file.open('rb'))
            response['Content-Disposition'] = f'attachment; filename="{file.original_filename}"'
            response['Content-Type'] = file.mime_type or 'application/octet-stream'
            response['Content-Length'] = file.file_size
            
            return response
            
        except GenericFile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'File not found',
                'message': 'The requested file does not exist or you do not have permission to access it'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f'Error downloading file: {str(e)}', exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error downloading file'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileAnalyzeView(APIView):
    """Analyze a file using the appropriate agent"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, file_id):
        try:
            file = GenericFile.objects.get(id=file_id, user=request.user)
            
            # Check if file exists
            file_path = file.get_file_path()
            if not file_path or not os.path.exists(file_path):
                return Response({
                    'success': False,
                    'error': 'File not found on server',
                    'message': 'The file does not exist on the server'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Set analyzing status
            file.processing_status = 'analyzing'
            file.save()
            
            # Process the file (this will also analyze it)
            from agents.generic_file_handler_agent import GenericFileHandlerAgent
            
            agent = GenericFileHandlerAgent()
            result = agent._process_single_file(file_path)
            
            if result.success:
                # Update file with analysis results
                file.analysis_results = result.analysis_results or {}
                file.recommendations = result.recommendations or []
                file.is_analyzed = True
                file.analyzed_at = datetime.now()
                file.processing_status = 'analyzed'
                file.save()
                
                return Response({
                    'success': True,
                    'analysis_results': result.analysis_results,
                    'recommendations': result.recommendations,
                    'message': 'File analysis completed'
                })
            else:
                file.processing_status = 'error'
                file.save()
                
                return Response({
                    'success': False,
                    'errors': result.processing_errors or [],
                    'message': 'File analysis failed'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except GenericFile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'File not found',
                'message': 'The requested file does not exist or you do not have permission to access it'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f'Error analyzing file: {str(e)}', exc_info=True)
            file.processing_status = 'error'
            file.save()
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error analyzing file'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileCrewAnalysisView(APIView):
    """Run the full CrewAI analysis pipeline (agents + report) on an uploaded file.

    Bridges the Generic File API (S3 format-agnostic loader) with the
    OP6 NIRAnalysisCrew: loads the stored file, converts the unified
    spectral schema to the crew's wavelengths/intensities contract and
    runs analyze_sample including the comprehensive HTML report.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        try:
            file = GenericFile.objects.get(id=file_id, user=request.user)

            file_path = file.get_file_path()
            if not file_path or not os.path.exists(file_path):
                return Response({
                    'success': False,
                    'error': 'File not found on server',
                    'message': 'The file does not exist on the server'
                }, status=status.HTTP_404_NOT_FOUND)

            from agents.data_preparation_agent import EnhancedDataPreparationAgent

            loader = EnhancedDataPreparationAgent(
                input_directory=os.path.dirname(file_path),
                output_directory=tempfile.mkdtemp(prefix='crew_bridge_'),
            )
            spectral = loader._load_spectral_data(file_path)
            if not spectral or spectral.get('data') is None or len(spectral.get('data', [])) == 0:
                return Response({
                    'success': False,
                    'error': 'Not a parseable spectral file',
                    'message': 'The file could not be parsed as spectral data (S3 loader)'
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            df = spectral.get('data')
            wavelength_column = spectral.get('wavelength_column')
            intensity_column = spectral.get('intensity_column')
            if wavelength_column not in df.columns or intensity_column not in df.columns:
                return Response({
                    'success': False,
                    'error': 'Spectral columns not found',
                    'message': 'Wavelength/intensity columns missing in parsed data'
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            wavelengths_raw = df[wavelength_column].tolist()
            intensities_raw = df[intensity_column].tolist()

            # Spectrometer exports often carry header/metadata rows (e.g.
            # 'Daten', units, blank lines) inside the numeric columns.
            # Convert tolerantly: keep only rows where BOTH values parse as
            # finite numbers, so a text row cannot crash the analysis.
            def _to_float(value):
                from agents.data_preparation_agent import EnhancedDataPreparationAgent
                try:
                    return float(EnhancedDataPreparationAgent._normalise_decimal_string(value))
                except (TypeError, ValueError):
                    return None

            def _column_pairs(wl_col, it_col):
                pairs = []
                for wl_raw, it_raw in zip(df[wl_col].tolist(), df[it_col].tolist()):
                    wl = _to_float(wl_raw)
                    it = _to_float(it_raw)
                    if wl is None or it is None:
                        continue
                    if math.isfinite(wl) and math.isfinite(it):
                        pairs.append((wl, it))
                return pairs

            numeric_pairs = _column_pairs(wavelength_column, intensity_column)

            # The loader picks columns by name patterns and heuristics; exotic
            # exports (unexpected column names, transposed tables, extra
            # metadata columns) can defeat that guess. When the chosen pair
            # yields nothing usable, scan ALL column pairs and keep the one
            # with the most finite (wavelength, intensity) rows.
            if not numeric_pairs:
                best_pairs, best_wl_col, best_it_col = [], None, None
                for wl_col in df.columns:
                    for it_col in df.columns:
                        if wl_col == it_col:
                            continue
                        pairs = _column_pairs(wl_col, it_col)
                        if len(pairs) > len(best_pairs):
                            best_pairs = pairs
                            best_wl_col, best_it_col = wl_col, it_col
                if best_pairs:
                    numeric_pairs = best_pairs
                    wavelength_column, intensity_column = best_wl_col, best_it_col
                    wavelengths_raw = df[wavelength_column].tolist()
                    intensities_raw = df[intensity_column].tolist()

            if not numeric_pairs:
                sample_rows = []
                for wl_raw, it_raw in list(zip(wavelengths_raw, intensities_raw))[:5]:
                    sample_rows.append(f'{wl_raw!r} | {it_raw!r}')
                return Response({
                    'success': False,
                    'error': 'No finite spectral values',
                    'message': (
                        f'The file parsed but contained no usable numeric '
                        f'wavelength/intensity rows. Detected columns: '
                        f'{wavelength_column!r}, {intensity_column!r}; '
                        f'available columns: {list(df.columns)!r}; '
                        f'first rows (wavelength | intensity): '
                        f'{"; ".join(sample_rows)}'
                    ),
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            wavelengths = [p[0] for p in numeric_pairs]
            intensities = [p[1] for p in numeric_pairs]

            # Keep the row count consistent for the report page.
            finite_pairs = numeric_pairs

            from agents.nir_analysis_crew import (
                NIRAnalysisCrew, CrewConfiguration, AnalysisRequest, AnalysisMode,
            )
            from agents.reporting_agent import ReportType, ReportFormat

            # Mission statement: the crew uses the local LLM (Ollama +
            # mistral in Docker) when the CrewAI package is installed and
            # the endpoint answers. Otherwise the deterministic standalone
            # agent path runs unchanged - same results, no LLM narration.
            try:
                import crewai  # noqa: F401
                import requests as _requests
                _llm_up = _requests.get(
                    f"{os.environ.get('OLLAMA_URL', 'http://localhost:11434').rstrip('/')}/api/tags",
                    timeout=2,
                ).ok
            except Exception:
                _llm_up = False

            config = CrewConfiguration(
                enable_crewai=_llm_up,
                temp_dir=tempfile.mkdtemp(prefix='crew_'),
                output_dir=str(Path(settings.BASE_DIR) / 'output' / 'analysis'),
            )
            crew = NIRAnalysisCrew(config)
            request_obj = AnalysisRequest(
                sample_id=str(file.id),
                spectral_data={'wavelengths': wavelengths, 'intensities': intensities},
                metadata={
                    'file_name': file.name,
                    'file_extension': file.file_extension,
                    **(spectral.get('metadata') or {}),
                },
                file_paths=[file_path],
                analysis_mode=AnalysisMode.STANDARD,
                report_type=ReportType.COMPREHENSIVE,
                report_format=ReportFormat.HTML,
                include_calibration=bool(request.data.get('include_calibration', True)),
                user_id=str(request.user.id),
            )
            result = crew.analyze_sample(request_obj)

            summary = NIRAnalysisCrew._json_safe(crew.get_analysis_summary(result))
            reports = []
            for report in result.generated_reports:
                reports.append({
                    'report_id': report.report_id,
                    'report_type': report.report_type.value if hasattr(report.report_type, 'value') else str(report.report_type),
                    'format': report.format.value if hasattr(report.format, 'value') else str(report.format),
                    'file_path': report.file_path,
                    'status': report.status.value if hasattr(report.status, 'value') else str(report.status),
                })

            file.analysis_results = {
                **(file.analysis_results or {}),
                'crew_analysis': {
                    'request_id': result.request_id,
                    'overall_quality_score': result.overall_quality_score,
                    'recommendations': result.recommendations,
                    'warnings': result.warnings,
                    'errors': result.errors,
                    'processing_time': result.processing_time,
                },
                'crew_summary': summary,
                'spectral_series': {
                    'wavelengths': wavelengths,
                    'intensities': intensities,
                },
            }
            file.is_analyzed = True
            file.analyzed_at = datetime.now()
            file.processing_status = 'analyzed'
            file.save()

            return Response({
                'success': True,
                'request_id': result.request_id,
                'overall_quality_score': result.overall_quality_score,
                'recommendations': result.recommendations,
                'warnings': result.warnings,
                'errors': result.errors,
                'reports': reports,
                'summary': summary,
                'spectral_data': {
                    'wavelengths': wavelengths,
                    'intensities': intensities,
                },
                'report_url': f"/analysis/report/{file.id}/",
                'message': 'CrewAI analysis completed'
            })

        except GenericFile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'File not found',
                'message': 'The requested file does not exist or you do not have permission to access it'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f'Error running crew analysis: {str(e)}', exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error running CrewAI analysis'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MultipleFileAnalyzeView(APIView):
    """Analyze multiple files"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            file_ids = request.data.get('file_ids', [])
            
            if not file_ids:
                return Response({
                    'success': False,
                    'error': 'No file IDs provided',
                    'message': 'Please provide at least one file ID'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            analyzed_count = 0
            errors = []
            results = []
            
            for file_id in file_ids:
                try:
                    file = GenericFile.objects.get(id=file_id, user=request.user)
                    
                    # Check if file exists
                    file_path = file.get_file_path()
                    if not file_path or not os.path.exists(file_path):
                        errors.append(f'File {file_id}: File not found on server')
                        continue
                    
                    # Set analyzing status
                    file.processing_status = 'analyzing'
                    file.save()
                    
                    # Process the file
                    from agents.generic_file_handler_agent import GenericFileHandlerAgent
                    
                    agent = GenericFileHandlerAgent()
                    result = agent._process_single_file(file_path)
                    
                    if result.success:
                        # Update file with analysis results
                        file.analysis_results = result.analysis_results or {}
                        file.recommendations = result.recommendations or []
                        file.is_analyzed = True
                        file.analyzed_at = datetime.now()
                        file.processing_status = 'analyzed'
                        file.save()
                        
                        results.append({
                            'file_id': file_id,
                            'success': True,
                            'analysis_results': result.analysis_results,
                            'recommendations': result.recommendations
                        })
                        analyzed_count += 1
                    else:
                        file.processing_status = 'error'
                        file.save()
                        
                        results.append({
                            'file_id': file_id,
                            'success': False,
                            'errors': result.processing_errors or []
                        })
                        errors.append(f'File {file_id}: Analysis failed')
                        
                except GenericFile.DoesNotExist:
                    errors.append(f'File {file_id} not found')
                    results.append({
                        'file_id': file_id,
                        'success': False,
                        'error': 'File not found'
                    })
                except Exception as e:
                    errors.append(f'File {file_id}: {str(e)}')
                    results.append({
                        'file_id': file_id,
                        'success': False,
                        'error': str(e)
                    })
            
            return Response({
                'success': True,
                'analyzed_count': analyzed_count,
                'results': results,
                'errors': errors,
                'message': f'Successfully analyzed {analyzed_count} file(s)'
            })
            
        except Exception as e:
            logger.error(f'Error analyzing multiple files: {str(e)}', exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error analyzing files'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileCategoryView(APIView):
    """Get supported file categories and extensions"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            from agents.generic_file_handler_agent import GenericFileHandlerAgent
            
            agent = GenericFileHandlerAgent()
            
            return Response({
                'success': True,
                'categories': agent.get_supported_categories(),
                'extensions': agent.get_supported_extensions(),
                'message': 'Supported file categories and extensions'
            })
            
        except Exception as e:
            logger.error(f'Error getting file categories: {str(e)}', exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error getting file categories'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileStatisticsView(APIView):
    """Get statistics about files"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            files = GenericFile.objects.filter(user=request.user)
            
            # Basic statistics
            statistics = {
                'total_files': files.count(),
                'total_size': sum(file.file_size for file in files if file.file_size),
                'valid_files': files.filter(is_valid=True).count(),
                'invalid_files': files.filter(is_valid=False).count(),
                'processed_files': files.filter(is_processed=True).count(),
                'analyzed_files': files.filter(is_analyzed=True).count(),
                'by_category': {},
                'by_quality': {},
                'by_status': {}
            }
            
            # Statistics by category
            for category in GenericFile.FILE_CATEGORIES:
                category_name = category[0]
                category_files = files.filter(file_category=category_name)
                if category_files.exists():
                    statistics['by_category'][category_name] = {
                        'count': category_files.count(),
                        'total_size': sum(f.file_size for f in category_files if f.file_size)
                    }
            
            # Statistics by quality
            for quality in GenericFile.QUALITY_GRADES:
                quality_name = quality[0]
                quality_files = files.filter(quality_grade=quality_name)
                if quality_files.exists():
                    statistics['by_quality'][quality_name] = quality_files.count()
            
            # Statistics by processing status
            for status in GenericFile.PROCESSING_STATUSES:
                status_name = status[0]
                status_files = files.filter(processing_status=status_name)
                if status_files.exists():
                    statistics['by_status'][status_name] = status_files.count()
            
            return Response({
                'success': True,
                'statistics': statistics,
                'message': 'File statistics retrieved'
            })
            
        except Exception as e:
            logger.error(f'Error getting file statistics: {str(e)}', exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Error getting file statistics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FileCrewReportView(TemplateView):
    """Render the in-app CrewAI analysis report page for an uploaded file.

    The page is driven by the analysis results the crew stored on the file
    (crew_summary, spectral_series, crew_analysis) after a crew-analysis run.
    It mirrors the report experience of the legacy nir_platform: quality
    scorecards, spectral chart, agent result cards and recommendations.
    """

    template_name = 'crew_report.html'

    def get(self, request, file_id):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        try:
            file = GenericFile.objects.get(id=file_id, user=request.user)
        except (GenericFile.DoesNotExist, ValueError, ValidationError):
            raise Http404('File not found')

        analysis_results = file.analysis_results or {}
        crew_summary = analysis_results.get('crew_summary') or {}
        crew_analysis = analysis_results.get('crew_analysis') or {}
        series = analysis_results.get('spectral_series') or {}
        wavelengths = series.get('wavelengths') or []
        intensities = series.get('intensities') or []

        context = {
            'file': file,
            'page_title': 'CrewAI Analysis Report',
            'crew_summary': crew_summary,
            'crew_analysis': crew_analysis,
            'spectral_analysis': crew_summary.get('spectral_analysis') or {},
            'metadata_quality': crew_summary.get('metadata_quality') or {},
            'sensor_quality': crew_summary.get('sensor_quality') or {},
            'statistical_analysis': crew_summary.get('statistical_analysis') or {},
            'neural_network': crew_summary.get('neural_network') or {},
            'recommendations': crew_summary.get('recommendations')
            or crew_analysis.get('recommendations') or [],
            'warnings': crew_summary.get('warnings') or crew_analysis.get('warnings') or [],
            'errors': crew_summary.get('errors') or crew_analysis.get('errors') or [],
            'reports': crew_summary.get('reports') or [],
            'overall_quality_score': crew_summary.get('overall_quality_score')
            or crew_analysis.get('overall_quality_score') or 0,
            'spectral_series_json': json.dumps({
                'wavelengths': wavelengths,
                'intensities': intensities,
            }),
            'summary_json': json.dumps(crew_summary),
        }
        return render(request, self.template_name, context)
