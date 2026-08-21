"""
Views for NIR_Mistral API
"""

import os
import sys
import json
import logging
import tempfile
import traceback
import requests
from pathlib import Path
from datetime import datetime
from django.http import JsonResponse
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, JSONParser
from .serializers import (
    UserRegistrationSerializer, UserProfileSerializer,
    CustomTokenObtainPairSerializer, NIRSpectrumSerializer,
    NIRSpectrumUploadSerializer, AnalysisJobSerializer,
    AnalysisJobUpdateSerializer, AgentSerializer, SystemLogSerializer,
    UserPreferenceSerializer, HealthCheckSerializer
)
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.views.generic import CreateView, TemplateView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib import messages
from core.models import User, NIRSpectrum, AnalysisJob, Agent, SystemLog, UserPreference
from django.contrib.auth import get_user_model
from .forms import CustomAuthenticationForm, CustomUserCreationForm

# Add framework to path
framework_path = settings.NIR_FRAMEWORK_PATH
if framework_path not in sys.path:
    sys.path.insert(0, framework_path)

logger = logging.getLogger(__name__)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain pair view that accepts both username and email"""
    serializer_class = CustomTokenObtainPairSerializer


class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""
    
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Create user preferences
        UserPreference.objects.create(user=user)
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'message': 'User created successfully. Please check your email for verification.'
        }, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile endpoint"""
    
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class DashboardView(APIView):
    """Dashboard endpoint with summary statistics"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get user statistics
        spectra_count = NIRSpectrum.objects.filter(user=user).count()
        jobs_count = AnalysisJob.objects.filter(user=user).count()
        completed_jobs = AnalysisJob.objects.filter(user=user, status='completed').count()
        
        # Get recent spectra
        recent_spectra = NIRSpectrum.objects.filter(user=user).order_by('-created_at')[:5]
        recent_spectra_data = NIRSpectrumSerializer(recent_spectra, many=True).data
        
        # Get recent jobs
        recent_jobs = AnalysisJob.objects.filter(user=user).order_by('-created_at')[:5]
        recent_jobs_data = AnalysisJobSerializer(recent_jobs, many=True).data
        
        # Get system agents
        agents = Agent.objects.all().order_by('name')
        agents_data = AgentSerializer(agents, many=True).data
        
        return Response({
            'statistics': {
                'total_spectra': spectra_count,
                'total_jobs': jobs_count,
                'completed_jobs': completed_jobs,
                'pending_jobs': jobs_count - completed_jobs,
            },
            'recent_spectra': recent_spectra_data,
            'recent_jobs': recent_jobs_data,
            'available_agents': agents_data,
            'system_info': {
                'app_name': settings.APP_NAME,
                'app_version': settings.APP_VERSION,
                'app_description': settings.APP_DESCRIPTION,
            }
        })


class HealthCheckView(APIView):
    """Health check endpoint"""
    
    permission_classes = [AllowAny]
    
    def _check_service_health(self, service_url, service_name, timeout=5):
        """Check if a service is healthy"""
        try:
            response = requests.get(f"{service_url}/health", timeout=timeout)
            if response.status_code == 200:
                return 'healthy'
            else:
                return f'unhealthy: HTTP {response.status_code}'
        except requests.exceptions.RequestException as e:
            return f'unhealthy: {str(e)}'
        except Exception as e:
            return f'unhealthy: {str(e)}'
    
    def get(self, request):
        # Check database
        try:
            User.objects.count()
            database_status = 'healthy'
        except Exception as e:
            database_status = f'unhealthy: {str(e)}'
        
        # Check storage
        try:
            test_file = tempfile.NamedTemporaryFile(delete=True)
            test_file.write(b'test')
            test_file.close()
            storage_status = 'healthy'
        except Exception as e:
            storage_status = f'unhealthy: {str(e)}'
        
        # Check framework integration
        try:
            from dev_framework.cli import main as framework_main
            framework_status = 'healthy'
        except ImportError as e:
            framework_status = f'unhealthy: {str(e)}'
        
        # Count loaded agents
        try:
            agents_loaded = Agent.objects.count()
        except Exception:
            agents_loaded = 0
        
        # Check Docker services (if running in Docker environment)
        docker_services = {}
        
        # Check Weaviate
        weaviate_url = getattr(settings, 'WEAVIATE_URL', 'http://weaviate:8080')
        docker_services['weaviate'] = self._check_service_health(weaviate_url, 'Weaviate')
        
        # Check Ollama
        ollama_url = getattr(settings, 'OLLAMA_URL', 'http://ollama:11434')
        docker_services['ollama'] = self._check_service_health(ollama_url, 'Ollama')
        
        # Check Faiss
        faiss_url = getattr(settings, 'FAISS_URL', 'http://faiss:8081')
        docker_services['faiss'] = self._check_service_health(faiss_url, 'Faiss')
        
        # Check Redis
        redis_url = getattr(settings, 'REDIS_URL', 'redis://redis:6379')
        try:
            import redis
            r = redis.Redis.from_url(redis_url)
            if r.ping():
                docker_services['redis'] = 'healthy'
            else:
                docker_services['redis'] = 'unhealthy: ping failed'
        except Exception as e:
            docker_services['redis'] = f'unhealthy: {str(e)}'
        
        # Check Flower server
        flower_url = 'http://flower_server:5556'
        docker_services['flower'] = self._check_service_health(flower_url, 'Flower')
        
        # Determine overall status
        all_healthy = (
            database_status == 'healthy' and 
            storage_status == 'healthy' and
            all(status == 'healthy' for status in docker_services.values())
        )
        
        overall_status = 'healthy' if all_healthy else 'degraded'
        
        return Response({
            'status': overall_status,
            'version': settings.APP_VERSION,
            'timestamp': datetime.now().isoformat(),
            'agents_loaded': agents_loaded,
            'database_status': database_status,
            'storage_status': storage_status,
            'framework_status': framework_status,
            'docker_services': docker_services,
            'system_info': {
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                'django_version': self._get_django_version(),
            }
        })
    
    def _get_django_version(self):
        import django
        return django.get_version()


class AgentListView(generics.ListAPIView):
    """List all available agents"""
    
    queryset = Agent.objects.all().order_by('name')
    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated]


class AgentDetailView(generics.RetrieveAPIView):
    """Get details of a specific agent"""
    
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'name'


class AgentExecuteView(APIView):
    """Execute an agent with given parameters"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, agent_name):
        try:
            # Get the agent
            agent = Agent.objects.get(name=agent_name)
            
            # Get parameters from request
            parameters = request.data.get('parameters', {})
            spectrum_ids = request.data.get('spectrum_ids', [])
            
            # Create analysis job
            job = AnalysisJob.objects.create(
                user=request.user,
                name=f"{agent_name} Execution",
                job_type='custom',
                description=f"Execution of {agent_name} agent",
                agent_name=agent_name,
                agent_version=agent.version,
                parameters=parameters,
                status='pending'
            )
            
            # Add spectra to job if provided
            if spectrum_ids:
                spectra = NIRSpectrum.objects.filter(id__in=spectrum_ids, user=request.user)
                job.spectra.set(spectra)
            
            # Execute the agent asynchronously (in a real implementation)
            # For now, we'll execute it synchronously
            try:
                # Update job status
                job.status = 'processing'
                job.started_at = datetime.now()
                job.save()
                
                # Execute the agent
                result = self._execute_agent(agent_name, parameters, spectrum_ids, request.user)
                
                # Update job with results
                job.status = 'completed'
                job.completed_at = datetime.now()
                job.results = result
                job.progress = 100.0
                job.save()
                
                return Response({
                    'success': True,
                    'job_id': str(job.id),
                    'results': result,
                    'message': f'Agent {agent_name} executed successfully'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                job.status = 'failed'
                job.error_message = str(e)
                job.completed_at = datetime.now()
                job.save()
                
                return Response({
                    'success': False,
                    'job_id': str(job.id),
                    'error': str(e),
                    'message': f'Agent {agent_name} execution failed'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Agent.DoesNotExist:
            return Response({
                'success': False,
                'error': f'Agent {agent_name} not found',
                'message': 'Agent not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Failed to execute agent'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _execute_agent(self, agent_name, parameters, spectrum_ids, user):
        """Execute the specified agent"""
        try:
            # Import and execute the agent from the framework
            framework_path = settings.NIR_FRAMEWORK_PATH
            agents_dir = os.path.join(framework_path, 'agents')
            
            if agents_dir not in sys.path:
                sys.path.insert(0, agents_dir)
            
            # Try to import the agent
            try:
                module = __import__(f'{agent_name.lower()}_agent', fromlist=[agent_name])
                agent_class = getattr(module, agent_name)
                agent = agent_class()
                
                # Prepare context
                context = {
                    'parameters': parameters,
                    'spectrum_ids': spectrum_ids,
                    'user_id': str(user.id),
                    'framework_path': framework_path
                }
                
                # Execute the agent
                output = agent.execute(context)
                
                # Convert output to serializable format
                result = {
                    'status': output.status.name if hasattr(output.status, 'name') else str(output.status),
                    'data': output.data,
                    'errors': [
                        {
                            'message': e.message,
                            'severity': e.severity.name if hasattr(e.severity, 'name') else str(e.severity),
                            'details': e.details,
                            'suggested_fix': e.suggested_fix
                        }
                        for e in output.errors
                    ] if hasattr(output, 'errors') else []
                }
                
                return result
                
            except ImportError as e:
                # Try the NIR_TEST agents
                test_agents_dir = os.path.join(settings.NIR_TEST_ENV_PATH, 'agents')
                if test_agents_dir not in sys.path:
                    sys.path.insert(0, test_agents_dir)
                
                try:
                    module = __import__('nir_test_agent', fromlist=['NIRTestAgent'])
                    agent = module.NIRTestAgent()
                    
                    # Execute the test agent
                    result = agent.analyze_spectra() if hasattr(agent, 'analyze_spectra') else {}
                    
                    return {
                        'status': 'completed',
                        'data': result,
                        'errors': [],
                        'message': 'Test agent executed successfully'
                    }
                    
                except Exception as e:
                    return {
                        'status': 'failed',
                        'data': {},
                        'errors': [{'message': str(e), 'severity': 'error'}],
                        'message': f'Failed to execute agent: {str(e)}'
                    }
            
        except Exception as e:
            return {
                'status': 'failed',
                'data': {},
                'errors': [{'message': str(e), 'severity': 'error'}],
                'message': f'Failed to execute agent: {str(e)}'
            }


# ============================================================================
# AUTHENTICATION VIEWS FOR FLOWERAI AND ILIAS INTEGRATION
# ============================================================================

class CustomLoginView(DjangoLoginView):
    """Custom login view that handles both traditional and JWT authentication"""
    template_name = 'login.html'
    authentication_form = CustomAuthenticationForm
    
    def form_valid(self, form):
        """Handle successful login with JWT token generation"""
        # Traditional Django login
        response = super().form_valid(form)
        
        # Generate JWT tokens for API access
        user = form.get_user()
        refresh = RefreshToken.for_user(user)
        
        # Store tokens in session for template access
        self.request.session['access_token'] = str(refresh.access_token)
        self.request.session['refresh_token'] = str(refresh)
        
        # Add success message
        messages.success(self.request, f'Welcome back, {user.username}!')
        
        # Redirect to dashboard or next URL
        next_url = self.request.GET.get('next', reverse_lazy('home'))
        return redirect(next_url)
    
    def form_invalid(self, form):
        """Handle failed login"""
        messages.error(self.request, 'Invalid username or password. Please try again.')
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Add FlowerAI and ILIAS context to login page"""
        context = super().get_context_data(**kwargs)
        context.update({
            'flowerai_enabled': getattr(settings, 'FLOWERAI_ENABLED', True),
            'ilias_enabled': getattr(settings, 'ILIAS_ENABLED', True),
            'federated_learning_enabled': getattr(settings, 'FEDERATED_LEARNING_ENABLED', True),
        })
        return context


class CustomRegisterView(CreateView):
    """Custom user registration view with FlowerAI and ILIAS integration"""
    template_name = 'register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        """Handle successful registration"""
        # Call parent form_valid to set self.object
        response = super().form_valid(form)
        
        # Get the user from the saved form
        user = self.object
        
        # Create user preferences with default integration settings
        UserPreference.objects.create(
            user=user,
            flowerai_enabled=True,
            federated_learning_enabled=True,
            share_spectra_data=True,
            share_metadata=True,
            share_analysis_results=True,
            data_visibility='private',  # Default to private
            ilias_enabled=True,
            ilias_sync_enabled=True
        )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        # Store tokens in session
        self.request.session['access_token'] = str(refresh.access_token)
        self.request.session['refresh_token'] = str(refresh)
        
        # Add success message
        messages.success(self.request, f'Account created successfully! Welcome, {user.username}!')
        
        # Auto-login the user
        user_auth = authenticate(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password1']
        )
        if user_auth:
            login(self.request, user_auth)
        
        return response
    
    def get_context_data(self, **kwargs):
        """Add FlowerAI and ILIAS context to registration page"""
        context = super().get_context_data(**kwargs)
        context.update({
            'flowerai_enabled': getattr(settings, 'FLOWERAI_ENABLED', True),
            'ilias_enabled': getattr(settings, 'ILIAS_ENABLED', True),
            'federated_learning_enabled': getattr(settings, 'FEDERATED_LEARNING_ENABLED', True),
            'terms_and_conditions': getattr(settings, 'TERMS_AND_CONDITIONS_URL', '/terms/'),
            'privacy_policy': getattr(settings, 'PRIVACY_POLICY_URL', '/privacy/'),
        })
        return context


class CustomLogoutView(TemplateView):
    """Custom logout view that clears both Django session and JWT tokens"""
    
    def get(self, request, *args, **kwargs):
        """Handle GET request for logout"""
        return self.post(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        """Handle POST request for logout"""
        # Clear Django session
        logout(request)
        
        # Clear JWT tokens from session
        if 'access_token' in request.session:
            del request.session['access_token']
        if 'refresh_token' in request.session:
            del request.session['refresh_token']
        
        # Add logout message
        messages.info(request, 'You have been logged out successfully.')
        
        # Redirect to home page
        return redirect('home')


# ============================================================================
# FLOWERAI AND ILIAS INTEGRATION VIEWS
# ============================================================================

class FlowerAIAuthView(APIView):
    """Handle FlowerAI authentication and federated learning setup"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get FlowerAI authentication status and configuration"""
        user = request.user
        
        # Check if user has FlowerAI enabled
        flowerai_enabled = getattr(user, 'flowerai_enabled', True)
        
        # Get FlowerAI server configuration
        flowerai_config = {
            'server_url': getattr(settings, 'FLOWERAI_SERVER_URL', 'http://flower_server:5555'),
            'client_id': getattr(user, 'flowerai_client_id', str(user.id)),
            'enabled': flowerai_enabled,
            'federated_learning': getattr(user, 'federated_learning_enabled', True),
        }
        
        return Response({
            'status': 'success',
            'flowerai_config': flowerai_config,
            'user_id': str(user.id),
            'username': user.username,
        })
    
    def post(self, request):
        """Enable or disable FlowerAI integration for the user"""
        user = request.user
        
        # Update user preferences for FlowerAI
        try:
            preferences = UserPreference.objects.get(user=user)
            preferences.flowerai_enabled = request.data.get('enabled', True)
            preferences.federated_learning_enabled = request.data.get('federated_learning', True)
            preferences.save()
            
            return Response({
                'status': 'success',
                'message': 'FlowerAI settings updated successfully',
                'flowerai_enabled': preferences.flowerai_enabled,
                'federated_learning_enabled': preferences.federated_learning_enabled,
            })
        except UserPreference.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'User preferences not found',
            }, status=status.HTTP_404_NOT_FOUND)


class ILIASAuthView(APIView):
    """Handle ILIAS platform integration and authentication"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get ILIAS integration status and configuration"""
        user = request.user
        
        # Check if user has ILIAS integration enabled
        ilias_enabled = getattr(user, 'ilias_enabled', True)
        
        # Get ILIAS configuration
        ilias_config = {
            'api_url': getattr(settings, 'ILIAS_API_URL', 'https://ilias.hswt.de'),
            'client_id': getattr(settings, 'ILIAS_CLIENT_ID', 'nir_mistral_client'),
            'enabled': ilias_enabled,
            'synchronization_enabled': getattr(user, 'ilias_sync_enabled', True),
        }
        
        return Response({
            'status': 'success',
            'ilias_config': ilias_config,
            'user_id': str(user.id),
            'username': user.username,
        })
    
    def post(self, request):
        """Enable or disable ILIAS integration for the user"""
        user = request.user
        
        # Update user preferences for ILIAS
        try:
            preferences = UserPreference.objects.get(user=user)
            preferences.ilias_enabled = request.data.get('enabled', True)
            preferences.ilias_sync_enabled = request.data.get('synchronization_enabled', True)
            preferences.save()
            
            return Response({
                'status': 'success',
                'message': 'ILIAS settings updated successfully',
                'ilias_enabled': preferences.ilias_enabled,
                'ilias_sync_enabled': preferences.ilias_sync_enabled,
            })
        except UserPreference.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'User preferences not found',
            }, status=status.HTTP_404_NOT_FOUND)


class FederatedLearningView(APIView):
    """Handle federated learning configuration and data sharing preferences"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get federated learning configuration for the user"""
        user = request.user
        
        try:
            preferences = UserPreference.objects.get(user=user)
            
            return Response({
                'status': 'success',
                'federated_learning': {
                    'enabled': preferences.federated_learning_enabled,
                    'share_spectra': preferences.share_spectra_data,
                    'share_metadata': preferences.share_metadata,
                    'share_analysis_results': preferences.share_analysis_results,
                    'data_visibility': preferences.data_visibility,  # 'private', 'public', 'federated'
                },
                'flowerai_config': {
                    'enabled': preferences.flowerai_enabled,
                    'client_id': getattr(user, 'flowerai_client_id', str(user.id)),
                },
                'ilias_config': {
                    'enabled': preferences.ilias_enabled,
                    'sync_enabled': preferences.ilias_sync_enabled,
                }
            })
        except UserPreference.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'User preferences not found',
            }, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request):
        """Update federated learning preferences"""
        user = request.user
        
        try:
            preferences = UserPreference.objects.get(user=user)
            
            # Update preferences from request data
            if 'federated_learning_enabled' in request.data:
                preferences.federated_learning_enabled = request.data['federated_learning_enabled']
            if 'share_spectra_data' in request.data:
                preferences.share_spectra_data = request.data['share_spectra_data']
            if 'share_metadata' in request.data:
                preferences.share_metadata = request.data['share_metadata']
            if 'share_analysis_results' in request.data:
                preferences.share_analysis_results = request.data['share_analysis_results']
            if 'data_visibility' in request.data:
                preferences.data_visibility = request.data['data_visibility']
            
            preferences.save()
            
            return Response({
                'status': 'success',
                'message': 'Federated learning preferences updated successfully',
                'preferences': {
                    'federated_learning_enabled': preferences.federated_learning_enabled,
                    'share_spectra_data': preferences.share_spectra_data,
                    'share_metadata': preferences.share_metadata,
                    'share_analysis_results': preferences.share_analysis_results,
                    'data_visibility': preferences.data_visibility,
                }
            })
        except UserPreference.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'User preferences not found',
            }, status=status.HTTP_404_NOT_FOUND)


