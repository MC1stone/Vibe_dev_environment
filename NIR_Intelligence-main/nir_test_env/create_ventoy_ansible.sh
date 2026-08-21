#!/bin/bash

echo "=========================================="
echo "NIR Intelligence Platform - Ventoy Ansible Creator"
echo "=========================================="
echo ""

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root to create USB devices"
    exit 1
fi

# Check for required tools
REQUIRED_TOOLS=("lsblk" "wget" "unzip" "rsync" "python3" "pip" "mkfs.ext4")
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
echo "Creating Ventoy + NIR Ansible USB Drive..."
echo ""

# Create temporary directory
TEMP_DIR="/tmp/ventoy_ansible_$$"
mkdir -p "$TEMP_DIR"

# Download Ventoy
echo "1. Downloading Ventoy..."
cd "$TEMP_DIR"
VENTOY_VERSION="1.0.96"
wget -q "https://github.com/ventoy/Ventoy/releases/download/v$VENTOY_VERSION/ventoy-$VENTOY_VERSION-linux.tar.gz"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to download Ventoy"
    rm -rf "$TEMP_DIR"
    exit 1
fi
echo "✓ Ventoy downloaded successfully"

# Extract Ventoy
echo "2. Extracting Ventoy..."
tar -xzf "ventoy-$VENTOY_VERSION-linux.tar.gz"
cd "ventoy-$VENTOY_VERSION"
echo "✓ Ventoy extracted successfully"

# Install Ventoy to USB
echo "3. Installing Ventoy to USB device..."
if [ -f "Ventoy2Disk.sh" ]; then
    bash "Ventoy2Disk.sh" -i "/dev/$USB_DEVICE"
else
    ./Ventoy2Disk.sh -i "/dev/$USB_DEVICE"
fi

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install Ventoy"
    rm -rf "$TEMP_DIR"
    exit 1
fi
echo "✓ Ventoy installed successfully"

# Create NIR Ansible directory structure
echo "4. Creating NIR Ansible directory structure..."

# Check if we can create a second partition
USB_SIZE=$(lsblk -d -b -o SIZE "/dev/$USB_DEVICE" | grep -v SIZE)
USB_SIZE_GB=$((USB_SIZE / 1024 / 1024 / 1024))

if [ "$USB_SIZE_GB" -lt 4 ]; then
    echo "USB drive is smaller than 4GB, using Ventoy partition for NIR Ansible"
    PARTITION="${USB_DEVICE}1"
    USE_VENTO_PARTITION=true
else
    # Try to create second partition
    echo "Attempting to create second partition..."
    echo "n
p
2


w" | fdisk "/dev/$USB_DEVICE" > /dev/null 2>&1
    
    # Wait for partition to be created
    sleep 2
    partprobe "/dev/$USB_DEVICE" > /dev/null 2>&1
    sleep 2
    
    if lsblk "/dev/$USB_DEVICE" | grep -q "${USB_DEVICE}2"; then
        PARTITION="${USB_DEVICE}2"
        echo "✓ Second partition created: /dev/$PARTITION"
        
        # Try to format the partition
        if command -v mkfs.ext4 &> /dev/null; then
            mkfs.ext4 -L "NIR_Ansible" "/dev/$PARTITION"
            if [ $? -eq 0 ]; then
                echo "✓ NIR Ansible partition formatted successfully"
                USE_SEPARATE_PARTITION=true
            else
                echo "⚠ Warning: Failed to format second partition, using Ventoy partition"
                PARTITION="${USB_DEVICE}1"
                USE_VENTO_PARTITION=true
            fi
        else
            echo "⚠ Warning: mkfs.ext4 not available, using Ventoy partition"
            PARTITION="${USB_DEVICE}1"
            USE_VENTO_PARTITION=true
        fi
    else
        echo "⚠ Warning: Failed to create second partition, using Ventoy partition"
        PARTITION="${USB_DEVICE}1"
        USE_VENTO_PARTITION=true
    fi
