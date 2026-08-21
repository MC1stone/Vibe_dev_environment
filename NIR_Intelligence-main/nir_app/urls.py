from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='nir_home'),
    path('api/', views.api_info, name='api_info'),
    path('api/spectral-analysis/', views.spectral_analysis, name='spectral_analysis'),
]