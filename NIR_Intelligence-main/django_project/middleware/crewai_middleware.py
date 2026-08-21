"""
NIR Intelligence Platform - Crew AI Middleware

This middleware automatically initializes and manages Crew AI components
for each request, providing seamless integration between Django and Crew AI.

Features:
- Automatic Crew AI initialization on first request
- Request-scoped Crew AI context
- Thread-safe Crew AI instance management
- Error handling and fallback mechanisms
- Task queue management
- Result caching
- Real-time status updates
"""

import sys
import os
import logging
import threading
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from collections import OrderedDict

# Import path configuration
try:
    from path_config import setup_project_paths
    setup_project_paths()
except ImportError:
    # Fallback path setup if path_config not available
    try:
        # Get the absolute path to the agents directory
        agents_dir = Path("/app/agents")
        if agents_dir.exists() and str(agents_dir) not in sys.path:
            sys.path.insert(0, str(agents_dir))
        
        # Also add the project root
        project_root = Path("/app")
        if project_root.exists() and str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
    except Exception:
        pass

from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest, HttpResponse
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class CrewAIMiddleware(MiddlewareMixin):
    """
    Middleware that initializes and manages Crew AI components for each request.
    
    Features:
    - Automatic Crew AI initialization on first request
    - Request-scoped Crew AI context
    - Thread-safe Crew AI instance management
    - Error handling and fallback mechanisms
    - Task queue management
    - Result caching
    - Real-time status updates
    """
    
    # Thread-local storage for Crew AI instances
    _thread_local = threading.local()
    
    # Global Crew AI instance (lazy initialization)
    _global_crew: Optional[Any] = None
    _global_lock = threading.Lock()
    
    # Task queue for background processing
    _task_queue: List[Dict[str, Any]] = []
    _task_queue_lock = threading.Lock()
    
    # Result cache configuration
    CACHE_TIMEOUT = getattr(settings, 'CREWAI_CACHE_TIMEOUT', 3600)  # 1 hour default
    CACHE_PREFIX = 'crewai_result_'
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        
        # Ensure project root is in path
        self._setup_paths()
        
        # Initialize Crew AI components
        self._initialize_crewai()
        
        logger.info("✅ Crew AI Middleware initialized")
    
    def _setup_paths(self):
        """Setup Python paths for Crew AI imports"""
        # Paths are already set at module level, but we can verify here
        try:
            project_root = Path(__file__).parent.parent.parent.parent
            agents_dir = project_root / "agents"
            if str(agents_dir) not in sys.path:
                sys.path.insert(0, str(agents_dir))
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
                
        except Exception as e:
            logger.warning(f"Failed to setup paths for Crew AI: {e}")
    
    def _initialize_crewai(self):
        """Initialize Crew AI components (lazy initialization)"""
        if CrewAIMiddleware._global_crew is None:
            with CrewAIMiddleware._global_lock:
                if CrewAIMiddleware._global_crew is None:
                    try:
                        from agents.nir_analysis_crew import NIRAnalysisCrew, CrewConfiguration
                        
                        # Create configuration with middleware settings
                        config = CrewConfiguration(
                            enable_crewai=True,
                            enable_federated_learning=True,
                            default_analysis_mode='standard',
                            default_privacy_level='local_only',
                            default_report_type='comprehensive',
                            default_report_format='html',
                            max_batch_size=10,
                            temp_dir=str(Path(settings.BASE_DIR) / "temp" / "crewai"),
                            output_dir=str(Path(settings.BASE_DIR) / "output" / "analysis")
                        )
                        
                        # Create global Crew AI instance
                        CrewAIMiddleware._global_crew = NIRAnalysisCrew(config)
                        logger.info("✅ Global Crew AI instance created with middleware configuration")
                        
                    except ImportError as e:
                        logger.warning(f"Could not initialize Crew AI: {e}")
                        CrewAIMiddleware._global_crew = None
                    except Exception as e:
                        logger.error(f"❌ Error initializing Crew AI: {e}")
                        CrewAIMiddleware._global_crew = None
    
    def _get_crewai_instance(self) -> Optional[Any]:
        """Get or create Crew AI instance for current thread"""
        # Check if we have a thread-local instance
        if not hasattr(self._thread_local, 'crew_instance'):
            # Use global instance if available
            if CrewAIMiddleware._global_crew is not None:
                self._thread_local.crew_instance = CrewAIMiddleware._global_crew
            else:
                # Try to create a new instance
                try:
                    from agents.nir_analysis_crew import NIRAnalysisCrew
                    self._thread_local.crew_instance = NIRAnalysisCrew()
                    logger.debug("✅ Thread-local Crew AI instance created")
                except ImportError as e:
                    logger.warning(f"Could not create Crew AI instance: {e}")
                    self._thread_local.crew_instance = None
        
        return getattr(self._thread_local, 'crew_instance', None)
    
    def _add_to_task_queue(self, task_data: Dict[str, Any]) -> str:
        """Add a task to the background processing queue"""
        task_id = f"task_{int(time.time() * 1000)}_{len(self._task_queue)}"
        task_data['task_id'] = task_id
        task_data['status'] = 'queued'
        task_data['created_at'] = time.time()
        
        with self._task_queue_lock:
            self._task_queue.append(task_data)
            logger.info(f"✅ Task {task_id} added to queue")
        
        return task_id
    
    def _get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task in the queue"""
        with self._task_queue_lock:
            for task in self._task_queue:
                if task.get('task_id') == task_id:
                    return task.copy()
        return None
    
    def _update_task_status(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None) -> bool:
        """Update the status of a task in the queue"""
        with self._task_queue_lock:
            for i, task in enumerate(self._task_queue):
                if task.get('task_id') == task_id:
                    self._task_queue[i]['status'] = status
                    self._task_queue[i]['updated_at'] = time.time()
                    if result:
                        self._task_queue[i]['result'] = result
                    logger.info(f"✅ Task {task_id} status updated to {status}")
                    return True
        return False
    
    def _cache_result(self, cache_key: str, result: Any) -> bool:
        """Cache a result with the configured timeout"""
        try:
            cache_key = f"{self.CACHE_PREFIX}{cache_key}"
            cache.set(cache_key, result, self.CACHE_TIMEOUT)
            logger.debug(f"✅ Result cached with key: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to cache result: {e}")
            return False
    
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get a cached result"""
        try:
            cache_key = f"{self.CACHE_PREFIX}{cache_key}"
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"✅ Cache hit for key: {cache_key}")
            return result
        except Exception as e:
            logger.error(f"❌ Failed to get cached result: {e}")
            return None
    
    def _cleanup_old_tasks(self, max_age: int = 3600) -> int:
        """Clean up old tasks from the queue"""
        current_time = time.time()
        removed_count = 0
        
        with self._task_queue_lock:
            self._task_queue = [
                task for task in self._task_queue
                if (current_time - task.get('created_at', current_time)) <= max_age
            ]
            removed_count = len(self._task_queue) - len(self._task_queue)
            logger.info(f"✅ Cleaned up {removed_count} old tasks from queue")
        
        return removed_count
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Process request and add Crew AI context"""
        try:
            # Get Crew AI instance for this request
            crew_instance = self._get_crewai_instance()
            
            if crew_instance is not None:
                # Add Crew AI to request context
                request.crewai = {
                    'crew': crew_instance,
                    'agents': {
                        'spectral': crew_instance.spectral_agent,
                        'metadata': crew_instance.metadata_agent,
                        'reporting': crew_instance.reporting_agent,
                        'calibration': crew_instance.calibration_agent,
                        'flower': crew_instance.flower_agent,
                    },
                    'config': crew_instance.config,
                    'analysis_history': crew_instance.analysis_history,
                    'task_queue': {
                        'add_task': self._add_to_task_queue,
                        'get_status': self._get_task_status,
                        'update_status': self._update_task_status,
                        'cleanup': self._cleanup_old_tasks,
                    },
                    'cache': {
                        'set': self._cache_result,
                        'get': self._get_cached_result,
                        'timeout': self.CACHE_TIMEOUT,
                    },
                    'middleware': self
                }
                
                logger.debug(f"✅ Crew AI context added to request: {request.path}")
            else:
                logger.warning(f"⚠️ No Crew AI instance available for request: {request.path}")
                
        except Exception as e:
            logger.error(f"❌ Error processing Crew AI request: {e}")
            # Don't fail the request, just continue without Crew AI
            
        # Continue processing the request
        return None
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Process response and cleanup Crew AI resources"""
        try:
            # Clean up thread-local resources if needed
            if hasattr(self._thread_local, 'crew_instance'):
                # For now, we don't cleanup the global instance
                # In future, we might want to implement cleanup logic
                pass
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up Crew AI resources: {e}")
            
        return response
    
    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse:
        """Handle exceptions and ensure Crew AI resources are cleaned up"""
        try:
            logger.error(f"❌ Exception in request {request.path}: {exception}")
            
            # Clean up any Crew AI resources
            if hasattr(self._thread_local, 'crew_instance'):
                delattr(self._thread_local, 'crew_instance')
                
        except Exception as cleanup_error:
            logger.error(f"❌ Error during Crew AI cleanup: {cleanup_error}")
            
        # Re-raise the original exception
        raise exception
    
    @classmethod
    def get_crewai(cls) -> Optional[Any]:
        """Get the global Crew AI instance"""
        return cls._global_crew
    
    @classmethod
    def reset_crewai(cls):
        """Reset the global Crew AI instance (for testing)"""
        with cls._global_lock:
            cls._global_crew = None
            logger.info("✅ Global Crew AI instance reset")


