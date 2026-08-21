# 🚀 Ventoy USB Stick Preparation Guide for NIR_Mistral Framework

## 📋 Overview

This guide explains how to prepare a **Ventoy USB stick** for running the **NIR_Mistral Framework** with Django Server and Port Agent. Ventoy is a tool that allows you to create a bootable USB drive that can contain multiple ISO files, making it perfect for deploying your framework on any system.

## 🎯 What You'll Need

### Hardware Requirements
- **USB Stick**: 16GB or larger (32GB recommended)
- **Computer**: Any system with USB port (Linux, Windows, or Mac)
- **Target System**: Any x86_64 system to boot from the Ventoy stick

### Software Requirements
- **Ventoy**: Latest version (currently 1.0.96)
- **Ansible**: For automated deployment (optional but recommended)
- **Python 3**: For running the framework

## 📥 Step 1: Download Ventoy

### Option A: Download from GitHub

```bash
# Download Ventoy for Linux
wget https://github.com/ventoy/Ventoy/releases/download/v1.0.96/ventoy-1.0.96-linux.tar.gz

# Extract the archive
tar -xzvf ventoy-1.0.96-linux.tar.gz

# Navigate to Ventoy directory
cd ventoy-1.0.96
```

### Option B: Download for Windows

1. Visit: https://github.com/ventoy/Ventoy/releases
2. Download: `ventoy-1.0.96-windows.zip`
3. Extract the ZIP file
4. Open Command Prompt in the extracted folder

### Option C: Download for Mac

```bash
# Download Ventoy for Mac (using Homebrew)
brew install ventoy

# Or download manually
wget https://github.com/ventoy/Ventoy/releases/download/v1.0.96/ventoy-1.0.96-mac.tar.gz
tar -xzvf ventoy-1.0.96-mac.tar.gz
cd ventoy-1.0.96
```

## 💾 Step 2: Install Ventoy to USB Stick

### ⚠️ IMPORTANT: Backup Your USB Stick

**All data on your USB stick will be erased!**

```bash
# List all disks to identify your USB stick
lsblk

# Or on Windows
wmic diskdrive list brief

# Or on Mac
diskutil list
```

**Identify your USB stick device name:**
- Linux: Typically `/dev/sdX` (where X is b, c, d, etc.)
- Windows: Typically `\\.\PHYSICALDRIVE1` or similar
- Mac: Typically `/dev/disk2` or similar

### Install Ventoy (Linux)

```bash
# Make sure you're in the Ventoy directory
cd ventoy-1.0.96

# Install Ventoy to your USB stick (replace sdX with your USB device)
# ⚠️ THIS WILL ERASE ALL DATA ON THE USB STICK
sudo ./Ventoy2Disk.sh -i /dev/sdX

# Example (replace X with your actual device):
# sudo ./Ventoy2Disk.sh -i /dev/sdb
```

### Install Ventoy (Windows)

```cmd
# Open Command Prompt as Administrator
cd ventoy-1.0.96

# Install Ventoy to your USB stick (replace X with your disk number)
# ⚠️ THIS WILL ERASE ALL DATA ON THE USB STICK
Ventoy2Disk.exe -i \\.\PHYSICALDRIVEX

# Example (replace X with your actual disk number):
# Ventoy2Disk.exe -i \\.\PHYSICALDRIVE1
```

### Install Ventoy (Mac)

```bash
# Make sure you're in the Ventoy directory
cd ventoy-1.0.96

# Install Ventoy to your USB stick (replace diskX with your USB device)
# ⚠️ THIS WILL ERASE ALL DATA ON THE USB STICK
sudo ./Ventoy2Disk.sh -i /dev/diskX

# Example (replace X with your actual device):
# sudo ./Ventoy2Disk.sh -i /dev/disk2
```

### Verify Installation

After installation, you should see:
```
Ventoy is installed to /dev/sdX successfully.
```

## 📁 Step 3: Prepare NIR_Mistral Files

### Option A: Using Ansible (Recommended)

```bash
# Navigate to the Ansible Ventoy setup directory
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/ansible/ventoy_setup

# Run the Ansible playbook to prepare files
ansible-playbook site.yml -e "skip_ventoy=true"

# This will create all necessary files in /opt/nir_mistral/
```

### Option B: Manual Preparation

