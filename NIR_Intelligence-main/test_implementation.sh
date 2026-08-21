#!/bin/bash

# NIR Intelligence Platform - Test Implementation Script
# This script sets up virtual environments for both server and client applications

set -e

echo "=========================================="
echo "NIR Intelligence Platform - Test Implementation"
echo "=========================================="
echo ""

# Check if running as root
if [ "$(id -u)" -eq 0 ]; then
    echo "ERROR: This script should NOT be run as root"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
if [ "$(printf '%s\n' "3.12" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.12" ]; then
    echo "ERROR: Python 3.12 or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose installation
if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create project directory structure
echo "Creating project directory structure..."
mkdir -p nir_test_env/{server,client}/{logs,data/{raw,processed},output,config}
mkdir -p nir_test_env/server/ansible/{playbooks,roles,inventory}
mkdir -p nir_test_env/client/ansible/{playbooks,roles,inventory}

echo "Directory structure created successfully."
echo ""

# Create virtual environment for server
echo "Setting up server environment..."
cd nir_test_env/server
python3 -m venv venv
source venv/bin/activate

# Install server dependencies
pip install --upgrade pip
pip install -r ../../requirements.txt

# Create server configuration
cat > config/server_settings.py << 'EOF'
# NIR Intelligence Platform - Server Configuration
import os

# Base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Development settings
DEBUG = True
SECRET_KEY = 'test-secret-key-for-development-only'
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Database settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nir_db',
        'USER': 'nir_user',
        'PASSWORD': 'nir_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# ILIAS Integration
ILIAS = {
    'BASE_URL': 'http://localhost:8080',  # Local test ILIAS
    'API_KEY': 'test_api_key',
    'API_SECRET': 'test_api_secret',
    'SSO_ENABLED': False,  # Disabled for testing
    'SYNC_FREQUENCY': 'manual',
    'COURSE_PREFIX': 'TEST_'
}

# Federated Learning
FLOWER = {
    'SERVER_ADDRESS': '0.0.0.0',
    'SERVER_PORT': 5555,
    'CLIENT_PORT': 5556,
    'ROUNDS': 3,
    'MIN_CLIENTS': 2
}

# File upload settings
FILE_UPLOAD_MAX_SIZE = 100 * 1024 * 1024  # 100MB
FILE_UPLOAD_TYPES = ['.csv', '.json', '.h5', '.jdx', '.spc', '.txt', '.zip']

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'nir_server.log'),
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'DEBUG',
    },
}
EOF

# Create server Ansible playbook
mkdir -p ansible/playbooks
cat > ansible/playbooks/server_deployment.yml << 'EOF'
---
- name: Deploy NIR Intelligence Platform Server
  hosts: localhost
  become: yes
  vars:
    project_dir: "{{ lookup('env', 'PWD') }}"
    python_version: "3.12"
    docker_users: ["{{ ansible_user }}"]

  tasks:
    - name: Install system dependencies
      apt:
        name: ["python3-pip", "python3-dev", "libpq-dev", "postgresql", "postgresql-contrib", "docker.io", "docker-compose", "ansible", "git"]
        state: present
        update_cache: yes

    - name: Install Python dependencies
      pip:
        name: ["virtualenv", "wheel", "setuptools"]
        state: present
        executable: pip3

    - name: Create virtual environment
      command: python3 -m venv {{ project_dir }}/venv
      args:
        creates: {{ project_dir }}/venv/bin/activate

    - name: Install project dependencies
      pip:
        requirements: {{ project_dir }}/requirements.txt
        virtualenv: {{ project_dir }}/venv

    - name: Start Docker service
      service:
        name: docker
        state: started
        enabled: yes

    - name: Add users to docker group
      user:
        name: "{{ item }}"
        groups: docker
        append: yes
      loop: "{{ docker_users }}"

    - name: Create database
      postgresql_db:
        name: nir_db
        state: present
      become_user: postgres

    - name: Create database user
      postgresql_user:
        db: nir_db
        name: nir_user
        password: nir_password
        priv: ALL
        state: present
      become_user: postgres

    - name: Create log directory
      file:
        path: "{{ project_dir }}/logs"
        state: directory
        mode: '0755'

    - name: Create data directories
      file:
        path: "{{ project_dir }}/data/{{ item }}"
        state: directory
        mode: '0755'
      loop: ["raw", "processed", "output"]

    - name: Display completion message
      debug:
        msg: "Server deployment completed successfully!"
EOF

# Create server inventory
cat > ansible/inventory.ini << 'EOF'
[localhost]
localhost ansible_connection=local

[servers]
localhost

