#!/usr/bin/env python3

"""
Mock ILIAS Server for NIR Intelligence Platform Testing
This simulates the ILIAS e-learning platform API for development and testing
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs
import threading
import time

class MockILIASRequestHandler(BaseHTTPRequestHandler):
    # Mock database
    users = {}
    courses = {
        'NIR_101': {
            'id': 'NIR_101',
            'title': 'Introduction to NIR Spectroscopy',
            'description': 'Fundamentals and basic concepts of NIR spectroscopy',
            'is_active': True,
            'enrolled_users': []
        },
        'NIR_201': {
            'id': 'NIR_201',
            'title': 'Advanced NIR Data Analysis',
            'description': 'Statistical and machine learning approaches for NIR data',
            'is_active': True,
            'enrolled_users': []
        },
        'NIR_PLATFORM': {
            'id': 'NIR_PLATFORM',
            'title': 'NIR Platform Training',
            'description': 'Platform-specific training materials and tutorials',
            'is_active': True,
            'enrolled_users': []
        }
    }
    
    messages = []
    message_id_counter = 1
    
    def _set_headers(self, status_code=200, content_type='application/json'):
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.end_headers()
    
    def _send_json_response(self, data, status_code=200):
        self._set_headers(status_code)
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
    
    def _send_error_response(self, message, status_code=400):
        self._send_json_response({'error': message}, status_code)
    
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        print(f"GET {path}")
        
        try:
            if path == '/api/health':
                self._send_json_response({
                    'status': 'healthy',
                    'service': 'ILIAS Mock Server',
                    'version': '1.0.0',
                    'timestamp': int(time.time())
                })
                
            elif path == '/api/users':
                self._send_json_response({
                    'users': list(self.users.values()),
                    'count': len(self.users)
                })
                
            elif path.startswith('/api/users/'):
                user_id = path.split('/')[-1]
                if user_id in self.users:
                    self._send_json_response(self.users[user_id])
                else:
                    self._send_error_response('User not found', 404)
                    
            elif path == '/api/courses':
                self._send_json_response({
                    'courses': list(self.courses.values()),
                    'count': len(self.courses)
                })
                
            elif path.startswith('/api/courses/'):
                course_id = path.split('/')[-1]
                if course_id in self.courses:
                    self._send_json_response(self.courses[course_id])
                else:
                    self._send_error_response('Course not found', 404)
                    
            elif path == '/api/messages':
                user_id = query_params.get('user_id', [None])[0]
                if user_id:
                    user_messages = [msg for msg in self.messages if msg['recipient_id'] == user_id]
                    self._send_json_response({
                        'messages': user_messages,
                        'count': len(user_messages)
                    })
                else:
                    self._send_json_response({
                        'messages': self.messages,
                        'count': len(self.messages)
                    })
                    
            elif path.startswith('/api/messages/'):
                message_id = path.split('/')[-1]
                message_id = int(message_id)
                matching_messages = [msg for msg in self.messages if msg['id'] == message_id]
                if matching_messages:
                    self._send_json_response(matching_messages[0])
                else:
                    self._send_error_response('Message not found', 404)
                    
            elif path == '/api/analytics':
                self._send_json_response({
                    'analytics': {
                        'total_users': len(self.users),
                        'total_courses': len(self.courses),
                        'total_messages': len(self.messages),
                        'active_courses': sum(1 for course in self.courses.values() if course['is_active'])
                    }
                })
                
            elif path == '/':
                self._set_headers(content_type='text/html')
                html_response = f"""
                <html>
                <head><title>Mock ILIAS Server</title></head>
                <body>
                    <h1>Mock ILIAS Server</h1>
                    <p>NIR Intelligence Platform - ILIAS Integration Test Server</p>
                    <h2>Available Endpoints</h2>
                    <ul>
                        <li><a href='/api/health'>/api/health</a> - Health check</li>
                        <li><a href='/api/users'>/api/users</a> - List users</li>
                        <li><a href='/api/courses'>/api/courses</a> - List courses</li>
                        <li><a href='/api/messages'>/api/messages</a> - List messages</li>
                        <li><a href='/api/analytics'>/api/analytics</a> - Analytics</li>
                    </ul>
                    <h2>Statistics</h2>
                    <p>Users: {len(self.users)}</p>
                    <p>Courses: {len(self.courses)}</p>
                    <p>Messages: {len(self.messages)}</p>
                </body>
                </html>
                """
                self.wfile.write(html_response.encode('utf-8'))
                
            else:
                self._send_error_response('Endpoint not found', 404)
                
        except Exception as e:
            self._send_error_response(f'Internal server error: {str(e)}', 500)
    
    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        print(f"POST {path}")
        
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                self._send_error_response('Invalid JSON data', 400)
                return
                
            if path == '/api/users/sync':
                # User synchronization
                username = data.get('username')
                if not username:
                    self._send_error_response('Username is required', 400)
                    return
                    
                user_id = f"ilias_{username}"
                self.users[user_id] = {
                    'ilias_id': user_id,
                    'username': username,
                    'email': data.get('email', f'{username}@example.com'),
                    'first_name': data.get('first_name', 'Test'),
                    'last_name': data.get('last_name', 'User'),
                    'role': data.get('role', 'learner'),
                    'is_active': data.get('is_active', True),
                    'last_sync': int(time.time())
                }
                
                self._send_json_response({
                    'status': 'success',
                    'message': 'User synchronized successfully',
                    'ilias_id': user_id,
                    'user': self.users[user_id]
                }, 201)
                
            elif path == '/api/courses/enroll':
                # Course enrollment
                user_id = data.get('user_id')
                course_id = data.get('course_id')
                
                if not user_id or not course_id:
                    self._send_error_response('user_id and course_id are required', 400)
                    return
                    
                if course_id not in self.courses:
                    self._send_error_response('Course not found', 404)
                    return
                    
                if user_id not in self.users:
                    self._send_error_response('User not found', 404)
                    return
                    
                if user_id not in self.courses[course_id]['enrolled_users']:
                    self.courses[course_id]['enrolled_users'].append(user_id)
                    
                self._send_json_response({
                    'status': 'success',
                    'message': 'User enrolled in course successfully',
                    'user_id': user_id,
                    'course_id': course_id,
                    'course_title': self.courses[course_id]['title']
                }, 200)
                
            elif path == '/api/messages/send':
                # Send message
                sender_id = data.get('sender_id')
                recipient_id = data.get('recipient_id')
                subject = data.get('subject')
                body = data.get('body')
                
                if not all([sender_id, recipient_id, subject, body]):
                    self._send_error_response('sender_id, recipient_id, subject, and body are required', 400)
                    return
                    
                message = {
                    'id': self.message_id_counter,
                    'sender_id': sender_id,
                    'recipient_id': recipient_id,
                    'subject': subject,
                    'body': body,
                    'sent_at': int(time.time()),
                    'read': False
                }
                
                self.messages.append(message)
                self.message_id_counter += 1
                
                self._send_json_response({
                    'status': 'success',
                    'message': 'Message sent successfully',
                    'message_id': message['id']
                }, 201)
                
            else:
                self._send_error_response('Endpoint not found', 404)
                
        except Exception as e:
            self._send_error_response(f'Internal server error: {str(e)}', 500)

def run_mock_ilias_server(port=8081):
    """Run the mock ILIAS server on the specified port"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, MockILIASRequestHandler)
    
    print(f"Starting Mock ILIAS Server on port {port}...")
    print(f"Server URL: http://localhost:{port}")
    print("Available endpoints:")
    print("  GET  /api/health - Health check")
    print("  GET  /api/users - List users")
    print("  POST /api/users/sync - Sync user")
    print("  GET  /api/courses - List courses")
    print("  POST /api/courses/enroll - Enroll user in course")
    print("  GET  /api/messages - List messages")
    print("  POST /api/messages/send - Send message")
    print("  GET  /api/analytics - Get analytics")
    print("Press Ctrl+C to stop the server...")
    print()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Mock ILIAS Server...")
        httpd.server_close()

if __name__ == '__main__':
    run_mock_ilias_server()