```bash
# Create deployment directory
mkdir -p /mnt/ventoy/nir_mistral

# Copy Django project
cp -r /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project /mnt/ventoy/nir_mistral/

# Copy Port Agent
cp -r /home/martin/Development/vsCode_Environment/NIR_Mistral/agents /mnt/ventoy/nir_mistral/

# Create virtual environment
cd /mnt/ventoy/nir_mistral
python3 -m venv venv

# Install dependencies
source venv/bin/activate
pip install -r django_project/requirements.txt
pip install -r agents/port_agent/requirements.txt

# Create logs directory
mkdir -p /mnt/ventoy/nir_mistral/logs

# Create data directory
mkdir -p /mnt/ventoy/nir_mistral/data
```

## 🎨 Step 4: Copy Files to Ventoy Stick

### Mount the Ventoy Stick

```bash
# Create mount point
sudo mkdir -p /mnt/ventoy

# Mount the Ventoy stick (replace sdX with your USB device)
sudo mount /dev/sdX1 /mnt/ventoy

# Navigate to the mounted Ventoy stick
cd /mnt/ventoy
```

### Copy NIR_Mistral Files

```bash
# Copy the prepared NIR_Mistral directory to the Ventoy stick
sudo cp -r /opt/nir_mistral /mnt/ventoy/

# Or if you prepared manually:
sudo cp -r /mnt/ventoy/nir_mistral /mnt/ventoy/
```

### Create Ventoy Configuration

```bash
# Create the ventoy directory on the stick
sudo mkdir -p /mnt/ventoy/ventoy

# Copy Ventoy configuration files from Ansible setup
sudo cp /home/martin/Development/vsCode_Environment/NIR_Mistral/ansible/ventoy_setup/roles/ventoy_config/templates/*.j2 /mnt/ventoy/ventoy/

# Rename .j2 files to remove template extension
cd /mnt/ventoy/ventoy
for file in *.j2; do
    sudo mv "$file" "${file%.j2}"
done
```

### Create Ventoy Themes Directory

```bash
# Create themes directory
sudo mkdir -p /mnt/ventoy/ventoy/themes/nir_mistral

# Copy theme files (create basic theme files)
cat > /tmp/nir_mistral_theme.json << 'EOF'
{
    "theme": {
        "name": "nir_mistral",
        "version": "1.0.0",
        "description": "NIR_Mistral Framework Theme",
        "author": "NIR_Mistral Team"
    },
    "colors": {
        "primary": "#e94560",
        "secondary": "#16213e",
        "background": "#1a1a2e",
        "foreground": "#ffffff"
    }
}
EOF

sudo cp /tmp/nir_mistral_theme.json /mnt/ventoy/ventoy/themes/nir_mistral/theme.json
```

## 📋 Step 5: Configure Ventoy Menu

### Create Ventoy Configuration File

```bash
# Create ventoy.json configuration
cat > /mnt/ventoy/ventoy/ventoy.json << 'EOF'
{
    "ventoy": {
        "version": "1.0.96",
        "configuration": {
            "theme": "nir_mistral",
            "default_selection": "NIR_Mistral Framework",
            "timeout": 10,
            "auto_boot": true,
            "menu_style": "graphical"
        }
    }
}
EOF
```

### Create Custom Menu Configuration

```bash
cat > /mnt/ventoy/ventoy/ventoy_menu.conf << 'EOF'
menu_title = "NIR_Mistral Framework - Ventoy Stick"
menu_subtitle = "Select an option to start"
menu_timeout = 10
menu_default = "NIR_Mistral Framework"
menu_auto_boot = true

menu_items = [
    {
        "id": "nir_mistral",
        "name": "NIR_Mistral Framework",
        "description": "Start Django Server and Port Agent",
        "boot_type": "script",
        "script": "/nir_mistral/start_nir_mistral.sh",
        "auto_boot": true,
        "default": true
    },
    {
        "id": "nir_mistral_debug",
        "name": "NIR_Mistral Framework (Debug)",
        "description": "Start with debug mode",
        "boot_type": "script",
        "script": "/nir_mistral/start_nir_mistral.sh --debug",
        "auto_boot": false
    },
    {
        "id": "django_only",
        "name": "Django Server Only",
        "description": "Start only Django server",
        "boot_type": "script",
        "script": "/nir_mistral/start_nir_mistral.sh start django",
        "auto_boot": false
    },
    {
        "id": "port_agent_only",
        "name": "Port Agent Only",
        "description": "Start only Port Agent",
        "boot_type": "script",
        "script": "/nir_mistral/start_nir_mistral.sh start port_agent",
        "auto_boot": false
    },
    {
        "id": "stop_services",
        "name": "Stop All Services",
        "description": "Stop all services",
        "boot_type": "script",
        "script": "/nir_mistral/start_nir_mistral.sh stop",
        "auto_boot": false
    },
    {
        "id": "status",
        "name": "Check Status",
        "description": "Check service status",
        "boot_type": "script",
        "script": "/nir_mistral/start_nir_mistral.sh status",
        "auto_boot": false
    }
]
EOF
```