class CrewAIContextManager:
    """
    Context manager for Crew AI operations within views.
    
    Usage:
        with CrewAIContextManager(request) as crewai:
            # Use crewai.crew for Crew AI operations
            result = crewai.crew.execute_analysis(request.data)
    """
    
    def __init__(self, request: HttpRequest):
        self.request = request
        self.crew_instance = None
    
    def __enter__(self):
        """Enter the context and initialize Crew AI"""
        # Get Crew AI instance from request or create new one
        if hasattr(self.request, 'crewai') and self.request.crewai.get('crew'):
            self.crew_instance = self.request.crewai['crew']
        else:
            # Create new instance for this context
            try:
                from agents.nir_analysis_crew import NIRAnalysisCrew
                self.crew_instance = NIRAnalysisCrew()
            except ImportError as e:
                logger.warning(f"Could not create Crew AI instance: {e}")
                self.crew_instance = None
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and cleanup resources"""
        # For now, we don't cleanup the Crew AI instance
        # as it might be reused for other requests
        pass
    
    @property
    def crew(self):
        """Get the Crew AI instance"""
        return self.crew_instance
    
    @property
    def agents(self) -> Dict[str, Any]:
        """Get all Crew AI agents"""
        if self.crew_instance is None:
            return {}
        
        return {
            'spectral': self.crew_instance.spectral_agent,
            'metadata': self.crew_instance.metadata_agent,
            'reporting': self.crew_instance.reporting_agent,
            'calibration': self.crew_instance.calibration_agent,
            'flower': self.crew_instance.flower_agent,
        }


# Utility functions for Crew AI integration

def get_crewai_from_request(request: HttpRequest) -> Optional[Any]:
    """Get Crew AI instance from request"""
    if hasattr(request, 'crewai') and request.crewai.get('crew'):
        return request.crewai['crew']
    return None


def ensure_crewai_available() -> bool:
    """Ensure Crew AI is available in the current environment"""
    try:
        from agents.nir_analysis_crew import NIRAnalysisCrew
        return True
    except ImportError:
        return False


def get_crewai_status() -> Dict[str, Any]:
    """Get the current status of Crew AI middleware"""
    global_crew = CrewAIMiddleware.get_crewai()
    
    status = {
        'available': global_crew is not None,
        'task_queue_size': len(CrewAIMiddleware._task_queue),
        'cache_timeout': CrewAIMiddleware.CACHE_TIMEOUT,
        'agents_available': {}
    }
    
    if global_crew is not None:
        status['agents_available'] = {
            'spectral': global_crew.spectral_agent is not None,
            'metadata': global_crew.metadata_agent is not None,
            'reporting': global_crew.reporting_agent is not None,
            'calibration': global_crew.calibration_agent is not None,
            'flower': global_crew.flower_agent is not None,
        }
        status['analysis_history_count'] = len(global_crew.analysis_history)
        status['config'] = {
            'enable_crewai': global_crew.config.enable_crewai,
            'enable_federated_learning': global_crew.config.enable_federated_learning,
            'default_analysis_mode': global_crew.config.default_analysis_mode.value,
            'default_privacy_level': global_crew.config.default_privacy_level.value,
        }
    
    return status


def cleanup_crewai_resources(max_age: int = 3600) -> Dict[str, Any]:
    """Clean up Crew AI resources including task queue and cache"""
    middleware_instance = CrewAIMiddleware(None)
    
    # Clean up task queue
    removed_tasks = middleware_instance._cleanup_old_tasks(max_age)
    
    # Clean up cache - this would need to be implemented based on your cache backend
    # For now, we'll just return the task cleanup results
    
    return {
        'tasks_removed': removed_tasks,
        'message': f'Cleaned up {removed_tasks} old tasks from queue'
    }