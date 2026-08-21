#!/usr/bin/env python3
"""
DeveloperAgent Framework - Development Server

Provides a development server with hot-reload for testing agents.
"""

import os
import sys
import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import importlib
import traceback

logger = logging.getLogger('DevelopmentServer')


class AgentHandler:
    """Handles agent execution and management"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.agents_dir = self.project_root / 'agents'
        self.agents = {}
        self.loaded_agents = set()
        
    def load_agent(self, agent_name: str) -> bool:
        """Load an agent dynamically"""
        snake_name = self._to_snake_case(agent_name)
        
        if agent_name in self.agents:
            return True
        
        try:
            # Add agents directory to path
            if str(self.agents_dir) not in sys.path:
                sys.path.insert(0, str(self.agents_dir))
            
            # Import the agent module
            module_name = f"{snake_name}"
            module = importlib.import_module(f"agents.{module_name}")
            
            # Get the agent class
            agent_class = getattr(module, agent_name)
            
            # Create instance
            agent = agent_class()
            agent.initialize()
            
            self.agents[agent_name] = agent
            self.loaded_agents.add(agent_name)
            
            logger.info(f"Loaded agent: {agent_name}")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import agent {agent_name}: {str(e)}")
            return False
        except AttributeError as e:
            logger.error(f"Agent class {agent_name} not found: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to load agent {agent_name}: {str(e)}")
            traceback.print_exc()
            return False
    
    def load_all_agents(self) -> Dict[str, bool]:
        """Load all available agents"""
        results = {}
        
        # Find all agent files
        agent_files = list(self.agents_dir.glob('*_agent.py'))
        
        for agent_file in agent_files:
            # Extract agent name from filename
            agent_name = agent_file.stem.replace('_agent', '')
            # Convert snake_case to CamelCase
            agent_name = ''.join(word.capitalize() for word in agent_name.split('_')) + 'Agent'
            
            results[agent_name] = self.load_agent(agent_name)
        
        return results
    
    def unload_agent(self, agent_name: str) -> bool:
        """Unload an agent"""
        if agent_name in self.agents:
            del self.agents[agent_name]
            self.loaded_agents.discard(agent_name)
            logger.info(f"Unloaded agent: {agent_name}")
            return True
        return False
    
    def unload_all_agents(self) -> None:
        """Unload all agents"""
        for agent_name in list(self.agents.keys()):
            self.unload_agent(agent_name)
    
    def execute_agent(self, agent_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an agent"""
        if agent_name not in self.agents:
            if not self.load_agent(agent_name):
                return {
                    'success': False,
                    'error': f"Failed to load agent: {agent_name}"
                }
        
        try:
            agent = self.agents[agent_name]
            output = agent.execute(context)
            
            return {
                'success': True,
                'agent_name': agent_name,
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
                ]
            }
            
        except Exception as e:
            logger.error(f"Error executing agent {agent_name}: {str(e)}")
            traceback.print_exc()
            return {
                'success': False,
                'agent_name': agent_name,
                'error': str(e)
            }
    
    def get_agent_info(self, agent_name: str) -> Dict[str, Any]:
        """Get information about an agent"""
        if agent_name not in self.agents:
            if not self.load_agent(agent_name):
                return {
                    'success': False,
                    'error': f"Failed to load agent: {agent_name}"
                }
        
        agent = self.agents[agent_name]
        
        return {
            'success': True,
            'name': agent.name,
            'version': agent.version,
            'status': agent.status.name if hasattr(agent.status, 'name') else str(agent.status),
            'dependencies': agent.dependencies,
            'errors': len(agent.errors)
        }
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all available agents"""
        agents = []
        
        # Find all agent files
        agent_files = list(self.agents_dir.glob('*_agent.py'))
        
        for agent_file in agent_files:
            # Extract agent name from filename
            agent_name = agent_file.stem.replace('_agent', '')
            # Convert snake_case to CamelCase
            agent_name = ''.join(word.capitalize() for word in agent_name.split('_')) + 'Agent'
            
            agents.append({
                'name': agent_name,
                'file': str(agent_file.relative_to(self.project_root)),
                'loaded': agent_name in self.loaded_agents
            })
        
        return agents
    
    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case"""
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
        return name.lower()