[servers:vars]
ansible_python_interpreter=/usr/bin/python3
EOF

deactivate

echo "Server environment setup completed."
echo ""

# Create virtual environment for client
echo "Setting up client environment..."
cd ../client
python3 -m venv venv
source venv/bin/activate

# Install client dependencies (lighter version)
pip install --upgrade pip
pip install ansible docker requests pyyaml jinja2

# Create client configuration
cat > config/client_settings.py << 'EOF'
# NIR Intelligence Platform - Client Configuration
import os

# Base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Server connection
SERVER_URL = "http://localhost:8000"  # Local test server
API_KEY = "test_client_api_key"
API_SECRET = "test_client_api_secret"

# Local cache settings
CACHE_DIR = os.path.join(BASE_DIR, 'data', 'cache')
CACHE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
CACHE_EXPIRATION = 30 * 24 * 60 * 60  # 30 days

# File settings
LOCAL_STORAGE = os.path.join(BASE_DIR, 'data', 'local')
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB

# Federated learning
FLOWER_CLIENT = {
    'SERVER_ADDRESS': 'localhost',
    'SERVER_PORT': 5555,
    'CLIENT_PORT': 5556,
    'AUTO_START': False
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'nir_client.log'),
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'DEBUG',
    },
}
EOF

# Create client Ansible playbook
mkdir -p ansible/playbooks
cat > ansible/playbooks/client_deployment.yml << 'EOF'
---
- name: Deploy NIR Intelligence Platform Client
  hosts: localhost
  become: yes
  vars:
    project_dir: "{{ lookup('env', 'PWD') }}"
    server_url: "http://localhost:8000"

  tasks:
    - name: Install system dependencies
      apt:
        name: ["python3-pip", "python3-dev", "git", "ansible"]
        state: present
        update_cache: yes

    - name: Install Python dependencies
      pip:
        name: ["virtualenv", "wheel", "setuptools"]
        state: present
        executable: pip3

    - name: Create virtual environment
      command: python3 -m venv {{ project_dir }}/venv
      args:
        creates: {{ project_dir }}/venv/bin/activate

    - name: Install client dependencies
      pip:
        name: ["ansible", "docker", "requests", "pyyaml", "jinja2"]
        virtualenv: {{ project_dir }}/venv

    - name: Create configuration directory
      file:
        path: "{{ project_dir }}/config"
        state: directory
        mode: '0755'

    - name: Create data directories
      file:
        path: "{{ project_dir }}/data/{{ item }}"
        state: directory
        mode: '0755'
      loop: ["local", "cache", "output"]

    - name: Create log directory
      file:
        path: "{{ project_dir }}/logs"
        state: directory
        mode: '0755'

    - name: Configure server connection
      template:
        src: "templates/client_config.j2"
        dest: "{{ project_dir }}/config/client_settings.py"
        mode: '0644'

    - name: Display completion message
      debug:
        msg: "Client deployment completed successfully!"
EOF

# Create client inventory
cat > ansible/inventory.ini << 'EOF'
[localhost]
localhost ansible_connection=local

[clients]
localhost

[clients:vars]
ansible_python_interpreter=/usr/bin/python3
EOF

deactivate

echo "Client environment setup completed."
echo ""

# Create test data
cd ../..
echo "Creating test data..."

# Create sample spectral data
cat > nir_test_env/server/data/raw/sample_spectrum.csv << 'EOF'
wavelength,intensity,metadata
900,0.123,"{"instrument":"DIY_Spectrometer","acquisition_time":"2026-07-30T10:00:00","sample":"test_sample_1"}"
950,0.187,"{"instrument":"DIY_Spectrometer","acquisition_time":"2026-07-30T10:00:00","sample":"test_sample_1"}"
1000,0.254,"{"instrument":"DIY_Spectrometer","acquisition_time":"2026-07-30T10:00:00","sample":"test_sample_1"}"
1050,0.312,"{"instrument":"DIY_Spectrometer","acquisition_time":"2026-07-30T10:00:00","sample":"test_sample_1"}"
1100,0.289,"{"instrument":"DIY_Spectrometer","acquisition_time":"2026-07-30T10:00:00","sample":"test_sample_1"}"
EOF

# Create test configuration for Docker
cat > nir_test_env/docker-compose.test.yml << 'EOF'
version: '3.8'