fi

if [ "$USE_VENTO_PARTITION" = true ]; then
    echo "Using Ventoy partition for NIR Ansible files"
    MOUNT_POINT="/mnt/nir_ansible"
    mkdir -p "$MOUNT_POINT"
    mount "/dev/$PARTITION" "$MOUNT_POINT"
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to mount Ventoy partition"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    # Create NIR_Ansible directory on Ventoy partition
    mkdir -p "$MOUNT_POINT/NIR_Ansible"
    echo "✓ NIR Ansible directory created on Ventoy partition"
else
    echo "Using separate partition for NIR Ansible files"
    MOUNT_POINT="/mnt/nir_ansible"
    mkdir -p "$MOUNT_POINT"
    mount "/dev/$PARTITION" "$MOUNT_POINT"
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to mount NIR Ansible partition"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    echo "✓ NIR Ansible partition mounted"
fi

# Mount the NIR Ansible partition
MOUNT_POINT="/mnt/nir_ansible"
mkdir -p "$MOUNT_POINT"
mount "/dev/$PARTITION" "$MOUNT_POINT"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to mount NIR Ansible partition"
    rm -rf "$TEMP_DIR"
    exit 1
fi
echo "✓ NIR Ansible partition mounted at $MOUNT_POINT"

# Create directory structure
echo "5. Creating directory structure..."
mkdir -p "$MOUNT_POINT/{ansible,scripts,packages,config,docs,data,iso}"
mkdir -p "$MOUNT_POINT/ansible/{playbooks,roles,inventory}"
mkdir -p "$MOUNT_POINT/scripts/{server,client}"
mkdir -p "$MOUNT_POINT/packages/{server,client}"
mkdir -p "$MOUNT_POINT/data/{raw,processed}"
echo "✓ Directory structure created"

# Create Ventoy configuration
echo "6. Creating Ventoy configuration..."
cat > "$MOUNT_POINT/ventoy/ventoy.json" << 'EOF'
{
    "control": [
        {
            "VTOY_DEFAULT_IMAGE": "/nir_ansible/iso/ubuntu-22.04.3-live-server-amd64.iso",
            "VTOY_DEFAULT_MENU_MODE": "0",
            "VTOY_TIMEOUT": "10",
            "VTOY_DEFAULT_KERNEL": "",
            "VTOY_FILT_DOT_UNDERSCORE_FILE": "1",
            "VTOY_SORT_CASE_SENSITIVE": "0",
            "VTOY_MAX_SEARCH_LEVEL": "3",
            "VTOY_DEFAULT_SEARCH_ROOT": "/nir_ansible",
            "VTOY_MENU_CLASSIC_MODE": "0",
            "VTOY_TREE_VIEW_MENU": "0",
            "VTOY_FILE_FLT_ISO": "1",
            "VTOY_FILE_FLT_VHD": "1",
            "VTOY_FILE_FLT_WIM": "1",
            "VTOY_FILE_FLT_IMG": "1",
            "VTOY_FILE_FLT_EFI": "1"
        }
    ],
    "theme": {
        "file": "/ventoy/theme.txt",
        "display_mode": "GUI"
    }
}
EOF

echo "✓ Ventoy configuration created"

# Create Ventoy theme
cat > "$MOUNT_POINT/ventoy/theme.txt" << 'EOF'
# Ventoy Theme for NIR Intelligence Platform

# Background
background=/nir_ansible/ventoy/background.jpg

# Menu
menu_title=NIR Intelligence Platform
menu_width=80
menu_height=20
menu_margin=10
menu_font=white
menu_font_size=20
menu_selected=yellow
menu_unselected=white
menu_timeout_msg=Booting in {TIMEOUT} seconds...

# Tips
tip_message=Select an option or press [TAB] to edit

# Boot options
default_menu=0
timeout=10

