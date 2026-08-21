#!/bin/bash

# NIR_Mistral Django Server Start Script
# This script ensures all dependencies are in the Python path

echo "Starting NIR_Mistral Django Server..."
echo "======================================"

# Add system site-packages to PYTHONPATH
PYTHONPATH="/var/data/python/lib/python3.13/site-packages:$PYTHONPATH"

# Add user site-packages to PYTHONPATH (for PEP 668 compatibility)
USER_SITE_PACKAGES="$HOME/.local/lib/python3.13/site-packages"
if [ -d "$USER_SITE_PACKAGES" ]; then
    PYTHONPATH="$USER_SITE_PACKAGES:$PYTHONPATH"
fi

# Add project directories to PYTHONPATH
PROJECT_ROOT="/home/martin/Development/vsCode_Environment/NIR_Mistral"
DJANGO_PROJECT="$PROJECT_ROOT/django_project"
NIR_TEST="$PROJECT_ROOT/NIR_TEST"

export PYTHONPATH="$DJANGO_PROJECT:$NIR_TEST:$PROJECT_ROOT:/var/data/python/lib/python3.13/site-packages:$PYTHONPATH"

echo "PYTHONPATH: $PYTHONPATH"
echo ""

# Change to django_project directory
cd "$DJANGO_PROJECT"

# Check if Django is available
echo "Checking Django installation..."
python3 -c "import django; print('✓ Django version:', django.get_version())" || {
    echo "❌ Django not found. Installing..."
    echo "Note: Using python3 -m pip to handle PEP 668 restrictions"
    python3 -m pip install --user django djangorestframework djangorestframework-simplejwt || {
        echo "❌ Failed to install Django. Trying with --break-system-packages..."
        python3 -m pip install --break-system-packages django djangorestframework djangorestframework-simplejwt
    }
}

echo ""
echo "Starting Django development server..."

# Default port
PORT=${1:-8000}
echo "Access the application at: http://localhost:$PORT/"
echo "Admin panel at: http://localhost:$PORT/admin/"
echo "Username: admin, Password: admin123"
echo ""

# Kill any existing Django server processes on this port
echo "Checking for existing processes on port $PORT..."
pkill -f "python3.*runserver.*:$PORT" || true
pkill -f "manage.py.*runserver.*:$PORT" || true
sleep 1

# Start the server
python3 manage.py runserver 0.0.0.0:$PORT