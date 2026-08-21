#!/bin/bash

echo "=========================================="
echo "NIR Intelligence Platform - USB Ansible Creator"
echo "=========================================="
echo ""

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root to create USB devices"
    exit 1
fi

# Check for required tools
REQUIRED_TOOLS=("lsblk" "mkfs.ext4" "rsync" "unzip" "wget" "python3" "pip")
for tool in "${REQUIRED_TOOLS[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
        echo "ERROR: Required tool '$tool' is not installed"
        exit 1
    fi
done

echo "✓ All required tools are available"
echo ""

# Show available USB devices
echo "Available USB devices:"
echo "======================"
lsblk -d -o NAME,SIZE,MODEL | grep -v "loop"
echo ""

# Ask user to select USB device
read -p "Enter USB device name (e.g., sdb, sdc): " USB_DEVICE
if [ -z "$USB_DEVICE" ]; then
    echo "ERROR: No USB device specified"
    exit 1
fi

# Verify device exists
if [ ! -e "/dev/$USB_DEVICE" ]; then
    echo "ERROR: Device /dev/$USB_DEVICE does not exist"
    exit 1
fi

# Confirm with user
echo "WARNING: All data on /dev/$USB_DEVICE will be ERASED!"
read -p "Are you sure you want to continue? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "Operation cancelled"
    exit 0
fi

echo ""
echo "Creating USB Bootable Ansible for NIR Intelligence Platform..."
echo ""

# Create mount point
MOUNT_POINT="/mnt/usb_ansible"
mkdir -p "$MOUNT_POINT"

# Format USB device
echo "1. Formatting USB device..."
mkfs.ext4 -L "NIR_Ansible" "/dev/$USB_DEVICE"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to format USB device"
    exit 1
fi
echo "✓ USB device formatted successfully"

# Mount USB device
echo "2. Mounting USB device..."
mount "/dev/$USB_DEVICE" "$MOUNT_POINT"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to mount USB device"
    exit 1
fi
echo "✓ USB device mounted at $MOUNT_POINT"

# Create directory structure on USB
echo "3. Creating directory structure..."
mkdir -p "$MOUNT_POINT/{ansible,scripts,packages,config,docs,data}"
mkdir -p "$MOUNT_POINT/ansible/{playbooks,roles,inventory}"
mkdir -p "$MOUNT_POINT/scripts/{server,client}"
mkdir -p "$MOUNT_POINT/packages/{server,client}"
mkdir -p "$MOUNT_POINT/data/{raw,processed}"
echo "✓ Directory structure created"

# Create README
echo "4. Creating documentation..."
cat > "$MOUNT_POINT/README.md" << 'EOF'
# NIR Intelligence Platform - USB Bootable Ansible

## Overview
This USB drive contains a complete offline deployment system for the NIR Intelligence Platform with ILIAS integration.

## Contents