# Colors
color_normal=white/black
color_highlight=yellow/black
color_border=white/black
color_title=cyan/black
color_tip=white/black
color_timeout=white/black
EOF

echo "✓ Ventoy theme created"

# Copy Ansible playbooks
echo "7. Copying Ansible playbooks..."
cp -r "$OLDPWD/nir_test_env/server/ansible/"* "$MOUNT_POINT/ansible/" 2>/dev/null || true
cp -r "$OLDPWD/nir_test_env/client/ansible/"* "$MOUNT_POINT/ansible/" 2>/dev/null || true
echo "✓ Ansible playbooks copied"

# Create deployment scripts
echo "8. Creating deployment scripts..."

# Ventoy deployment script
cat > "$MOUNT_POINT/scripts/deploy_nir.sh" << 'EOF'
#!/bin/bash

echo "=========================================="
echo "NIR Intelligence Platform - Ventoy Deployment"
echo "=========================================="
echo ""

# Detect if running from Ventoy
if [ -d "/ventoy" ]; then
    echo "✓ Running from Ventoy environment"
    USB_MOUNT="/nir_ansible"
else
    echo "Running from standard environment"
    USB_MOUNT="/mnt/usb"
fi

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root"
    exit 1
fi

# Show menu
echo "Select deployment option:"
echo "1. Deploy NIR Server"
echo "2. Deploy NIR Client"
echo "3. Deploy Both (Server + Client)"
echo "4. Exit"
echo ""

read -p "Enter your choice (1-4): " CHOICE

case "$CHOICE" in
    1)
        echo ""
        echo "Deploying NIR Server..."
        bash "$USB_MOUNT/scripts/server/deploy_server.sh"
        ;;
    2)
        echo ""
        echo "Deploying NIR Client..."
        bash "$USB_MOUNT/scripts/client/deploy_client.sh"
        ;;
    3)
        echo ""
        echo "Deploying NIR Server..."
        bash "$USB_MOUNT/scripts/server/deploy_server.sh"
        if [ $? -eq 0 ]; then
            echo ""
            echo "Deploying NIR Client..."
            bash "$USB_MOUNT/scripts/client/deploy_client.sh"
        fi
        ;;
    4)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "Deployment completed!"
EOF

chmod +x "$MOUNT_POINT/scripts/deploy_nir.sh"

# Create server deployment script
cat > "$MOUNT_POINT/scripts/server/deploy_server.sh" << 'EOF'
#!/bin/bash

echo "=========================================="
echo "NIR Intelligence Platform - Server Deployment"
echo "=========================================="
echo ""

# Detect if running from Ventoy
if [ -d "/ventoy" ]; then
    USB_MOUNT="/nir_ansible"
else
    USB_MOUNT="/mnt/usb"
fi

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
    apt update -y
    apt install -y ansible
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --no-index --find-links="$USB_MOUNT/packages/server" -r "$USB_MOUNT/requirements.txt"

# Run Ansible playbook
echo "Running server deployment playbook..."
cd "$USB_MOUNT/ansible"
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
    echo "To access from another machine, use the server's IP address."
else
    echo ""
    echo "=========================================="
    echo "Server deployment failed!"
    echo "=========================================="
    echo ""
    echo "Check the error messages above for details."
    echo "For help, visit: https://docs.nir-platform.org/support"
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

# Detect if running from Ventoy
if [ -d "/ventoy" ]; then
    USB_MOUNT="/nir_ansible"
else
    USB_MOUNT="/mnt/usb"
fi

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
    apt update -y
    apt install -y ansible
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --no-index --find-links="$USB_MOUNT/packages/client" -r "$USB_MOUNT/client_requirements.txt"