class FileWatcher:
    """Watches files for changes and triggers callbacks"""
    
    def __init__(self, paths: List[Path], callback: Callable, interval: float = 1.0):
        self.paths = paths
        self.callback = callback
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread = None
        self._file_mod_times = {}
        
    def start(self):
        """Start watching files"""
        # Record initial modification times
        for path in self.paths:
            if path.exists():
                if path.is_dir():
                    for file in path.rglob('*.py'):
                        self._file_mod_times[str(file)] = file.stat().st_mtime
                else:
                    self._file_mod_times[str(path)] = path.stat().st_mtime
        
        # Start watch thread
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        """Stop watching files"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
    
    def _watch_loop(self):
        """Main watch loop"""
        while not self._stop_event.is_set():
            time.sleep(self.interval)
            
            changed_files = []
            
            for path in self.paths:
                if path.exists():
                    if path.is_dir():
                        for file in path.rglob('*.py'):
                            file_str = str(file)
                            current_mtime = file.stat().st_mtime
                            if file_str in self._file_mod_times:
                                if current_mtime > self._file_mod_times[file_str]:
                                    changed_files.append(file_str)
                                    self._file_mod_times[file_str] = current_mtime
                            else:
                                self._file_mod_times[file_str] = current_mtime
                    else:
                        file_str = str(path)
                        current_mtime = path.stat().st_mtime
                        if file_str in self._file_mod_times:
                            if current_mtime > self._file_mod_times[file_str]:
                                changed_files.append(file_str)
                                self._file_mod_times[file_str] = current_mtime
                        else:
                            self._file_mod_times[file_str] = current_mtime
            
            if changed_files:
                logger.info(f"Detected changes in: {', '.join(changed_files)}")
                self.callback(changed_files)


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for development server"""
    
    # Class-level agent handler
    agent_handler = None
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            self._handle_get()
        except Exception as e:
            self._send_error(500, f"Server error: {str(e)}")
    
    def do_POST(self):
        """Handle POST requests"""
        try:
            self._handle_post()
        except Exception as e:
            self._send_error(500, f"Server error: {str(e)}")
    
    def _handle_get(self):
        """Handle GET requests"""
        path = self.path.strip('/')
        
        if not path or path == '':
            self._send_index()
        elif path == 'agents':
            self._send_agent_list()
        elif path.startswith('agents/'):
            agent_name = path.replace('agents/', '')
            self._send_agent_info(agent_name)
        elif path == 'health':
            self._send_health_check()
        else:
            self._send_error(404, f"Not found: {path}")
    
    def _handle_post(self):
        """Handle POST requests"""
        path = self.path.strip('/')
        
        if path.startswith('agents/'):
            agent_name = path.replace('agents/', '')
            self._execute_agent(agent_name)
        else:
            self._send_error(404, f"Not found: {path}")
    
    def _send_index(self):
        """Send index page"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>NIR Intelligence Platform - Development Server</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #333; }
                .agent-list { margin: 20px 0; }
                .agent-item { padding: 10px; border: 1px solid #ddd; margin: 5px 0; border-radius: 5px; }
                .agent-item.loaded { background: #e8f5e9; }
                .agent-item a { text-decoration: none; color: #333; }
                .agent-item a:hover { text-decoration: underline; }
                .actions { margin: 20px 0; }
                .actions a { margin-right: 10px; }
            </style>
        </head>
        <body>
            <h1>NIR Intelligence Platform - Development Server</h1>
            <p>Welcome to the development server for testing NIR agents.</p>
            
            <div class="actions">
                <a href="/agents">List All Agents</a>
                <a href="/health">Health Check</a>
            </div>
            
            <div class="agent-list">
                <h2>Available Endpoints</h2>
                <ul>
                    <li><code>GET /agents</code> - List all available agents</li>
                    <li><code>GET /agents/{agent_name}</code> - Get info about a specific agent</li>
                    <li><code>POST /agents/{agent_name}</code> - Execute a specific agent</li>
                    <li><code>GET /health</code> - Health check</li>
                </ul>
            </div>
        </body>
        </html>
        """
        self._send_response(200, html, content_type='text/html')
    
    def _send_agent_list(self):
        """Send list of agents"""
        if not self.agent_handler:
            self._send_error(500, "Agent handler not initialized")
            return
        
        agents = self.agent_handler.list_agents()
        
        # Send as JSON
        self._send_response(200, json.dumps(agents, indent=2), content_type='application/json')
    
    def _send_agent_info(self, agent_name: str):
        """Send information about a specific agent"""
        if not self.agent_handler:
            self._send_error(500, "Agent handler not initialized")
            return
        
        result = self.agent_handler.get_agent_info(agent_name)
        
        if not result.get('success', False):
            self._send_error(404, result.get('error', 'Agent not found'))
            return
        
        self._send_response(200, json.dumps(result, indent=2), content_type='application/json')
    
    def _execute_agent(self, agent_name: str):
        """Execute a specific agent"""
        if not self.agent_handler:
            self._send_error(500, "Agent handler not initialized")
            return
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            try:
                context = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                context = {}
        else:
            context = {}
        
        result = self.agent_handler.execute_agent(agent_name, context)
        
        if not result.get('success', False):
            self._send_error(400, result.get('error', 'Execution failed'))
            return
        
        self._send_response(200, json.dumps(result, indent=2), content_type='application/json')
    
    def _send_health_check(self):
        """Send health check response"""
        health = {
            'status': 'healthy',
            'agents_loaded': len(self.agent_handler.agents) if self.agent_handler else 0,
            'timestamp': time.time()
        }
        self._send_response(200, json.dumps(health, indent=2), content_type='application/json')
    
    def _send_response(self, status_code: int, content: str, content_type: str = 'text/plain'):
        """Send HTTP response"""
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
    
    def _send_error(self, status_code: int, message: str):
        """Send error response"""
        error_response = {
            'error': message,
            'status_code': status_code
        }
        self._send_response(status_code, json.dumps(error_response, indent=2), 'application/json')


