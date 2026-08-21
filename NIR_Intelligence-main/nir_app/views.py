from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
import json


def home(request):
    """Home view for NIR Intelligence Platform"""
    return HttpResponse("""
    <h1>NIR Intelligence Platform</h1>
    <p>Welcome to the NIR Spectral Analysis System</p>
    <ul>
        <li><a href="/admin/">Admin Panel</a></li>
        <li><a href="/api/">API Documentation</a></li>
        <li><a href="/media/test.txt">Test Media File</a></li>
    </ul>
    """)


def api_info(request):
    """API information endpoint"""
    api_info = {
        "name": "NIR Intelligence Platform API",
        "version": "1.0.0",
        "endpoints": {
            "/api/spectral-analysis/": "POST - Analyze spectral data",
            "/api/parameter-recommendations/": "POST - Get parameter recommendations",
            "/api/shift-detection/": "POST - Detect wavelength shifts",
            "/api/reports/": "GET - Generate analysis reports"
        },
        "media_url": "/media/",
        "static_url": "/static/"
    }
    return JsonResponse(api_info, json_dumps_params={'indent': 2})


def spectral_analysis(request):
    """Placeholder for spectral analysis endpoint"""
    if request.method == 'POST':
        # This will be implemented with your actual spectral analysis logic
        return JsonResponse({
            "status": "success",
            "message": "Spectral analysis endpoint - to be implemented",
            "data": {}
        })
    return JsonResponse({"error": "Method not allowed"}, status=405)
