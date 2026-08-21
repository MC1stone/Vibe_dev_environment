#!/usr/bin/env python3
"""
NIR Intelligence Platform - ILIASIntegrationAgent
Agent for ILIAS e-learning platform integration
"""

import logging
import requests
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from .base_agent import BaseAgent, AgentOutput, AgentStatus, ErrorSeverity, AgentError


@dataclass
class ILIASConfig:
    """Configuration for ILIAS integration"""
    ilias_url: str = "https://ilias.example.com"
    client_id: str = "nir_mistral_client"
    client_secret: str = ""
    api_version: str = "v1"
    saml_enabled: bool = True
    sync_users: bool = True
    sync_courses: bool = True
    sync_content: bool = True


@dataclass
class SyncResult:
    """Result of synchronization operation"""
    success: bool
    operation: str
    items_synced: int = 0
    items_created: int = 0
    items_updated: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ILIASIntegrationAgent(BaseAgent):
    """
    Agent for ILIAS e-learning platform integration
    
    Features:
    - REST API connection to ILIAS
    - User synchronization between Django and ILIAS
    - Course synchronization
    - Communication features (forums, messaging)
    - Learning analytics
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="ILIASIntegrationAgent", version="2.0.0", **kwargs)
        self.dependencies = ['requests', 'python3-saml']
        self.logger = logging.getLogger(f"Agent.ILIASIntegrationAgent")
        
        # Configuration
        self.config = ILIASConfig(
            ilias_url=kwargs.get('ilias_url', 'https://ilias.example.com'),
            client_id=kwargs.get('client_id', 'nir_mistral_client'),
            client_secret=kwargs.get('client_secret', ''),
            saml_enabled=kwargs.get('saml_enabled', True),
            sync_users=kwargs.get('sync_users', True),
            sync_courses=kwargs.get('sync_courses', True)
        )
        
        # API client
        self.api_token: Optional[str] = None
        self.session = requests.Session()
    
    def connect(self) -> Tuple[bool, str]:
        """Establish connection to ILIAS API using OAuth2"""
        try:
            token_url = f"{self.config.ilias_url}/oauth2/token"
            response = self.session.post(token_url, data={
                'grant_type': 'client_credentials',
                'client_id': self.config.client_id,
                'client_secret': self.config.client_secret,
                'scope': 'read write'
            }, headers={'Content-Type': 'application/x-www-form-urlencoded'})
            
            if response.status_code == 200:
                token_data = response.json()
                self.api_token = token_data.get('access_token')
                self.session.headers.update({
                    'Authorization': f'Bearer {self.api_token}'
                })
                self.logger.info("Successfully connected to ILIAS API")
                return True, "Connected successfully"
            else:
                return False, f"Connection failed: {response.status_code} - {response.text}"
                
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def disconnect(self):
        """Disconnect from ILIAS API"""
        self.api_token = None
        self.session.headers.pop('Authorization', None)
        self.logger.info("Disconnected from ILIAS API")
    
    def is_connected(self) -> bool:
        """Check if connected to ILIAS API"""
        return self.api_token is not None
    
    def sync_users(self, django_users: List[Dict[str, Any]]) -> SyncResult:
        """Synchronize users between Django and ILIAS"""
        if not self.is_connected():
            success, message = self.connect()
            if not success:
                return SyncResult(success=False, operation="user_sync", errors=[message])
        
        try:
            ilias_users = self._get_ilias_users()
            created = 0
            updated = 0
            errors = []
            
            for django_user in django_users:
                try:
                    ilias_user = next((u for u in ilias_users if u.get('email') == django_user.get('email')), None)
                    if ilias_user:
                        result = self._update_user(django_user, ilias_user)
                        if result == "updated":
                            updated += 1
                    else:
                        result = self._create_user(django_user)
                        if result == "created":
                            created += 1
                except Exception as e:
                    errors.append(f"Error syncing user {django_user.get('username')}: {str(e)}")
            
            return SyncResult(
                success=True,
                operation="user_sync",
                items_synced=len(django_users),
                items_created=created,
                items_updated=updated,
                errors=errors
            )
        except Exception as e:
            return SyncResult(success=False, operation="user_sync", errors=[str(e)])
    
    def sync_courses(self, django_courses: List[Dict[str, Any]]) -> SyncResult:
        """Synchronize courses between Django and ILIAS"""
        if not self.is_connected():
            success, message = self.connect()
            if not success:
                return SyncResult(success=False, operation="course_sync", errors=[message])
        
        try:
            ilias_courses = self._get_ilias_courses()
            created = 0
            updated = 0
            errors = []
            
            for django_course in django_courses:
                try:
                    ilias_course = next((c for c in ilias_courses if c.get('title') == django_course.get('title')), None)
                    if ilias_course:
                        result = self._update_course(django_course, ilias_course)
                        if result == "updated":
                            updated += 1
                    else:
                        result = self._create_course(django_course)
                        if result == "created":
                            created += 1
                except Exception as e:
                    errors.append(f"Error syncing course {django_course.get('title')}: {str(e)}")
            
            return SyncResult(
                success=True,
                operation="course_sync",
                items_synced=len(django_courses),
                items_created=created,
                items_updated=updated,
                errors=errors
            )
        except Exception as e:
            return SyncResult(success=False, operation="course_sync", errors=[str(e)])
    
    def create_forum(self, course_id: int, forum_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a forum in ILIAS"""
        if not self.is_connected():
            success, message = self.connect()
            if not success:
                return {'success': False, 'error': message}
        
        try:
            url = f"{self.config.ilias_url}/api/v1/courses/{course_id}/forums"
            response = self.session.post(url, json=forum_data)
            if response.status_code in [200, 201]:
                return {'success': True, 'forum': response.json()}
            else:
                return {'success': False, 'error': f"Failed: {response.status_code} - {response.text}"}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_message(self, recipient_id: int, subject: str, body: str) -> Dict[str, Any]:
        """Send a message to a user in ILIAS"""
        if not self.is_connected():
            success, message = self.connect()
            if not success:
                return {'success': False, 'error': message}
        
        try:
            url = f"{self.config.ilias_url}/api/v1/users/{recipient_id}/messages"
            message_data = {'subject': subject, 'body': body, 'priority': 'normal'}
            response = self.session.post(url, json=message_data)
            if response.status_code in [200, 201]:
                return {'success': True, 'message': response.json()}
            else:
                return {'success': False, 'error': f"Failed: {response.status_code} - {response.text}"}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_learning_analytics(self, user_id: int, course_id: Optional[int] = None) -> Dict[str, Any]:
        """Get learning analytics for a user or course"""
        if not self.is_connected():
            success, message = self.connect()
            if not success:
                return {'success': False, 'error': message}
        
        try:
            if course_id:
                url = f"{self.config.ilias_url}/api/v1/courses/{course_id}/users/{user_id}/analytics"
            else:
                url = f"{self.config.ilias_url}/api/v1/users/{user_id}/analytics"
            response = self.session.get(url)
            if response.status_code == 200:
                return {'success': True, 'analytics': response.json()}
            else:
                return {'success': False, 'error': f"Failed: {response.status_code} - {response.text}"}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_ilias_users(self) -> List[Dict[str, Any]]:
        """Get all users from ILIAS"""
        try:
            url = f"{self.config.ilias_url}/api/v1/users"
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json().get('users', [])
            else:
                self.logger.error(f"Failed to get ILIAS users: {response.status_code}")
                return []
        except Exception as e:
            self.logger.error(f"Error getting ILIAS users: {str(e)}")
            return []
    
    def _get_ilias_courses(self) -> List[Dict[str, Any]]:
        """Get all courses from ILIAS"""
        try:
            url = f"{self.config.ilias_url}/api/v1/courses"
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json().get('courses', [])
            else:
                self.logger.error(f"Failed to get ILIAS courses: {response.status_code}")
                return []
        except Exception as e:
            self.logger.error(f"Error getting ILIAS courses: {str(e)}")
            return []
    
    def _create_user(self, django_user: Dict[str, Any]) -> str:
        """Create a new user in ILIAS"""
        try:
            url = f"{self.config.ilias_url}/api/v1/users"
            user_data = {
                'login': django_user.get('username'),
                'email': django_user.get('email'),
                'firstname': django_user.get('first_name', ''),
                'lastname': django_user.get('last_name', ''),
                'active': True
            }
            response = self.session.post(url, json=user_data)
            if response.status_code in [200, 201]:
                self.logger.info(f"Created ILIAS user: {django_user.get('username')}")
                return "created"
            else:
                self.logger.warning(f"Failed to create user: {response.text}")
                return "skipped"
        except Exception as e:
            self.logger.error(f"Error creating user: {str(e)}")
            raise
    
    def _update_user(self, django_user: Dict[str, Any], ilias_user: Dict[str, Any]) -> str:
        """Update an existing user in ILIAS"""
        try:
            url = f"{self.config.ilias_url}/api/v1/users/{ilias_user.get('id')}"
            user_data = {
                'login': django_user.get('username'),
                'email': django_user.get('email'),
                'firstname': django_user.get('first_name', ilias_user.get('firstname')),
                'lastname': django_user.get('last_name', ilias_user.get('lastname')),
                'active': django_user.get('is_active', ilias_user.get('active'))
            }
            response = self.session.put(url, json=user_data)
            if response.status_code == 200:
                self.logger.info(f"Updated ILIAS user: {django_user.get('username')}")
                return "updated"
            else:
                self.logger.warning(f"Failed to update user: {response.text}")
                return "skipped"
        except Exception as e:
            self.logger.error(f"Error updating user: {str(e)}")
            raise
    
    def _create_course(self, django_course: Dict[str, Any]) -> str:
        """Create a new course in ILIAS"""
        try:
            url = f"{self.config.ilias_url}/api/v1/courses"
            course_data = {
                'title': django_course.get('title'),
                'description': django_course.get('description', ''),
                'owner_id': django_course.get('owner_id'),
                'active': True
            }
            response = self.session.post(url, json=course_data)
            if response.status_code in [200, 201]:
                self.logger.info(f"Created ILIAS course: {django_course.get('title')}")
                return "created"
            else:
                self.logger.warning(f"Failed to create course: {response.text}")
                return "skipped"
        except Exception as e:
            self.logger.error(f"Error creating course: {str(e)}")
            raise
    
    def _update_course(self, django_course: Dict[str, Any], ilias_course: Dict[str, Any]) -> str:
        """Update an existing course in ILIAS"""
        try:
            url = f"{self.config.ilias_url}/api/v1/courses/{ilias_course.get('id')}"
            course_data = {
                'title': django_course.get('title'),
                'description': django_course.get('description', ilias_course.get('description')),
                'active': django_course.get('is_active', ilias_course.get('active'))
            }
            response = self.session.put(url, json=course_data)
            if response.status_code == 200:
                self.logger.info(f"Updated ILIAS course: {django_course.get('title')}")
                return "updated"
            else:
                self.logger.warning(f"Failed to update course: {response.text}")
                return "skipped"
        except Exception as e:
            self.logger.error(f"Error updating course: {str(e)}")
            raise
    
    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute the agent's primary function"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting ILIASIntegrationAgent execution")
            
            action = context.get('action', 'connect')
            
            if action == 'connect':
                result = self.connect()
                output = {"status": "completed" if result[0] else "failed", "connected": result[0], "message": result[1]}
                
            elif action == 'sync_users':
                django_users = context.get('users', [])
                sync_result = self.sync_users(django_users)
                output = {
                    "status": "completed" if sync_result.success else "failed",
                    "sync_result": {
                        "success": sync_result.success,
                        "items_synced": sync_result.items_synced,
                        "items_created": sync_result.items_created,
                        "items_updated": sync_result.items_updated,
                        "errors": sync_result.errors
                    }
                }
                
            elif action == 'sync_courses':
                django_courses = context.get('courses', [])
                sync_result = self.sync_courses(django_courses)
                output = {
                    "status": "completed" if sync_result.success else "failed",
                    "sync_result": {
                        "success": sync_result.success,
                        "items_synced": sync_result.items_synced,
                        "items_created": sync_result.items_created,
                        "items_updated": sync_result.items_updated,
                        "errors": sync_result.errors
                    }
                }
                
            elif action == 'create_forum':
                output = self.create_forum(context.get('course_id'), context.get('forum_data', {}))
                
            elif action == 'send_message':
                output = self.send_message(
                    context.get('recipient_id'),
                    context.get('subject', ''),
                    context.get('body', '')
                )
                
            elif action == 'analytics':
                output = self.get_learning_analytics(
                    context.get('user_id'),
                    context.get('course_id')
                )
                
            else:
                output = {"status": "error", "message": f"Unknown action: {action}"}
            
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(output)
            
        except Exception as e:
            return self._handle_error(e)
    
    def validate(self) -> List[AgentError]:
        """Validate agent configuration and state"""
        errors = super().validate()
        
        if not self.config.ilias_url:
            errors.append(AgentError(
                agent_name=self.name,
                error_type="configuration_error",
                message="ILIAS URL is required",
                severity=ErrorSeverity.HIGH,
                context={"missing_field": "ilias_url"},
                solution="Set ilias_url in agent configuration"
            ))
        
        if not self.config.client_id:
            errors.append(AgentError(
                agent_name=self.name,
                error_type="configuration_error",
                message="Client ID is required",
                severity=ErrorSeverity.HIGH,
                context={"missing_field": "client_id"},
                solution="Set client_id in agent configuration"
            ))
        
        return errors


if __name__ == "__main__":
    agent = ILIASIntegrationAgent()
    output = agent.initialize()
    print(f"ILIASIntegrationAgent initialized: {output.status.name}")