class DevelopmentServer:
    """Development server for testing agents"""
    
    def __init__(self, port: int = 8001, host: str = 'localhost', hot_reload: bool = True):
        self.port = port
        self.host = host
        self.hot_reload = hot_reload
        self.server = None
        self.agent_handler = AgentHandler()
        self.file_watcher = None
        
        # Set up request handler
        RequestHandler.agent_handler = self.agent_handler
    
    def start(self):
        """Start the development server"""
        logger.info(f"Starting development server on {self.host}:{self.port}")
        
        # Load all agents initially
        load_results = self.agent_handler.load_all_agents()
        loaded_count = sum(1 for success in load_results.values() if success)
        logger.info(f"Loaded {loaded_count}/{len(load_results)} agents")
        
        # Set up file watching for hot reload
        if self.hot_reload:
            self._setup_file_watching()
        
        # Create and start server
        self.server = socketserver.TCPServer((self.host, self.port), RequestHandler)
        
        logger.info(f"Server started at http://{self.host}:{self.port}")
        logger.info("Press Ctrl+C to stop")
        
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        finally:
            self.stop()
    
    def _setup_file_watching(self):
        """Set up file watching for hot reload"""
        # Watch agents directory and dev_framework
        watch_paths = [
            self.agent_handler.agents_dir,
            Path(__file__).parent  # dev_framework directory
        ]
        
        self.file_watcher = FileWatcher(
            paths=watch_paths,
            callback=self._on_file_change,
            interval=1.0
        )
        self.file_watcher.start()
    
    def _on_file_change(self, changed_files: List[str]):
        """Handle file changes"""
        logger.info(f"Files changed: {changed_files}")
        
        # Reload all agents
        self.agent_handler.unload_all_agents()
        load_results = self.agent_handler.load_all_agents()
        loaded_count = sum(1 for success in load_results.values() if success)
        logger.info(f"Reloaded {loaded_count}/{len(load_results)} agents")
    
    def serve_agent(self, agent_name: str):
        """Serve a specific agent in isolation"""
        logger.info(f"Serving agent: {agent_name}")
        
        # Load the specific agent
        if not self.agent_handler.load_agent(agent_name):
            logger.error(f"Failed to load agent: {agent_name}")
            return
        
        # Start server
        self.start()
    
    def serve_all(self):
        """Serve all agents"""
        self.start()
    
    def stop(self):
        """Stop the server"""
        if self.file_watcher:
            self.file_watcher.stop()
        
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        
        self.agent_handler.unload_all_agents()
        logger.info("Server stopped")


# Import time at the end to avoid issues
import time