### /ansible/
- **playbooks/**: Ansible playbooks for server and client deployment
- **roles/**: Ansible roles for different components
- **inventory/**: Inventory files for different environments

### /scripts/
- **server/**: Server deployment and management scripts
- **client/**: Client deployment and management scripts

### /packages/
- **server/**: Offline packages for server deployment
- **client/**: Offline packages for client deployment

### /config/
- Configuration files for different environments

### /docs/
- Documentation and setup guides

### /data/
- Sample data and test datasets

## Usage

### For Server Deployment
```bash
# Mount the USB drive
mount /dev/sdX1 /mnt/usb

# Navigate to the USB drive
cd /mnt/usb

# Run server deployment
bash scripts/server/deploy_server.sh
```

### For Client Deployment
```bash
# Mount the USB drive
mount /dev/sdX1 /mnt/usb

# Navigate to the USB drive
cd /mnt/usb

# Run client deployment
bash scripts/client/deploy_client.sh
```

## Requirements
- Linux system (Ubuntu 22.04+ recommended)
- Python 3.12+
- Ansible 2.15+
- Docker (for containerized components)
- At least 4GB RAM, 20GB disk space

## Support
For issues or questions, contact:
- Support Email: support@nir-platform.org
- Documentation: https://docs.nir-platform.org

## Version
NIR Intelligence Platform v1.0.0
USB Ansible Creator v1.0.0
EOF

echo "✓ Documentation created"

# Copy Ansible playbooks
echo "5. Copying Ansible playbooks..."
cp -r "$OLDPWD/nir_test_env/server/ansible/"* "$MOUNT_POINT/ansible/"
cp -r "$OLDPWD/nir_test_env/client/ansible/"* "$MOUNT_POINT/ansible/"
echo "✓ Ansible playbooks copied"

# Create server deployment script
cat > "$MOUNT_POINT/scripts/server/deploy_server.sh" << 'EOF'
#!/bin/bash

echo "=========================================="
echo "NIR Intelligence Platform - Server Deployment"
echo "=========================================="
echo ""

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
if [ "$(printf '%s\n' "3.12" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.12" ]; then
    echo "ERROR: Python 3.12 or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

# Check Ansible installation
if ! command -v ansible &> /dev/null; then
    echo "Installing Ansible..."
    apt update
    apt install -y ansible
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --no-index --find-links=/mnt/usb/packages/server -r requirements.txt

# Run Ansible playbook
echo "Running server deployment playbook..."
cd /mnt/usb/ansible
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
else
    echo ""
    echo "=========================================="
    echo "Server deployment failed!"
    echo "=========================================="
    exit 1
fi
EOF

chmod +x "$MOUNT_POINT/scripts/server/deploy_server.sh"

# Create client deployment script
cat > "$MOUNT_POINT/scripts/client/deploy_client.sh" << 'EOF'
#!/bin/bash

echo "=========================================="
echo "NIR Intelligence Platform - Client Deployment"
echo "=========================================="
echo ""

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
if [ "$(printf '%s\n' "3.12" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.12" ]; then
    echo "ERROR: Python 3.12 or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

# Check Ansible installation
if ! command -v ansible &> /dev/null; then
    echo "Installing Ansible..."
    apt update
    apt install -y ansible
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --no-index --find-links=/mnt/usb/packages/client -r requirements.txt

# Run Ansible playbook
echo "Running client deployment playbook..."
cd /mnt/usb/ansible
ansible-playbook playbooks/client_deployment.yml -i inventory.ini

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Client deployment completed successfully!"
    echo "=========================================="
    echo ""
    echo "Client is now configured to connect to: http://localhost:8000"
    echo "Configuration file: /etc/nir/client_config.yaml"
    echo "Logs: /var/log/nir/client.log"
else
    echo ""
    echo "=========================================="
    echo "Client deployment failed!"
    echo "=========================================="
    exit 1
fi
EOF

chmod +x "$MOUNT_POINT/scripts/client/deploy_client.sh"

# Create server requirements file
cat > "$MOUNT_POINT/requirements.txt" << 'EOF'
# NIR Intelligence Platform - Server Requirements
Django==4.2.0
djangorestframework==3.14.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
flwr==1.0.0
weaviate-client==3.23.0
pandas==2.0.3
numpy==1.24.3
scikit-learn==1.3.0
requests==2.31.0
ansible==8.0.0
docker==6.1.3
python3-saml==1.15.0
django-saml2==1.5.0
social-auth-app-django==5.2.0
lti==1.3.0
celery==5.3.4
redis==4.5.5
gunicorn==21.2.0
EOF

# Create client requirements file
cat > "$MOUNT_POINT/client_requirements.txt" << 'EOF'
# NIR Intelligence Platform - Client Requirements
requests==2.31.0
ansible==8.0.0
docker==6.1.3
python3-saml==1.15.0
python-dotenv==1.0.0
pandas==2.0.3
numpy==1.24.3
EOF

echo "✓ Deployment scripts created"

# Create sample data
cat > "$MOUNT_POINT/data/raw/sample_spectrum.csv" << 'EOF'
wavelength,intensity,instrument,acquisition_time,sample
900,0.123,DIY_Spectrometer,2026-07-30T10:00:00,test_sample_1
950,0.187,DIY_Spectrometer,2026-07-30T10:00:00,test_sample_1
1000,0.254,DIY_Spectrometer,2026-07-30T10:00:00,test_sample_1
1050,0.312,DIY_Spectrometer,2026-07-30T10:00:00,test_sample_1
1100,0.289,DIY_Spectrometer,2026-07-30T10:00:00,test_sample_1
EOF

echo "✓ Sample data created"

# Create configuration files
cat > "$MOUNT_POINT/config/server_config.yaml" << 'EOF'
# NIR Intelligence Platform - Server Configuration

# Server settings
server:
  host: 0.0.0.0
  port: 8000
  debug: false
  secret_key: "change-this-in-production"
  allowed_hosts: ["localhost", "127.0.0.1"]

# Database settings
database:
  engine: django.db.backends.postgresql
  name: nir_db
  user: nir_user
  password: nir_password
  host: localhost
  port: 5432

# ILIAS Integration
ilias:
  base_url: "http://localhost:8081"
  api_key: "your_api_key"
  api_secret: "your_api_secret"
  sso_enabled: false
  sync_frequency: "daily"
  course_prefix: "NIR_"

# Federated Learning
flower:
  server_address: "0.0.0.0"
  server_port: 5555
  client_port: 5556
  rounds: 3
  min_clients: 2

# File upload settings
file_upload:
  max_size: 104857600  # 100MB
  allowed_types: [".csv", ".json", ".h5", ".jdx", ".spc", ".txt", ".zip"]

# Logging
logging:
  version: 1
  disable_existing_loggers: false
  handlers:
    file:
      level: DEBUG
      class: logging.FileHandler
      filename: /var/log/nir/server.log
  root:
    handlers: [file]
    level: DEBUG
EOF

cat > "$MOUNT_POINT/config/client_config.yaml" << 'EOF'
# NIR Intelligence Platform - Client Configuration

# Server connection
server:
  url: "http://localhost:8000"
  api_key: "client_api_key"
  api_secret: "client_api_secret"

# Local cache settings
cache:
  directory: /var/cache/nir
  size: 5368709120  # 5GB
  expiration: 2592000  # 30 days

# File settings
files:
  local_storage: /var/lib/nir/data
  max_upload_size: 52428800  # 50MB

# Federated learning
flower_client:
  server_address: "localhost"
  server_port: 5555
  client_port: 5556
  auto_start: false

# Logging
logging:
  version: 1
  disable_existing_loggers: false
  handlers:
    file:
      level: DEBUG
      class: logging.FileHandler
      filename: /var/log/nir/client.log
  root:
    handlers: [file]
    level: DEBUG
EOF

echo "✓ Configuration files created"

# Create documentation
cat > "$MOUNT_POINT/docs/INSTALLATION.md" << 'EOF'
# NIR Intelligence Platform - Installation Guide

## Prerequisites

### Hardware Requirements
- **Server**: 4GB RAM, 20GB disk space, 2+ CPU cores
- **Client**: 2GB RAM, 10GB disk space, 1+ CPU core
- **Network**: HTTPS connectivity between server and clients

### Software Requirements
- **Operating System**: Ubuntu 22.04 LTS or later
- **Python**: 3.12 or higher
- **Ansible**: 2.15 or higher
- **Docker**: 24.0 or higher (for containerized components)
- **PostgreSQL**: 15 or higher

## Installation Methods

### Method 1: USB Bootable Ansible (Recommended)

1. **Insert USB drive** into target server/client
2. **Mount the USB drive**:
   ```bash
   sudo mkdir -p /mnt/usb
   sudo mount /dev/sdX1 /mnt/usb
   ```
3. **Navigate to USB drive**:
   ```bash
   cd /mnt/usb
   ```
4. **Run deployment script**:
   - For server: `sudo bash scripts/server/deploy_server.sh`
   - For client: `sudo bash scripts/client/deploy_client.sh`

### Method 2: Manual Installation

1. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip ansible docker.io postgresql postgresql-contrib
   ```

2. **Install Python packages**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Ansible playbooks**:
   ```bash
   cd ansible
   ansible-playbook playbooks/server_deployment.yml -i inventory.ini
   ```

## Post-Installation

### Server Configuration
1. Edit configuration: `/etc/nir/server_config.yaml`
2. Set up database: `sudo -u postgres createdb nir_db`
3. Create database user: `sudo -u postgres createuser -P nir_user`
4. Start services: `sudo systemctl start nir-server`

### Client Configuration
1. Edit configuration: `/etc/nir/client_config.yaml`
2. Set server URL and API keys
3. Start client service: `sudo systemctl start nir-client`

## Troubleshooting

### Common Issues

**Issue: Port already in use**
```bash
sudo lsof -i :8000
sudo kill -9 <PID>
```

**Issue: Database connection failed**
```bash
sudo systemctl restart postgresql
sudo -u postgres psql -c "ALTER USER nir_user WITH PASSWORD 'nir_password';"
```

**Issue: Ansible playbook failed**
```bash
ansible-playbook playbooks/server_deployment.yml -i inventory.ini -vvv
```

## Support

For additional help:
- **Documentation**: https://docs.nir-platform.org
- **Support Email**: support@nir-platform.org
- **Community Forum**: https://community.nir-platform.org

## License

NIR Intelligence Platform © 2026
All rights reserved
EOF

echo "✓ Installation guide created"

# Create quick start guide
cat > "$MOUNT_POINT/docs/QUICKSTART.md" << 'EOF'
# NIR Intelligence Platform - Quick Start Guide

## 5-Minute Setup

### 1. Insert USB Drive
```bash
lsblk  # Find your USB device (e.g., sdb1)
sudo mount /dev/sdb1 /mnt/usb
cd /mnt/usb
```

### 2. Deploy Server
```bash
sudo bash scripts/server/deploy_server.sh
```

### 3. Deploy Client
```bash
sudo bash scripts/client/deploy_client.sh
```

### 4. Access Platform
- **Server**: http://localhost:8000
- **Admin**: http://localhost:8000/admin
- **API Docs**: http://localhost:8000/api/docs

## Common Commands

### Start Services
```bash
# Server
sudo systemctl start nir-server

# Client
sudo systemctl start nir-client

# Database
sudo systemctl start postgresql
```

### Stop Services
```bash
# Server
sudo systemctl stop nir-server

# Client
sudo systemctl stop nir-client

# Database
sudo systemctl stop postgresql
```

### Check Status
```bash
# Server
sudo systemctl status nir-server

# Client
sudo systemctl status nir-client

# Logs
journalctl -u nir-server -f
```

## Testing

### Run Tests
```bash
# Mock tests (no Docker required)
bash test_ilias_integration.sh

# Full tests (with Docker)
bash run_tests.sh
```

### Test API
```bash
# Health check
curl http://localhost:8000/api/health

# List courses
curl http://localhost:8000/api/courses

# User sync
curl -X POST http://localhost:8000/api/users/sync \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "email": "test@example.com"}'
```

## ILIAS Integration

### Test ILIAS Connection
```bash
# Health check
curl http://localhost:8081/api/health

# List courses
curl http://localhost:8081/api/courses

# Sync user
curl -X POST http://localhost:8081/api/users/sync \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "email": "test@example.com"}'
```

## Troubleshooting Quick Fixes

### Reset Database
```bash
sudo -u postgres dropdb nir_db
sudo -u postgres createdb nir_db
sudo -u postgres psql -c "CREATE USER nir_user WITH PASSWORD 'nir_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE nir_db TO nir_user;"
```

### Reinstall Dependencies
```bash
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

### Restart All Services
```bash
sudo systemctl restart nir-server nir-client postgresql docker
```

## Contact

Need help? Contact support:
- **Email**: support@nir-platform.org
- **Phone**: +1 (555) 123-4567
- **Web**: https://support.nir-platform.org
EOF

echo "✓ Quick start guide created"

# Create version info
cat > "$MOUNT_POINT/VERSION.txt" << 'EOF'
NIR Intelligence Platform - USB Bootable Ansible
================================================

Version: 1.0.0
Build Date: 2026-07-30
Build Type: USB Bootable Ansible

Components:
- Server: 1.0.0
- Client: 1.0.0
- ILIAS Integration: 1.0.0
- Ansible Playbooks: 1.0.0

Features:
✓ Complete offline deployment
✓ Server and client installation
✓ ILIAS integration setup
✓ Sample data included
✓ Configuration templates
✓ Documentation included

Requirements:
- Ubuntu 22.04+ recommended
- Python 3.12+
- Ansible 2.15+
- Minimum 4GB RAM for server
- Minimum 2GB RAM for client

Support:
- Documentation: https://docs.nir-platform.org
- Support: support@nir-platform.org
- Community: https://community.nir-platform.org

License:
NIR Intelligence Platform © 2026
All rights reserved
EOF

echo "✓ Version information created"

# Unmount USB device
echo "6. Unmounting USB device..."
sync
sleep 2
umount "$MOUNT_POINT"
if [ $? -eq 0 ]; then
    echo "✓ USB device unmounted successfully"
else
    echo "⚠ Warning: Failed to unmount USB device"
fi

# Clean up
echo "7. Cleaning up..."
rmdir "$MOUNT_POINT"
echo "✓ Cleanup completed"

echo ""
echo "=========================================="
echo "USB Bootable Ansible Created Successfully!"
echo "=========================================="
echo ""
echo "USB Device: /dev/${USB_DEVICE}"
echo "Label: NIR_Ansible"
echo "Size: $(lsblk -d -o SIZE /dev/${USB_DEVICE} | grep -v SIZE)"
echo ""
echo "Contents:"
echo "  ✓ Ansible playbooks for server and client"
echo "  ✓ Deployment scripts"
echo "  ✓ Configuration templates"
echo "  ✓ Sample data"
echo "  ✓ Documentation"
echo "  ✓ Version information"
echo ""
echo "Usage:"
echo "  1. Insert USB into target machine"
echo "  2. Mount: sudo mount /dev/${USB_DEVICE}1 /mnt/usb"
echo "  3. Deploy Server: sudo bash /mnt/usb/scripts/server/deploy_server.sh"
echo "  4. Deploy Client: sudo bash /mnt/usb/scripts/client/deploy_client.sh"
echo ""
echo "Note: This USB contains a complete offline deployment system"
echo "for the NIR Intelligence Platform with ILIAS integration."