## 🚀 Step 6: Create Startup Scripts

### Create Main Startup Script

```bash
cat > /mnt/ventoy/nir_mistral/start_nir_mistral.sh << 'SCRIPT'
#!/bin/bash
# NIR_Mistral Startup Script

PROJECT_ROOT="/nir_mistral"
DJANGO_PROJECT="${PROJECT_ROOT}/django_project"
PORT_AGENT_PATH="${PROJECT_ROOT}/agents/port_agent"
VENV_PATH="${PROJECT_ROOT}/venv"
DJANGO_PORT=8000
PORT_AGENT_PORT=8001
LOG_DIR="${PROJECT_ROOT}/logs"

# Create directories
mkdir -p "${LOG_DIR}"

# Start Port Agent
start_port_agent() {
    cd "${PORT_AGENT_PATH}"
    nohup ${VENV_PATH}/bin/python -c "
from agents.port_agent.agent import port_agent
from agents.port_agent.server import create_app
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('${LOG_DIR}/port_agent.log'),
        logging.StreamHandler()
    ]
)

result = port_agent.initialize()
app = create_app()
app.run(host='0.0.0.0', port=${PORT_AGENT_PORT}, debug=False)
" > "${LOG_DIR}/port_agent.log" 2>&1 &
}

# Start Django
start_django() {
    cd "${DJANGO_PROJECT}"
    nohup ${VENV_PATH}/bin/python manage.py runserver 0.0.0.0:${DJANGO_PORT} > "${LOG_DIR}/django.log" 2>&1 &
}

# Main
case "$1" in
    start)
        start_port_agent
        start_django
        ;;
    stop)
        pkill -f "python.*manage.py.*runserver"
        pkill -f "python.*port_agent"
        ;;
    status)
        echo "Django Server: $(pgrep -f 'python.*manage.py.*runserver' > /dev/null && echo 'RUNNING' || echo 'STOPPED')"
        echo "Port Agent: $(pgrep -f 'python.*port_agent' > /dev/null && echo 'RUNNING' || echo 'STOPPED')"
        ;;
    *)
        start_port_agent
        start_django
        ;;
esac
SCRIPT

# Make startup script executable
sudo chmod +x /mnt/ventoy/nir_mistral/start_nir_mistral.sh
```

### Create README File

```bash
cat > /mnt/ventoy/VENTOY_README.txt << 'EOF'
NIR_Mistral Framework - Ventoy Stick
====================================

This Ventoy stick contains the NIR_Mistral Framework with:
- Django Server (Port 8000)
- Port Management Agent (Port 8001)

To start the framework:
1. Boot from this Ventoy stick
2. Select "NIR_Mistral Framework" from the menu
3. Wait for services to start
4. Access the services:
   - Django: http://localhost:8000
   - Port Agent: http://localhost:8001

API Endpoints:
- Django Health: http://localhost:8000/api/health/
- Port Agent: http://localhost:8001/api/ports/
- Port Scan: http://localhost:8001/api/ports/scan/?start=8000&end=9000

Management Commands:
- Start: /nir_mistral/start_nir_mistral.sh start
- Stop: /nir_mistral/start_nir_mistral.sh stop
- Status: /nir_mistral/start_nir_mistral.sh status
EOF
```

## 🔧 Step 7: Final Configuration

### Set Proper Permissions

```bash
# Set permissions for all files
sudo chmod -R 755 /mnt/ventoy/nir_mistral/
sudo chmod -R 755 /mnt/ventoy/ventoy/

# Set executable permissions for scripts
sudo chmod +x /mnt/ventoy/nir_mistral/start_nir_mistral.sh
```

### Unmount the Ventoy Stick

```bash
# Sync changes to disk
sync

# Unmount the Ventoy stick
sudo umount /mnt/ventoy
```

## ✅ Step 8: Test the Ventoy Stick

### Boot from Ventoy Stick

1. **Insert the Ventoy stick** into your target system
2. **Boot from the USB stick** (may need to change boot order in BIOS)
3. **Select "NIR_Mistral Framework"** from the Ventoy menu
4. **Wait for services to start** (should take 10-30 seconds)

### Verify Services Are Running