services:
  # Test PostgreSQL Database
  postgresql:
    image: postgres:15-alpine
    container_name: nir_postgresql_test
    environment:
      POSTGRES_USER: nir_user
      POSTGRES_PASSWORD: nir_password
      POSTGRES_DB: nir_db
    ports:
      - "5432:5432"
    volumes:
      - nir_test_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nir_user -d nir_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Test Weaviate Vector Database
  weaviate:
    image: semitechnologies/weaviate:1.23.0
    container_name: nir_weaviate_test
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"
      PERSISTENCE_DATA_PATH: "/var/lib/weaviate"
      DEFAULT_VECTORIZER_MODULE: "none"
      ENABLE_MODULES: ""
    ports:
      - "8080:8080"
    volumes:
      - nir_test_weaviate_data:/var/lib/weaviate

  # Test ILIAS (simulated)
  ilias:
    image: python:3.12-slim
    container_name: nir_ilias_test
    command: tail -f /dev/null
    ports:
      - "8081:8081"
    volumes:
      - ./nir_test_env/server/data:/app/data
    working_dir: /app

volumes:
  nir_test_postgres_data:
  nir_test_weaviate_data:
EOF

# Create test script for server
cat > nir_test_env/test_server.sh << 'EOF'
#!/bin/bash

echo "Starting NIR Intelligence Platform Server Test..."
echo ""

# Activate virtual environment
cd nir_test_env/server
source venv/bin/activate

# Run Ansible playbook
echo "Running server deployment playbook..."
ansible-playbook ansible/playbooks/server_deployment.yml -i ansible/inventory.ini

# Start Docker containers
echo "Starting Docker containers..."
cd ../..
docker-compose -f nir_test_env/docker-compose.test.yml up -d

# Wait for services to be ready
echo "Waiting for services to initialize..."
sleep 15

# Check service status
echo "Checking service status..."
docker ps

# Run basic tests
echo "Running basic functionality tests..."
python3 -c "
import sys
sys.path.append('nir_test_env/server')
import psycopg2
try:
    conn = psycopg2.connect(
        dbname='nir_db',
        user='nir_user',
        password='nir_password',
        host='localhost'
    )
    print('✓ Database connection successful')
    conn.close()
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    sys.exit(1)
"

echo ""
echo "Server test environment is ready!"
echo "Access the server at: http://localhost:8000"
echo "Access Weaviate at: http://localhost:8080"
echo "Access test ILIAS at: http://localhost:8081"
EOF

# Create test script for client
cat > nir_test_env/test_client.sh << 'EOF'
#!/bin/bash

echo "Starting NIR Intelligence Platform Client Test..."
echo ""

# Activate virtual environment
cd nir_test_env/client
source venv/bin/activate

# Run Ansible playbook
echo "Running client deployment playbook..."
ansible-playbook ansible/playbooks/client_deployment.yml -i ansible/inventory.ini

# Test server connection
echo "Testing server connection..."
python3 -c "
import requests
import sys
try:
    response = requests.get('http://localhost:8000/api/status/')
    if response.status_code == 200:
        print('✓ Server connection successful')
    else:
        print(f'✗ Server connection failed with status {response.status_code}')
        sys.exit(1)
except Exception as e:
    print(f'✗ Server connection failed: {e}')
    sys.exit(1)
"

echo ""
echo "Client test environment is ready!"
echo "Client can connect to server at: http://localhost:8000"
EOF

# Create comprehensive test script
cat > nir_test_env/run_tests.sh << 'EOF'
#!/bin/bash

echo "=========================================="
echo "NIR Intelligence Platform - Comprehensive Test"
echo "=========================================="
echo ""

# Test server
echo "1. Testing Server Environment..."
bash nir_test_env/test_server.sh
if [ $? -ne 0 ]; then
    echo "✗ Server test failed"
    exit 1
fi
echo "✓ Server test passed"
echo ""

# Test client
echo "2. Testing Client Environment..."
bash nir_test_env/test_client.sh
if [ $? -ne 0 ]; then
    echo "✗ Client test failed"
    exit 1
fi
echo "✓ Client test passed"
echo ""

# Test data processing
echo "3. Testing Data Processing..."
python3 << 'PYTHON'
import sys
import os
import json
import pandas as pd

# Add server to path
sys.path.append('nir_test_env/server')

# Test data loading
try:
    data_path = 'nir_test_env/server/data/raw/sample_spectrum.csv'
    df = pd.read_csv(data_path)
    print(f"✓ Data loaded successfully: {len(df)} rows")
    
    # Test metadata extraction
    metadata = json.loads(df['metadata'].iloc[0])
    print(f"✓ Metadata extracted: {metadata['instrument']}")
    
    # Test basic analysis
    wavelengths = df['wavelength'].tolist()
    intensities = df['intensity'].tolist()
    
    if len(wavelengths) > 0 and len(intensities) > 0:
        print(f"✓ Spectral data validated: {len(wavelengths)} data points")
    else:
        print("✗ Spectral data validation failed")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ Data processing failed: {e}")
    sys.exit(1)
