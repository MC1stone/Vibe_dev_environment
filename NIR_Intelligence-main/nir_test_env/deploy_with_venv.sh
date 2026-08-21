#!/bin/bash

echo "=========================================="
echo "NIR Intelligence Platform - Virtual Environment Deployment"
echo "=========================================="
echo ""

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root for system-wide installation"
    echo "Trying to continue with user installation..."
fi

# Create virtual environment
echo "1. Creating virtual environment..."
python3 -m venv /opt/nir_venv
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment"
    echo "Trying alternative location..."
    python3 -m venv ~/nir_venv
    VENV_PATH="~/nir_venv"
else
    VENV_PATH="/opt/nir_venv"
fi
echo "✓ Virtual environment created at: $VENV_PATH"

# Activate virtual environment
echo "2. Activating virtual environment..."
source "$VENV_PATH/bin/activate"
echo "✓ Virtual environment activated"

# Install Python dependencies
echo "3. Installing Python dependencies..."

# Install build dependencies first
if command -v apt &> /dev/null; then
    echo "Installing build dependencies..."
    apt update -y 2>/dev/null
    apt install -y build-essential python3-dev libpq-dev libssl-dev libffi-dev 2>/dev/null
fi

# Try with break-system-packages flag first
pip install --break-system-packages -r /media/martin/Ventoy/NIR_Ansible/requirements.txt

if [ $? -ne 0 ]; then
    echo "⚠ Warning: break-system-packages failed, trying without flag..."
    pip install -r /media/martin/Ventoy/NIR_Ansible/requirements.txt
fi

if [ $? -ne 0 ]; then
    echo "⚠ Warning: Direct pip install failed, trying individual packages..."
    
    # Install packages individually with better error handling
    PACKAGES=(
        "Django==4.2.0"
        "djangorestframework==3.14.0"
        "psycopg2-binary==2.9.9"
        "python-dotenv==1.0.0"
        "flwr==1.0.0"
        "weaviate-client==3.23.0"
        "pandas==2.0.3"
        "numpy==1.24.3"
        "scikit-learn==1.3.0"
        "requests==2.31.0"
        "ansible==8.0.0"
        "docker==6.1.3"
        "python3-saml==1.15.0"
        "django-saml2==1.5.0"
        "social-auth-app-django==5.2.0"
        "lti==1.3.0"
        "celery==5.3.4"
        "redis==4.5.5"
        "gunicorn==21.2.0"
    )
    
    for package in "${PACKAGES[@]}"; do
        echo "Installing $package..."
        
        # Try with break-system-packages first
        pip install --break-system-packages "$package"
        
        if [ $? -ne 0 ]; then
            echo "⚠ Warning: Failed to install $package with break-system-packages, trying without..."
            pip install "$package"
        fi
        
        if [ $? -ne 0 ]; then
            echo "⚠ Warning: Failed to install $package, trying with --no-cache-dir..."
            pip install --no-cache-dir "$package"
        fi
        
        if [ $? -ne 0 ]; then
            echo "❌ Error: Failed to install $package after multiple attempts, skipping..."
        else
            echo "✓ Successfully installed $package"
        fi
    done
fi

echo "✓ Python dependencies installed"

# Check Ansible installation
if ! command -v ansible &> /dev/null; then
    echo "4. Installing Ansible..."
    
    # Try system package first
    apt update -y 2>/dev/null
    apt install -y ansible 2>/dev/null
    
    if [ $? -ne 0 ]; then
        echo "⚠ Warning: System ansible failed, trying pip..."
        pip install --break-system-packages ansible==8.0.0
    fi
    
    if command -v ansible &> /dev/null; then
        echo "✓ Ansible installed"
    else
        echo "✗ ERROR: Failed to install Ansible"
        exit 1
    fi
fi

# Update PATH to include virtual environment
export PATH="$VENV_PATH/bin:$PATH"

# Run Ansible playbook
echo "5. Running Ansible playbook..."
cd /media/martin/Ventoy/NIR_Ansible/ansible

# Check if inventory file exists
if [ ! -f "inventory.ini" ]; then
    echo "Creating default inventory..."
    cat > inventory.ini << 'EOF'
[localhost]
localhost ansible_connection=local

[localhost:vars]
ansible_python_interpreter=/usr/bin/python3
EOF
fi

# Run server deployment playbook
ansible-playbook playbooks/server_deployment.yml -i inventory.ini

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Server deployment completed successfully!"
    echo "=========================================="
    echo ""
    echo "Server is now running at: http://localhost:8000"
    echo "Admin interface: http://localhost:8000/admin"
    echo "API documentation: http://localhost:8000/api/docs"
    echo ""
    echo "Virtual environment location: $VENV_PATH"
    echo "To activate manually: source $VENV_PATH/bin/activate"
else
    echo ""
    echo "=========================================="
    echo "Server deployment failed!"
    echo "=========================================="
    echo ""
    echo "Check the error messages above for details."
    echo "Common issues:"
    echo "  - Missing dependencies"
    echo "  - Permission issues"
    echo "  - Network connectivity"
    echo ""
    echo "Try:"
    echo "  1. Check logs: journalctl -xe"
    echo "  2. Install missing packages manually"
    echo "  3. Run with verbose: bash -x $0"
    exit 1
fi

echo ""
echo "=========================================="
echo "Virtual Environment Deployment Complete!"
echo "=========================================="