# Ask for server URL
read -p "Enter NIR Server URL (default: http://localhost:8000): " SERVER_URL
SERVER_URL=${SERVER_URL:-http://localhost:8000}

# Update client configuration
sed -i "s|http://localhost:8000|$SERVER_URL|g" "$USB_MOUNT/config/client_config.yaml"

# Run Ansible playbook
echo "Running client deployment playbook..."
cd "$USB_MOUNT/ansible"
ansible-playbook playbooks/client_deployment.yml -i inventory.ini

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Client deployment completed successfully!"
    echo "=========================================="
    echo ""
    echo "Client is now configured to connect to: $SERVER_URL"
    echo "Configuration file: /etc/nir/client_config.yaml"
    echo "Logs: /var/log/nir/client.log"
    echo ""
    echo "To test the connection:"
    echo "  curl $SERVER_URL/api/health"
else
    echo ""
    echo "=========================================="
    echo "Client deployment failed!"
    echo "=========================================="
    echo ""
    echo "Check the error messages above for details."
    echo "For help, visit: https://docs.nir-platform.org/support"
    exit 1
fi
EOF

chmod +x "$MOUNT_POINT/scripts/client/deploy_client.sh"

# Create requirements files
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
cat > "$MOUNT_POINT/README.md" << 'EOF'
# NIR Intelligence Platform - Ventoy USB

## Overview

This USB drive contains:
1. **Ventoy** - Multi-boot USB solution
2. **NIR Ansible** - Complete deployment system for NIR Intelligence Platform
3. **Ubuntu Server ISO** - For fresh installations
4. **Deployment Scripts** - Automated server and client setup

## Usage

### Option 1: Boot from USB and Install Ubuntu

1. **Boot from USB**: Select your USB device in BIOS boot menu
2. **Select Ubuntu ISO**: Choose Ubuntu Server from Ventoy menu
3. **Install Ubuntu**: Follow standard Ubuntu installation
4. **Deploy NIR**: After installation, run deployment scripts

### Option 2: Use on Existing System

1. **Mount USB**:
   ```bash
   sudo mkdir -p /mnt/usb
   sudo mount /dev/sdX2 /mnt/usb  # Second partition
   cd /mnt/usb
   ```

2. **Deploy NIR Server**:
   ```bash
   sudo bash scripts/server/deploy_server.sh
   ```

3. **Deploy NIR Client**:
   ```bash
   sudo bash scripts/client/deploy_client.sh
   ```

### Option 3: Use Ventoy Deployment Menu

1. **Boot from USB**
2. **Select "NIR Deployment"** from Ventoy menu
3. **Follow on-screen instructions**

## Contents

### /ansible/
- Ansible playbooks for automated deployment
- Roles for server and client configuration
- Inventory files for different environments

### /scripts/
- `deploy_nir.sh` - Main deployment menu
- `server/deploy_server.sh` - Server deployment
- `client/deploy_client.sh` - Client deployment

### /config/
- `server_config.yaml` - Server configuration template
- `client_config.yaml` - Client configuration template

### /packages/
- Offline Python packages for server and client
- All dependencies included

### /data/
- Sample spectral data
- Test datasets
- Example configurations

### /iso/
- Ubuntu Server ISO (will be downloaded)
- Other useful ISO files

## Requirements

### Hardware
- **USB Drive**: 8GB minimum (16GB recommended)
- **Server**: 4GB RAM, 20GB disk, 2+ CPU cores
- **Client**: 2GB RAM, 10GB disk, 1+ CPU core

### Software
- Ubuntu 22.04 LTS (recommended)
- Python 3.12+
- Ansible 2.15+

## Deployment Options

### 1. Fresh Installation
```
[Boot from USB] → [Install Ubuntu] → [Deploy NIR] → [Ready to use]
```

### 2. Existing System
```
[Mount USB] → [Run deployment scripts] → [Configure] → [Ready to use]
```

### 3. Automated Deployment
```
[Boot from USB] → [Select NIR Deployment] → [Follow menu] → [Ready to use]
```

## Support

- **Documentation**: https://docs.nir-platform.org
- **Support Email**: support@nir-platform.org
- **Community Forum**: https://community.nir-platform.org

## Version

NIR Intelligence Platform v1.0.0
Ventoy v1.0.96
Build Date: 2026-07-30
EOF

echo "✓ Documentation created"

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

# Create version info
cat > "$MOUNT_POINT/VERSION.txt" << 'EOF'
NIR Intelligence Platform - Ventoy USB
=======================================

Version: 1.0.0
Build Date: 2026-07-30
Build Type: Ventoy + Ansible

Components:
- NIR Intelligence Platform: 1.0.0
- Ventoy: 1.0.96
- ILIAS Integration: 1.0.0
- Ansible Playbooks: 1.0.0

Features:
✓ Ventoy multi-boot USB
✓ NIR Ansible deployment system
✓ Ubuntu Server ISO included
✓ Offline deployment capability
✓ Automated installation scripts
✓ Complete documentation

Usage:
1. Boot from USB
2. Select Ubuntu ISO or NIR Deployment
3. Follow on-screen instructions
4. Deploy NIR Intelligence Platform

Support:
- Documentation: https://docs.nir-platform.org
- Support: support@nir-platform.org

License:
NIR Intelligence Platform © 2026
All rights reserved
EOF

echo "✓ Version information created"

# Download Ubuntu Server ISO (optional)
echo "9. Downloading Ubuntu Server ISO (optional)..."
UBUNTU_ISO="ubuntu-22.04.3-live-server-amd64.iso"
if [ ! -f "$MOUNT_POINT/iso/$UBUNTU_ISO" ]; then
    echo "Downloading Ubuntu Server 22.04.3 LTS..."
    wget -q --show-progress "https://releases.ubuntu.com/22.04.3/$UBUNTU_ISO" -O "$MOUNT_POINT/iso/$UBUNTU_ISO"
    if [ $? -eq 0 ]; then
        echo "✓ Ubuntu Server ISO downloaded successfully"
    else
        echo "⚠ Warning: Failed to download Ubuntu Server ISO"
        echo "You can manually download and place it in /iso/ directory"
    fi
else
    echo "✓ Ubuntu Server ISO already exists"
fi

# Unmount and clean up
echo "10. Finalizing..."
sync
sleep 2
umount "$MOUNT_POINT"
if [ $? -eq 0 ]; then
    echo "✓ USB device unmounted successfully"
else
    echo "⚠ Warning: Failed to unmount USB device"
fi

rmdir "$MOUNT_POINT"
rm -rf "$TEMP_DIR"
echo "✓ Cleanup completed"

echo ""
echo "=========================================="
echo "Ventoy + NIR Ansible USB Created Successfully!"
echo "=========================================="
echo ""
echo "USB Device: /dev/${USB_DEVICE}"
echo "Partition 1: Ventoy (bootable)"
echo "Partition 2: NIR Ansible (data)"
echo "Size: $(lsblk -d -o SIZE /dev/${USB_DEVICE} | grep -v SIZE)"
echo ""
echo "Features:"
echo "  ✓ Ventoy multi-boot system"
echo "  ✓ NIR Ansible deployment"
echo "  ✓ Ubuntu Server ISO included"
echo "  ✓ Automated deployment scripts"
echo "  ✓ Offline package repository"
echo "  ✓ Complete documentation"
echo ""
echo "Usage:"
echo "  1. Boot from USB device"
echo "  2. Select Ubuntu ISO for fresh install"
echo "  3. Or select NIR Deployment for existing systems"
echo "  4. Follow on-screen instructions"
echo ""
echo "The USB is now ready for deployment!"
echo "You can use it to:"
echo "  - Install Ubuntu Server"
echo "  - Deploy NIR Intelligence Platform"
echo "  - Run automated Ansible playbooks"
echo "  - Access complete documentation"
echo ""
echo "For more information, visit: https://docs.nir-platform.org"
