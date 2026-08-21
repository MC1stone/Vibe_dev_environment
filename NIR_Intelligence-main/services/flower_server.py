#!/usr/bin/env python3
"""
Flower Federated Learning Server for NIR_MISTRAL
Implements the Flower framework for distributed model training
"""

import os
import json
import numpy as np
from typing import List, Tuple, Dict, Any
import flwr as fl
from flwr.common import Metrics
from flwr.server.strategy import FedAvg, FedProx
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('flower_server')

class NirFlowerClient(fl.client.NumPyClient):
    """Custom Flower client for NIR spectroscopy"""
    
    def __init__(self, model, x_train, y_train, x_test, y_test):
        self.model = model
        self.x_train, self.y_train = x_train, y_train
        self.x_test, self.y_test = x_test, y_test
    
    def get_parameters(self, config):
        """Get model parameters"""
        return self.model.get_weights()
    
    def fit(self, parameters, config):
        """Train model on local data"""
        self.model.set_weights(parameters)
        
        # Train model (simplified example)
        # In practice, this would use your actual training logic
        batch_size = config.get('batch_size', 32)
        epochs = config.get('epochs', 1)
        
        # Simulate training
        history = self.model.fit(
            self.x_train, self.y_train,
            batch_size=batch_size,
            epochs=epochs,
            validation_data=(self.x_test, self.y_test),
            verbose=0
        )
        
        # Return updated parameters and metrics
        parameters = self.model.get_weights()
        metrics = {
            'loss': history.history['loss'][-1],
            'val_loss': history.history['val_loss'][-1] if 'val_loss' in history.history else 0,
            'num_examples': len(self.x_train)
        }
        
        return parameters, len(self.x_train), metrics
    
    def evaluate(self, parameters, config):
        """Evaluate model on local test data"""
        self.model.set_weights(parameters)
        
        # Evaluate model
        loss, accuracy = self.model.evaluate(self.x_test, self.y_test, verbose=0)
        
        return loss, len(self.x_test), {"loss": loss, "accuracy": accuracy}

class FlowerServerManager:
    """Manages Flower federated learning server"""
    
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.server = None
        self.strategy = None
        self.clients = {}
        self.models = {}
        self.is_running = False
        
    def start_server(self, strategy_type='fedavg', **strategy_kwargs):
        """Start the Flower server with specified strategy"""
        
        # Select strategy based on type
        if strategy_type.lower() == 'fedavg':
            self.strategy = FedAvg(
                min_available_clients=2,
                **strategy_kwargs
            )
        elif strategy_type.lower() == 'fedprox':
            self.strategy = FedProx(
                min_available_clients=2,
                proximal_mu=0.1,
                **strategy_kwargs
            )
        else:
            self.strategy = FedAvg(min_available_clients=2)
        
        # Start Flower server
        self.server = fl.server.ServerApp(
            server_address=f"{self.host}:{self.port}",
            config=fl.server.ServerConfig(num_rounds=10),
            strategy=self.strategy
        )
        
        # Start server in a separate thread
        server_thread = threading.Thread(target=self.server.run)
        server_thread.daemon = True
        server_thread.start()
        
        self.is_running = True
        logger.info(f"Flower server started on {self.host}:{self.port}")
        logger.info(f"Using strategy: {strategy_type}")
        
        return server_thread
    
    def stop_server(self):
        """Stop the Flower server"""
        if self.server:
            self.server.shutdown()
            self.is_running = False
            logger.info("Flower server stopped")
    
    def register_client(self, client_id, client_config):
        """Register a new client"""
        self.clients[client_id] = client_config
        logger.info(f"Client registered: {client_id}")
    
    def unregister_client(self, client_id):
        """Unregister a client"""
        if client_id in self.clients:
            del self.clients[client_id]
            logger.info(f"Client unregistered: {client_id}")
    
    def get_server_status(self):
        """Get server status"""
        return {
            'is_running': self.is_running,
            'host': self.host,
            'port': self.port,
            'strategy': str(self.strategy.__class__.__name__),
            'num_clients': len(self.clients),
            'client_ids': list(self.clients.keys())
        }

class FlowerHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Flower server operations"""
    
    def log_message(self, format, *args):
        logger.info("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))
    
    def _send_json_response(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _send_error_response(self, status_code, message):
        """Send error response"""
        self._send_json_response(status_code, {'error': message})
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        try:
            if path == '/health':
                self._send_json_response(200, {
                    'status': 'healthy',
                    'service': 'flower',
                    'server_status': flower_manager.get_server_status()
                })
                
            elif path == '/status':
                status = flower_manager.get_server_status()
                self._send_json_response(200, status)
                
            elif path == '/clients':
                self._send_json_response(200, {
                    'clients': list(flower_manager.clients.keys()),
                    'count': len(flower_manager.clients)
                })
                
            else:
                self._send_error_response(404, 'Endpoint not found')
                
        except Exception as e:
            logger.error(f"Error in GET {path}: {str(e)}")
            self._send_error_response(500, str(e))
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        try:
            if path == '/start':
                content_length = int(self.headers.get('Content-Length', 0))
                request_body = self.rfile.read(content_length)
                data = json.loads(request_body.decode('utf-8'))
                
                strategy_type = data.get('strategy', 'fedavg')
                strategy_config = data.get('config', {})
                
                flower_manager.start_server(strategy_type, **strategy_config)
                self._send_json_response(200, {
                    'status': 'started',
                    'strategy': strategy_type,
                    'config': strategy_config
                })
                
            elif path == '/stop':
                flower_manager.stop_server()
                self._send_json_response(200, {'status': 'stopped'})
                
            elif path == '/register':
                content_length = int(self.headers.get('Content-Length', 0))
                request_body = self.rfile.read(content_length)
                data = json.loads(request_body.decode('utf-8'))
                
                client_id = data.get('client_id')
                client_config = data.get('config', {})
                
                if client_id:
                    flower_manager.register_client(client_id, client_config)
                    self._send_json_response(200, {
                        'status': 'registered',
                        'client_id': client_id
                    })
                else:
                    self._send_error_response(400, 'client_id required')
                    
            elif path == '/unregister':
                content_length = int(self.headers.get('Content-Length', 0))
                request_body = self.rfile.read(content_length)
                data = json.loads(request_body.decode('utf-8'))
                
                client_id = data.get('client_id')
                if client_id:
                    flower_manager.unregister_client(client_id)
                    self._send_json_response(200, {
                        'status': 'unregistered',
                        'client_id': client_id
                    })
                else:
                    self._send_error_response(400, 'client_id required')
                    
            else:
                self._send_error_response(404, 'Endpoint not found')
                
        except Exception as e:
            logger.error(f"Error in POST {path}: {str(e)}")
            self._send_error_response(500, str(e))

def run_flower_server(host='0.0.0.0', port=5555, http_port=5556):
    """Run the Flower server with HTTP management interface"""
    global flower_manager
    
    # Initialize Flower manager
    flower_manager = FlowerServerManager(host=host, port=port)
    
    # Start Flower server with default strategy
    flower_manager.start_server(strategy_type='fedavg')
    
    # Start HTTP management server
    http_server_address = (host, http_port)
    httpd = HTTPServer(http_server_address, FlowerHTTPHandler)
    
    logger.info(f"Starting Flower server on {host}:{port}")
    logger.info(f"Starting HTTP management interface on {host}:{http_port}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down Flower server")
        flower_manager.stop_server()
        httpd.server_close()

if __name__ == '__main__':
    # Get configuration from environment
    host = os.getenv('FLOWER_SERVER_HOST', '0.0.0.0')
    port = int(os.getenv('FLOWER_SERVER_PORT', '5555'))
    http_port = int(os.getenv('FLOWER_HTTP_PORT', '5556'))
    
    run_flower_server(host=host, port=port, http_port=http_port)