```bash
# Check if Django is running
curl http://localhost:8000/api/health/

# Check if Port Agent is running
curl http://localhost:8001/api/ports/

# Check service status
/nir_mistral/start_nir_mistral.sh status
```

### Test API Endpoints

```bash
# Test Django health
curl http://localhost:8000/api/health/

# Test Port Agent
curl http://localhost:8001/api/ports/

# Test port scanning
curl "http://localhost:8001/api/ports/scan/?start=9000&end=9100"

# Test port assignment
curl -X POST http://localhost:8001/api/ports/assign/ \
  -H "Content-Type: application/json" \
  -d '{"start": 9500, "end": 9600, "service_name": "test_service"}'
```

## 🛠️ Troubleshooting

### Ventoy Stick Not Booting

1. **Check BIOS settings**: Ensure USB boot is enabled
2. **Try different USB port**: Some systems have issues with USB 3.0
3. **Reinstall Ventoy**: The installation may have failed
4. **Check USB stick**: Try a different USB stick

### Services Not Starting

1. **Check logs**:
   ```bash
   tail -f /nir_mistral/logs/django.log
   tail -f /nir_mistral/logs/port_agent.log
   ```

2. **Check dependencies**:
   ```bash
   python3 --version
   /nir_mistral/venv/bin/python --version
   ```

3. **Manual start**:
   ```bash
   cd /nir_mistral/django_project
   /nir_mistral/venv/bin/python manage.py runserver 0.0.0.0:8000
   ```

### Port Conflicts

1. **Check running processes**:
   ```bash
   ps aux | grep python
   netstat -tlnp | grep -E "8000|8001"
   ```

2. **Kill conflicting processes**:
   ```bash
   sudo kill -9 $(lsof -t -i :8000)
   sudo kill -9 $(lsof -t -i :8001)
   ```

### Missing Dependencies

1. **Install missing packages**:
   ```bash
   source /nir_mistral/venv/bin/activate
   pip install -r /nir_mistral/django_project/requirements.txt
   pip install -r /nir_mistral/agents/port_agent/requirements.txt
   ```

## 🔄 Update Process

### Update NIR_Mistral Framework on Ventoy Stick

1. **Mount the Ventoy stick**:
   ```bash
   sudo mount /dev/sdX1 /mnt/ventoy
   ```

2. **Update the files**:
   ```bash
   # Copy updated files
   sudo cp -r /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project /mnt/ventoy/nir_mistral/
   sudo cp -r /home/martin/Development/vsCode_Environment/NIR_Mistral/agents /mnt/ventoy/nir_mistral/
   
   # Update dependencies
   source /mnt/ventoy/nir_mistral/venv/bin/activate
   pip install -r /mnt/ventoy/nir_mistral/django_project/requirements.txt
   pip install -r /mnt/ventoy/nir_mistral/agents/port_agent/requirements.txt
   ```

3. **Unmount and test**:
   ```bash
   sync
   sudo umount /mnt/ventoy
   ```

## 📚 Alternative: Using Ansible for Complete Setup

For a more automated approach, you can use the Ansible playbook:

### 1. Install Ansible

```bash
sudo apt update
sudo apt install -y ansible
```

### 2. Configure Inventory

Edit `/home/martin/Development/vsCode_Environment/NIR_Mistral/ansible/ventoy_setup/inventory.ini`:

```ini
[ventoy_stick]
ventoy_host ansible_host=192.168.1.100 ansible_user=your_user

[ventoy_stick:vars]
project_root=/home/martin/Development/vsCode_Environment/NIR_Mistral
deploy_root=/mnt/ventoy/nir_mistral
ventoy_mount_point=/mnt/ventoy
```

### 3. Run Ansible Playbook

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/ansible/ventoy_setup
ansible-playbook site.yml
```

## 🏁 Conclusion

You now have a **fully functional Ventoy stick** with the **NIR_Mistral Framework**! 🎉

**What you can do:**
- ✅ Boot from the Ventoy stick on any system
- ✅ Start Django Server and Port Agent automatically
- ✅ Access REST API endpoints for port management
- ✅ Manage port conflicts intelligently
- ✅ Use Django management commands
- ✅ Monitor services through health checks

**Next Steps:**
1. Test the Ventoy stick on your target system
2. Verify all services are running
3. Test the API endpoints
4. Integrate with your applications
5. Customize the configuration as needed

---

**Need Help?**
- Check the logs in `/nir_mistral/logs/`
- Review the troubleshooting section above
- Check the main documentation at `/nir_mistral/VENTOY_README.txt`

*Generated by NIR_Mistral Framework*
*Version: 1.0.0*