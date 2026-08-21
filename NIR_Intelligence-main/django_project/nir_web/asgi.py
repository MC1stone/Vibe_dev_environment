"""
ASGI config for NIR_Mistral Web Application
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')

application = get_asgi_application()