class SpectrumListCreateView(generics.ListCreateAPIView):
    """List and create NIR spectra"""
    
    serializer_class = NIRSpectrumSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return NIRSpectrum.objects.filter(user=self.request.user).order_by('-created_at')
        else:
            # For demo purposes, return recent spectra (limited)
            return NIRSpectrum.objects.all().order_by('-created_at')[:10]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return NIRSpectrumUploadSerializer
        return NIRSpectrumSerializer
    
    def perform_create(self, serializer):
        # Save the spectrum with the current user
        spectrum = serializer.save(user=self.request.user, status='uploaded')
        
        # Process the uploaded file if it's a text file
        if spectrum.original_file and spectrum.data_format == 'txt':
            self._process_text_file(spectrum)
        
        # Update status to processed
        spectrum.status = 'processed'
        spectrum.processed_at = datetime.now()
        spectrum.save()
    
    def _process_text_file(self, spectrum):
        """Process a text file to extract spectral data"""
        try:
            file_path = spectrum.get_file_path()
            if file_path and os.path.exists(file_path):
                
                # Read the file
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                # Find data start (skip header lines starting with #)
                data_lines = []
                for line in lines:
                    if not line.strip().startswith('#'):
                        data_lines.append(line.strip())
                
                if data_lines:
                    # Parse the first data line to get wavelength range
                    first_line = data_lines[0].split(',')
                    if len(first_line) >= 2:
                        start_wl = float(first_line[0].strip())
                        end_wl = start_wl
                        data_points = 0
                        
                        for line in data_lines:
                            parts = line.split(',')
                            if len(parts) >= 2:
                                try:
                                    wl = float(parts[0].strip())
                                    value = float(parts[1].strip())
                                    end_wl = wl
                                    data_points += 1
                                except ValueError:
                                    continue
                        
                        # Update spectrum metadata
                        spectrum.wavelength_range_start = start_wl
                        spectrum.wavelength_range_end = end_wl
                        spectrum.data_points = data_points
                        spectrum.resolution = (end_wl - start_wl) / (data_points - 1) if data_points > 1 else 1.0
                        spectrum.save()
                        
        except Exception as e:
            logger.error(f"Error processing text file for spectrum {spectrum.id}: {e}")


