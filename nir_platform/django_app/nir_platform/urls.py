"""
URL configuration for NIR Intelligence Platform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from analysis import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('upload/', views.upload_file, name='upload_file'),
    path('analysis/<int:analysis_id>/', views.analysis_detail, name='analysis_detail'),
    path('analysis/<int:analysis_id>/report/', views.analysis_report, name='analysis_report'),
    path('analysis/<int:analysis_id>/download/', views.download_analysis, name='download_analysis'),
    path('chat/', views.chat_interface, name='chat_interface'),
    path('api/analyze/', views.api_analyze, name='api_analyze'),
    path('api/chat/', views.api_chat, name='api_chat'),
    path('about/', views.about, name='about'),
    path('docs/', views.documentation, name='documentation'),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
