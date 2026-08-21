#!/bin/bash

# NIR_Mistral Django Server Start Script (Virtual Environment)
# This script starts the Django server using the project's virtual environment

echo "=========================================="
echo "NIR_Mistral Django Server Start Script"
echo "=========================================="
echo ""

# Change to project directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    /usr/bin/python -m venv venv
    echo "Virtual environment created."
fi

# Use the virtual environment's Python directly
PYTHON="$(pwd)/venv/bin/python"

# Install dependencies if not already installed
if ! $PYTHON -c "import django" 2>/dev/null; then
    echo "Installing dependencies..."
    $(pwd)/venv/bin/pip install django djangorestframework djangorestframework-simplejwt python-dotenv django-cors-headers psycopg2-binary django-storages numpy pandas scipy matplotlib seaborn scikit-learn h5py plotly python-dateutil pytz
    echo "Dependencies installed."
fi

# Check Django version
echo ""
echo "Checking Django installation..."
$PYTHON -c "import django; print('✓ Django version:', django.get_version())"

# Run migrations if needed
echo ""
echo "Running database migrations..."
$PYTHON manage.py migrate 2>/dev/null || echo "Migrations already applied or no changes."

# Start the server
echo ""
echo "=========================================="
echo "Starting Django development server..."
echo "=========================================="
echo ""
echo "🌐 Access the application at: http://localhost:8000/"
echo "🔒 Admin panel at: http://localhost:8000/admin/"
echo "👤 Username: admin"
echo "🔑 Password: admin123"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start Django server
$PYTHON manage.py runserver 0.0.0.0:8000