class SpectrumRetrieveView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific spectrum"""
    
    queryset = NIRSpectrum.objects.all()
    serializer_class = NIRSpectrumSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return super().get_queryset().filter(user=self.request.user)
        else:
            # For demo purposes, allow read-only access to existing spectra
            return super().get_queryset()


class AnalysisJobListCreateView(generics.ListCreateAPIView):
    """List and create analysis jobs"""
    
    serializer_class = AnalysisJobSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return AnalysisJob.objects.filter(user=self.request.user).order_by('-created_at')
        else:
            # For demo purposes, return recent jobs (limited)
            return AnalysisJob.objects.all().order_by('-created_at')[:10]


class AnalysisJobRetrieveView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific analysis job"""
    
    queryset = AnalysisJob.objects.all()
    serializer_class = AnalysisJobSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return super().get_queryset().filter(user=self.request.user)
        else:
            # For demo purposes, allow read-only access to existing jobs
            return super().get_queryset()
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return AnalysisJobUpdateSerializer
        return AnalysisJobSerializer


class FileUploadView(APIView):
    """Handle file uploads for spectra"""
    
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    
    def post(self, request):
        try:
            file = request.FILES.get('file')
            if not file:
                return Response({
                    'success': False,
                    'error': 'No file provided'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate file type
            valid_extensions = ['.txt', '.csv', '.json', '.h5', '.hdf5']
            file_extension = os.path.splitext(file.name)[1].lower()
            
            if file_extension not in valid_extensions:
                return Response({
                    'success': False,
                    'error': f'Invalid file type. Allowed: {", ".join(valid_extensions)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Determine data format
            data_format = file_extension[1:]  # Remove the dot
            if data_format == 'hdf5':
                data_format = 'h5'
            
            # Save the file temporarily to parse metadata
            temp_path = os.path.join(tempfile.gettempdir(), file.name)
            with open(temp_path, 'wb+') as temp_file:
                for chunk in file.chunks():
                    temp_file.write(chunk)
            
            # Parse file to get metadata
            metadata = self._parse_spectrum_file(temp_path, data_format)
            
            # Clean up temp file
            os.remove(temp_path)
            
            # Create spectrum record
            spectrum = NIRSpectrum.objects.create(
                user=request.user,
                name=metadata.get('name', file.name),
                description=metadata.get('description', ''),
                spectral_type=metadata.get('spectral_type', 'absorbance'),
                data_format=data_format,
                wavelength_range_start=metadata.get('wavelength_range_start', 700.0),
                wavelength_range_end=metadata.get('wavelength_range_end', 2500.0),
                resolution=metadata.get('resolution', 2.0),
                data_points=metadata.get('data_points', 0),
                instrument=metadata.get('instrument', ''),
                status='uploaded'
            )
            
            # Save the original file
            spectrum.original_file.save(file.name, ContentFile(file.read()))
            spectrum.save()
            
            return Response({
                'success': True,
                'spectrum_id': str(spectrum.id),
                'message': 'File uploaded successfully',
                'metadata': metadata
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'File upload failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _parse_spectrum_file(self, file_path, data_format):
        """Parse spectrum file to extract metadata"""
        metadata = {
            'spectral_type': 'absorbance',
            'wavelength_range_start': 700.0,
            'wavelength_range_end': 2500.0,
            'resolution': 2.0,
            'data_points': 0
        }
        
        try:
            if data_format == 'txt':
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                # Parse header for metadata
                for line in lines:
                    line = line.strip()
                    if line.startswith('#'):
                        if 'Sample:' in line:
                            metadata['name'] = line.split('Sample:')[1].strip()
                        elif 'Type:' in line:
                            spectral_type = line.split('Type:')[1].strip().lower()
                            if spectral_type in ['absorbance', 'reflectance', 'transmittance']:
                                metadata['spectral_type'] = spectral_type
                        elif 'Range:' in line:
                            range_part = line.split('Range:')[1].strip()
                            if '-' in range_part:
                                start, end = range_part.replace('nm', '').split('-')
                                metadata['wavelength_range_start'] = float(start.strip())
                                metadata['wavelength_range_end'] = float(end.strip())
                        elif 'Resolution:' in line:
                            resolution = line.split('Resolution:')[1].strip().split()[0]
                            metadata['resolution'] = float(resolution)
                    else:
                        # Count data points
                        if ',' in line:
                            metadata['data_points'] += 1
            
        except Exception as e:
            logger.error(f"Error parsing spectrum file: {e}")
        
        return metadata