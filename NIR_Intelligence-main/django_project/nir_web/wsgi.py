"""
WSGI config for NIR_Mistral Web Application
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')

application = get_wsgi_application()