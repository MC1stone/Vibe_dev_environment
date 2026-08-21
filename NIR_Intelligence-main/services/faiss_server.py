#!/usr/bin/env python3
"""
Faiss Similarity Search Server for NIR_MISTRAL
Provides HTTP API for vector similarity search operations
"""

import os
import json
import numpy as np
import faiss
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('faiss_server')

class FaissIndexManager:
    """Manages Faiss indexes for spectral data"""
    
    def __init__(self, index_path='/app/index', dimension=100):
        self.index_path = index_path
        self.dimension = dimension
        self.indexes = {}
        self.locks = {}
        self._ensure_index_directory()
        
    def _ensure_index_directory(self):
        """Ensure the index directory exists"""
        os.makedirs(self.index_path, exist_ok=True)
        
    def get_index(self, index_name='spectral'):
        """Get or create a Faiss index"""
        if index_name not in self.indexes:
            with threading.Lock():
                if index_name not in self.indexes:
                    index_file = os.path.join(self.index_path, f'{index_name}.index')
                    if os.path.exists(index_file):
                        logger.info(f"Loading existing index: {index_name}")
                        self.indexes[index_name] = faiss.read_index(index_file)
                    else:
                        logger.info(f"Creating new index: {index_name}")
                        self.indexes[index_name] = faiss.IndexFlatL2(self.dimension)
                    self.locks[index_name] = threading.Lock()
        return self.indexes[index_name], self.locks[index_name]
    
    def add_vectors(self, index_name, vectors, ids=None):
        """Add vectors to an index"""
        index, lock = self.get_index(index_name)
        
        vectors = np.array(vectors, dtype=np.float32)
        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Vectors must have dimension {self.dimension}, got {vectors.shape[1]}")
        
        with lock:
            if ids is not None:
                ids = np.array(ids, dtype=np.int64)
                if not index.is_trained:
                    index.add(vectors)
                else:
                    index.add_with_ids(vectors, ids)
            else:
                index.add(vectors)
            
            # Save the index
            index_file = os.path.join(self.index_path, f'{index_name}.index')
            faiss.write_index(index, index_file)
            logger.info(f"Added {len(vectors)} vectors to index {index_name}")
    
    def search(self, index_name, query_vector, k=10):
        """Search for similar vectors"""
        index, lock = self.get_index(index_name)
        
        query_vector = np.array(query_vector, dtype=np.float32).reshape(1, -1)
        if query_vector.shape[1] != self.dimension:
            raise ValueError(f"Query vector must have dimension {self.dimension}, got {query_vector.shape[1]}")
        
        with lock:
            distances, indices = index.search(query_vector, k)
            return distances[0].tolist(), indices[0].tolist()
    
    def get_index_info(self, index_name):
        """Get information about an index"""
        index, _ = self.get_index(index_name)
        return {
            'name': index_name,
            'dimension': index.d,
            'ntotal': index.ntotal,
            'is_trained': index.is_trained
        }

class FaissHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Faiss operations"""
    
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
        query_params = parse_qs(parsed_url.query)
        
        try:
            if path == '/health':
                self._send_json_response(200, {'status': 'healthy', 'service': 'faiss'})
                
            elif path == '/indexes':
                indexes = list(faiss_manager.indexes.keys())
                self._send_json_response(200, {'indexes': indexes})
                
            elif path.startswith('/index/'):
                index_name = path.split('/')[2]
                if index_name in faiss_manager.indexes:
                    info = faiss_manager.get_index_info(index_name)
                    self._send_json_response(200, info)
                else:
                    self._send_error_response(404, f'Index {index_name} not found')
                    
            elif path == '/search':
                index_name = query_params.get('index', ['spectral'])[0]
                k = int(query_params.get('k', ['10'])[0])
                
                # For GET requests, expect query vector in query params
                # This is not ideal for large vectors, but works for testing
                vector_str = query_params.get('vector', [None])[0]
                if vector_str:
                    vector = [float(x) for x in vector_str.split(',')]
                    distances, indices = faiss_manager.search(index_name, vector, k)
                    self._send_json_response(200, {
                        'distances': distances,
                        'indices': indices
                    })
                else:
                    self._send_error_response(400, 'Query vector required')
                    
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
            if path.startswith('/index/'):
                index_name = path.split('/')[2]
                
                # Read request body
                content_length = int(self.headers.get('Content-Length', 0))
                request_body = self.rfile.read(content_length)
                data = json.loads(request_body.decode('utf-8'))
                
                if 'vectors' in data:
                    vectors = data['vectors']
                    ids = data.get('ids')
                    faiss_manager.add_vectors(index_name, vectors, ids)
                    self._send_json_response(200, {
                        'status': 'success',
                        'index': index_name,
                        'vectors_added': len(vectors)
                    })
                else:
                    self._send_error_response(400, 'Vectors required in request body')
                    
            elif path == '/search':
                content_length = int(self.headers.get('Content-Length', 0))
                request_body = self.rfile.read(content_length)
                data = json.loads(request_body.decode('utf-8'))
                
                index_name = data.get('index', 'spectral')
                query_vector = data.get('vector')
                k = data.get('k', 10)
                
                if query_vector and isinstance(query_vector, list):
                    distances, indices = faiss_manager.search(index_name, query_vector, k)
                    self._send_json_response(200, {
                        'distances': distances,
                        'indices': indices
                    })
                else:
                    self._send_error_response(400, 'Query vector required in request body')
                    
            else:
                self._send_error_response(404, 'Endpoint not found')
                
        except Exception as e:
            logger.error(f"Error in POST {path}: {str(e)}")
            self._send_error_response(500, str(e))
    
    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        try:
            if path.startswith('/index/'):
                index_name = path.split('/')[2]
                if index_name in faiss_manager.indexes:
                    del faiss_manager.indexes[index_name]
                    index_file = os.path.join(faiss_manager.index_path, f'{index_name}.index')
                    if os.path.exists(index_file):
                        os.remove(index_file)
                    self._send_json_response(200, {
                        'status': 'success',
                        'index': index_name,
                        'message': 'Index deleted'
                    })
                else:
                    self._send_error_response(404, f'Index {index_name} not found')
            else:
                self._send_error_response(404, 'Endpoint not found')
                
        except Exception as e:
            logger.error(f"Error in DELETE {path}: {str(e)}")
            self._send_error_response(500, str(e))

def run_server(port=8081, dimension=100):
    """Run the Faiss HTTP server"""
    global faiss_manager
    
    # Initialize Faiss manager
    faiss_manager = FaissIndexManager(dimension=dimension)
    
    # Start HTTP server
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, FaissHTTPHandler)
    
    logger.info(f"Starting Faiss server on port {port}")
    logger.info(f"Index directory: {faiss_manager.index_path}")
    logger.info(f"Vector dimension: {dimension}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down Faiss server")
        httpd.server_close()

if __name__ == '__main__':
    # Get configuration from environment
    port = int(os.getenv('FAISS_PORT', '8081'))
    dimension = int(os.getenv('FAISS_DIMENSION', '100'))
    index_path = os.getenv('FAISS_INDEX_PATH', '/app/index')
    
    # Update Faiss manager configuration
    faiss_manager = FaissIndexManager(index_path=index_path, dimension=dimension)
    
    run_server(port=port, dimension=dimension)