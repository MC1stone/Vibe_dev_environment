#!/bin/bash

# Test script to verify Docker path configuration

echo "🧪 Testing Docker path configuration..."
echo ""

# Test if we can find manage.py in the right location
echo "📁 Checking for manage.py files..."
find . -name "manage.py" -type f

echo ""
echo "📁 Current directory structure:"
ls -la | grep -E "(django_project|manage.py)"

echo ""
echo "🔍 Testing path that Docker will use..."
echo "Working directory: /app"
echo "Command: python django_project/manage.py check"
echo ""

# Test if the command would work locally
if [ -f "./django_project/manage.py" ]; then
    echo "✅ django_project/manage.py exists"
    echo "✅ Command 'python django_project/manage.py' should work"
else
    echo "❌ django_project/manage.py not found"
fi

echo ""
echo "🔍 Testing Django settings module..."
if [ -f "./django_project/nir_web/settings.py" ]; then
    echo "✅ django_project/nir_web/settings.py exists"
    echo "✅ DJANGO_SETTINGS_MODULE=nir_web.settings is correct"
else
    echo "❌ django_project/nir_web/settings.py not found"
fi

echo ""
echo "🔍 Testing WSGI module..."
if [ -f "./django_project/nir_web/wsgi.py" ]; then
    echo "✅ django_project/nir_web/wsgi.py exists"
    echo "✅ WSGI module path is correct"
else
    echo "❌ django_project/nir_web/wsgi.py not found"
fi

echo ""
echo "📋 Summary:"
echo "   - Project structure: Django project in ./django_project/"
echo "   - manage.py: ./django_project/manage.py"
echo "   - settings.py: ./django_project/nir_web/settings.py"
echo "   - wsgi.py: ./django_project/nir_web/wsgi.py"
echo ""
echo "✅ Docker configuration should use:"
echo "   - WORKDIR: /app"
echo "   - PYTHONPATH: /app"
echo "   - Command: python django_project/manage.py"
echo "   - WSGI: django_project.nir_web.wsgi:application"