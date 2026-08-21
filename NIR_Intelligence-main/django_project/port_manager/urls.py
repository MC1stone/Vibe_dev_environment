"""
URL Configuration for Port Manager API

This module defines the URL patterns for the Port Management API endpoints.
"""

from django.urls import path
from . import views

app_name = 'port_manager'

urlpatterns = [
    # Main API endpoint
    path('', views.PortManagementAPI.as_view(), name='port_management_api'),
    path('<str:action>/', views.PortManagementAPI.as_view(), name='port_management_action'),
    
    # Simplified endpoints
    path('status/', views.port_status, name='port_status'),
    path('check/<int:port>/', views.check_port_availability, name='check_port'),
    path('reserve/', views.reserve_port_endpoint, name='reserve_port'),
    
    # Specific actions
    path('scan/', views.PortManagementAPI.as_view(), {'action': 'scan'}, name='scan_ports'),
    path('conflicts/', views.PortManagementAPI.as_view(), {'action': 'conflicts'}, name='port_conflicts'),
    path('agents/', views.PortManagementAPI.as_view(), {'action': 'agents'}, name='port_agents'),
    
    # POST endpoints
    path('reserve/', views.PortManagementAPI.as_view(), {'action': 'reserve'}, name='api_reserve_port'),
    path('release/', views.PortManagementAPI.as_view(), {'action': 'release'}, name='api_release_port'),
    path('assign/', views.PortManagementAPI.as_view(), {'action': 'assign'}, name='api_assign_port'),
    path('resolve/', views.PortManagementAPI.as_view(), {'action': 'resolve'}, name='api_resolve_conflicts'),
]

# URL patterns for including in other apps
port_api_urls = [
    path('ports/', views.PortManagementAPI.as_view()),
    path('ports/status/', views.port_status),
    path('ports/check/<int:port>/', views.check_port_availability),
    path('ports/reserve/', views.reserve_port_endpoint),
]

__all__ = ['urlpatterns', 'port_api_urls']