PYTHON

if [ $? -ne 0 ]; then
    echo "✗ Data processing test failed"
    exit 1
fi
echo "✓ Data processing test passed"
echo ""

# Test ILIAS integration (simulated)
echo "4. Testing ILIAS Integration..."
python3 << 'PYTHON'
import sys
sys.path.append('nir_test_env/server')

# Simulate ILIAS API calls
class MockILIASAPI:
    def __init__(self):
        self.users = {}
        self.courses = {
            'NIR_101': {'title': 'Introduction to NIR Spectroscopy'},
            'NIR_201': {'title': 'Advanced NIR Data Analysis'}
        }
    
    def sync_user(self, user_data):
        user_id = f"ilias_{user_data['username']}"
        self.users[user_id] = user_data
        return {'ilias_id': user_id, 'status': 'synced'}
    
    def get_courses(self):
        return list(self.courses.values())

try:
    api = MockILIASAPI()
    
    # Test user sync
    user_data = {
        'username': 'test_user',
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User'
    }
    result = api.sync_user(user_data)
    print(f"✓ User synchronization successful: {result['ilias_id']}")
    
    # Test course listing
    courses = api.get_courses()
    print(f"✓ Course retrieval successful: {len(courses)} courses")
    
except Exception as e:
    print(f"✗ ILIAS integration failed: {e}")
    sys.exit(1)
PYTHON

if [ $? -ne 0 ]; then
    echo "✗ ILIAS integration test failed"
    exit 1
fi
echo "✓ ILIAS integration test passed"
echo ""

# Test federated learning setup
echo "5. Testing Federated Learning Setup..."
python3 << 'PYTHON'
import sys
sys.path.append('nir_test_env/server')

try:
    # Test Flower client setup
    from flwr.client import NumPyClient
    from flwr.common import ndarrays_to_parameters
    
    # Create mock client
    class MockNIRClient(NumPyClient):
        def get_parameters(self, config):
            return ndarrays_to_parameters([1, 2, 3])
        
        def fit(self, parameters, config):
            return ndarrays_to_parameters([1, 2, 3]), 10, {}
        
        def evaluate(self, parameters, config):
            return 0.5, 10, {'accuracy': 0.95}
    
    client = MockNIRClient()
    params = client.get_parameters({})
    print(f"✓ Federated learning client initialized")
    print(f"✓ Parameter exchange successful: {len(params.tensors)} tensors")
    
except Exception as e:
    print(f"✗ Federated learning test failed: {e}")
    sys.exit(1)
PYTHON

if [ $? -ne 0 ]; then
    echo "✗ Federated learning test failed"
    exit 1
fi
echo "✓ Federated learning test passed"
echo ""

echo "=========================================="
echo "All tests passed successfully!"
echo "=========================================="
echo ""
echo "Test Environment Summary:"
echo "- Server: http://localhost:8000"
echo "- Weaviate: http://localhost:8080"
echo "- Test ILIAS: http://localhost:8081"
echo "- PostgreSQL: localhost:5432"
echo ""
echo "Server directory: nir_test_env/server"
echo "Client directory: nir_test_env/client"
echo "Test data: nir_test_env/server/data/raw/"
echo ""
echo "To stop the test environment:"
echo "  docker-compose -f nir_test_env/docker-compose.test.yml down"
EOF

# Make scripts executable
chmod +x nir_test_env/test_server.sh
chmod +x nir_test_env/test_client.sh
chmod +x nir_test_env/run_tests.sh
chmod +x nir_test_env/test_implementation.sh

echo "=========================================="
echo "Test Implementation Setup Complete!"
echo "=========================================="
echo ""
echo "Created test environment structure:"
echo "  - nir_test_env/server/ (Full server installation)"
echo "  - nir_test_env/client/ (Lightweight client)"
echo "  - Test data and configurations"
echo "  - Ansible playbooks for deployment"
echo ""
echo "To run the comprehensive test:"
echo "  bash nir_test_env/run_tests.sh"
echo ""
echo "To run individual tests:"
echo "  Server: bash nir_test_env/test_server.sh"
echo "  Client: bash nir_test_env/test_client.sh"
echo ""
echo "The test environment includes:"
echo "  ✓ PostgreSQL database"
echo "  ✓ Weaviate vector database"
echo "  ✓ Simulated ILIAS instance"
echo "  ✓ Sample spectral data"
echo "  ✓ Automated deployment scripts"
