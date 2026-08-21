# 💾 NIR Mistral Ventoy Stick Deployment Guide

## Local NIR Data Analysis Setup from USB Boot

**Status:** ✅ **PRODUCTION READY**  
**Deployment Method:** Ventoy USB Stick  
**Target:** Local NIR Spectral Analysis  
**Missing Features:** ILIAS Integration, Quarto Reports (not critical for local)

---

## 🎯 **OVERVIEW**

This guide provides instructions for deploying the **NIR Mistral Local NIR Data Analysis Platform** from a **Ventoy bootable USB stick**. The deployment uses **Ansible** for automation and creates a **production-ready local setup** for spectral analysis.

### **What You Get:**
- ✅ **Complete NIR Spectral Analysis Platform**
- ✅ **4 AI Agents** for analysis and recommendations
- ✅ **Professional Web Interface** with HSWT styling
- ✅ **Colorful UI/UX** with smooth animations
- ✅ **REST API** for integration
- ✅ **User Management** and authentication
- ✅ **Database** for spectra, jobs, and users
- ✅ **Production-ready** deployment

### **What's NOT Included (Not Critical for Local):**
- ❌ **ILIAS Integration** (future enhancement)
- ❌ **Quarto Report Rendering** (templates ready, engine optional)
- ❌ **Federated Learning UI** (framework ready, UI pending)

---

## 📋 **PREREQUISITES**

### **Hardware Requirements**
- **Ventoy USB Stick** (16GB+ recommended)
- **Target Computer** with:
  - 4+ CPU cores
  - 8GB+ RAM
  - 50GB+ free disk space
  - Internet connection (for dependencies)

### **Software Requirements**
- **Ventoy** installed on USB stick
- **Ubuntu/Debian Live ISO** on Ventoy (22.04 LTS recommended)
- **Ansible** (included in deployment)

---

## 🚀 **DEPLOYMENT METHODS**

### **Method 1: Fully Automated (Recommended)**

#### **Step 1: Prepare Ventoy Stick**
1. Download **Ventoy** from [https://www.ventoy.net](https://www.ventoy.net)
2. Install Ventoy on your USB stick
3. Copy **Ubuntu 22.04 LTS ISO** to Ventoy stick
4. Boot from Ventoy stick and select Ubuntu

#### **Step 2: Run Automated Deployment**
```bash
# After Ubuntu boots, open terminal and run:

# Install Ansible
sudo apt update
sudo apt install -y ansible git

# Clone or copy NIR Mistral repository
cd /tmp
git clone /home/martin/Development/vsCode_Environment/NIR_Mistral.git
cd NIR_Mistral

# Run deployment playbook
sudo ansible-playbook -i localhost, ansible/deploy_nir_mistral.yml --ask-become-pass
```

#### **Step 3: Access Your Platform**
- **Dashboard**: `http://<your-server-ip>/dashboard/`
- **Admin**: `http://<your-server-ip>/admin/`
- **API**: `http://<your-server-ip>/api/`

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

---

### **Method 2: Manual Deployment**

#### **Step 1: Install Dependencies**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git curl nginx supervisor sqlite3 build-essential libpq-dev

# Install Python dependencies
sudo apt install -y python3-dev libssl-dev libffi-dev
```

#### **Step 2: Setup NIR Mistral**
```bash
# Create installation directory
sudo mkdir -p /opt/nir_mistral
sudo chown $USER:$USER /opt/nir_mistral

# Copy files from Ventoy stick (assuming mounted at /media/ventoy)
cp -r /media/ventoy/NIR_Mistral/* /opt/nir_mistral/

# Create virtual environment
cd /opt/nir_mistral
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Setup Django
cd django_project
python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser
```

#### **Step 3: Create Systemd Service**
```bash
# Create service file
sudo nano /etc/systemd/system/nir_mistral.service
```

Paste the following (adjust paths as needed):
```ini
[Unit]
Description=NIR Mistral Spectral Analysis Platform
After=network.target

[Service]
User=nir_user
Group=nir_group
WorkingDirectory=/opt/nir_mistral/django_project
Environment="PATH=/opt/nir_mistral/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=/opt/nir_mistral"
ExecStart=/opt/nir_mistral/venv/bin/python /opt/nir_mistral/django_project/manage.py runserver 0.0.0.0:8000
Restart=always
RestartSec=5
StandardOutput=file:/var/log/nir_mistral.out
StandardError=file:/var/log/nir_mistral.err

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable nir_mistral
sudo systemctl start nir_mistral
```

#### **Step 4: Setup Nginx (Optional)**
```bash
# Install Nginx
sudo apt install -y nginx

# Create configuration
sudo nano /etc/nginx/sites-available/nir_mistral
```

Paste the following:
```nginx
upstream nir_mistral {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name your-server-ip;
    
    client_max_body_size 100M;
    
    location /static/ {
        alias /opt/nir_mistral/django_project/static/;
        expires 30d;
    }
    
    location /media/ {
        alias /opt/nir_mistral/django_project/media/;
        expires 30d;
    }
    
    location / {
        proxy_pass http://nir_mistral;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/nir_mistral /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 📁 **VENTOY STICK STRUCTURE**

```
Ventoy Stick/
├── ubuntu-22.04-desktop-amd64.iso    # Ubuntu Live ISO
├── NIR_Mistral/                       # NIR Mistral files
│   ├── ansible/                       # Ansible playbooks
│   │   ├── deploy_nir_mistral.yml     # Main deployment playbook
│   │   ├── nir_mistral.service.j2     # Systemd service template
│   │   ├── nginx_nir_mistral.conf.j2  # Nginx configuration template
│   │   └── logrotate_nir_mistral.j2   # Log rotation template
│   ├── django_project/                # Django application
│   │   ├── nir_web/                  # Django project
│   │   ├── api/                      # REST API
│   │   ├── core/                     # Core models
│   │   ├── templates/                # HTML templates
│   │   ├── static/                   # Static files
│   │   └── ...
│   ├── requirements.txt               # Python dependencies
│   ├── start_bg.sh                   # Startup script
│   ├── quickstart.sh                 # Quick start script
│   ├── stop_nir_server.sh            # Stop script
│   ├── PRODUCTION_SETUP.md           # Production setup guide
│   ├── VENTOY_DEPLOYMENT.md         # This file
│   ├── QUICKSTART.md                 # Quick start guide
│   └── ...
└── ventoy.json                       # Ventoy configuration
```

---

## 🎯 **DEPLOYMENT CHECKLIST**

### **Pre-Deployment**
- [ ] Ventoy USB stick prepared
- [ ] Ubuntu ISO copied to Ventoy
- [ ] NIR Mistral files copied to Ventoy
- [ ] Target computer meets requirements
- [ ] Network connection available

### **During Deployment**
- [ ] Boot from Ventoy stick
- [ ] Select Ubuntu Live
- [ ] Open terminal
- [ ] Run deployment commands
- [ ] Monitor deployment progress

### **Post-Deployment**
- [ ] Server is running
- [ ] Can access dashboard
- [ ] All pages load correctly
- [ ] Colorful UI is visible
- [ ] API endpoints respond
- [ ] Can upload spectral data
- [ ] Analysis works correctly

---

## 🔧 **TROUBLESHOOTING**

### **Issue: Deployment Fails**
```bash
# Check Ansible logs
sudo tail -f /var/log/ansible.log

# Run with verbose output
sudo ansible-playbook -i localhost, ansible/deploy_nir_mistral.yml --ask-become-pass -vvv
```

### **Issue: Server Won't Start**
```bash
# Check service status
sudo systemctl status nir_mistral

# Check logs
sudo journalctl -u nir_mistral -f

# Check application logs
sudo tail -f /var/log/nir_mistral.out
sudo tail -f /var/log/nir_mistral.err
```

### **Issue: Nginx Configuration Error**
```bash
# Test configuration
sudo nginx -t

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log

# Restart Nginx
sudo systemctl restart nginx
```

### **Issue: Port Already in Use**
```bash
# Find and kill process
sudo lsof -i :8000
sudo kill -9 <PID>

# Or use different port
# Edit: /etc/systemd/system/nir_mistral.service
# Change: ExecStart=...:8001
sudo systemctl daemon-reload
sudo systemctl restart nir_mistral
```

### **Issue: Database Errors**
```bash
# Recreate database
cd /opt/nir_mistral/django_project
source /opt/nir_mistral/venv/bin/activate
python manage.py migrate --run-syncdb
python manage.py createsuperuser
```

---

## 📊 **DEPLOYMENT VERIFICATION**

### **1. Check Service Status**
```bash
sudo systemctl status nir_mistral
```

Expected output:
```
● nir_mistral.service - NIR Mistral Spectral Analysis Platform
   Loaded: loaded (/etc/systemd/system/nir_mistral.service; enabled)
   Active: active (running) since ...
```

### **2. Test Web Access**
```bash
curl http://localhost:8000/api/health/
```

Expected output:
```json
{"status":"healthy","version":"1.0.0",...}
```

### **3. Test Dashboard**
```bash
curl http://localhost/dashboard/ | grep "NIR Mistral Dashboard"
```

Expected output:
```html
<title>NIR Mistral Dashboard - Advanced Spectral Analysis</title>
```

### **4. Test Colorful CSS**
```bash
curl http://localhost/dashboard/ | grep "nir-colorful.css"
```

Expected output:
```html
<link rel="stylesheet" href="/static/css/nir-colorful.css">
```

---

## 🚀 **SERVICE MANAGEMENT**

### **Start/Stop/Restart**
```bash
# Start
sudo systemctl start nir_mistral

# Stop
sudo systemctl stop nir_mistral

# Restart
sudo systemctl restart nir_mistral

# Status
sudo systemctl status nir_mistral

# Enable on boot
sudo systemctl enable nir_mistral

# Disable on boot
sudo systemctl disable nir_mistral
```

### **Logs**
```bash
# Application logs
sudo tail -f /var/log/nir_mistral.out

# Error logs
sudo tail -f /var/log/nir_mistral.err

# Systemd logs
sudo journalctl -u nir_mistral -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## 📝 **POST-DEPLOYMENT TASKS**

### **1. Change Admin Password**
```bash
cd /opt/nir_mistral/django_project
source /opt/nir_mistral/venv/bin/activate
python manage.py changepassword admin
```

### **2. Create Additional Users**
```bash
python manage.py createsuperuser
```

### **3. Install Quarto (Optional)**
```bash
# Download and install Quarto
wget https://github.com/quarto-dev/quarto-cli/releases/download/v1.3.450/quarto-1.3.450-linux-amd64.deb
sudo dpkg -i quarto-1.3.450-linux-amd64.deb

# Verify
quarto --version
```

### **4. Configure HTTPS (Recommended for Production)**
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo certbot renew --dry-run
```

### **5. Setup Backups**
```bash
# Create backup directory
sudo mkdir -p /backup/nir_mistral

# Backup database and files
sudo tar -czvf /backup/nir_mistral/backup_$(date +%Y%m%d).tar.gz \
  /opt/nir_mistral/django_project/db.sqlite3 \
  /opt/nir_mistral/data
```

---

## 🎯 **FEATURES STATUS**

### **✅ FULLY FUNCTIONAL**
- [x] **Spectral Data Analysis** - Complete analysis pipeline
- [x] **Parameter Recommendations** - AI-powered suggestions
- [x] **Quality Assessment** - Metadata and spectral quality
- [x] **Shift Detection** - Wavelength and intensity drift
- [x] **Multi-Agent Orchestration** - CrewAI integration
- [x] **Web Interface** - Professional, colorful UI/UX
- [x] **REST API** - Full API access
- [x] **User Management** - Authentication and profiles
- [x] **Database** - SQLite with all models
- [x] **File Upload** - Spectrum and metadata upload

### **⚠️ PARTIAL (Framework Ready)**
- [x] **Flower Framework** - Federated learning ready
- [ ] **ILIAS Integration** - Not yet implemented
- [x] **Quarto Templates** - Templates ready
- [ ] **Quarto Engine** - Not installed
- [ ] **Public/Private Toggle** - UI not implemented

### **❌ NOT IMPLEMENTED**
- [ ] **ILIAS SSO** - Authentication through ILIAS
- [ ] **ILIAS User Groups** - Group management
- [ ] **ILIAS Communication** - User group communication
- [ ] **Automatic Report Rendering** - Quarto HTML generation
- [ ] **Federated Calibration** - Community calibration

---

## ✅ **CONCLUSION**

**Your NIR Mistral Local NIR Data Analysis Platform is ready for deployment from Ventoy stick!**

### **What Works:**
- ✅ **Complete spectral analysis** pipeline
- ✅ **Professional web interface** with HSWT styling
- ✅ **AI-powered agents** for analysis and recommendations
- ✅ **Multi-agent orchestration** with CrewAI
- ✅ **REST API** for integration
- ✅ **User management** and authentication
- ✅ **Colorful, user-friendly UI/UX**
- ✅ **Production-ready** deployment

### **What's Missing (Not Critical):**
- ❌ **ILIAS Integration** - Can be added later
- ❌ **Quarto Reports** - Can be installed optionally
- ❌ **Federated Learning UI** - Framework is ready

### **Deployment Options:**
1. **Fully Automated** - Use Ansible playbook (recommended)
2. **Manual** - Step-by-step instructions provided

**Your local NIR data analysis platform is production-ready and can be deployed from a Ventoy USB stick!** 🚀

---

## 📞 **SUPPORT**

### **Documentation Files:**
- `PRODUCTION_SETUP.md` - Production setup guide
- `QUICKSTART.md` - Quick start instructions
- `UI_UX_DESIGN_GUIDE.md` - UI/UX documentation
- `SERVER_UPDATE_SUMMARY.md` - Server update summary

### **Common Commands:**
```bash
# Check service
sudo systemctl status nir_mistral

# View logs
sudo journalctl -u nir_mistral -f

# Restart
sudo systemctl restart nir_mistral

# Test API
curl http://localhost/api/health/
```

---

**Last Updated:** August 7, 2026  
**Version:** 1.0.0  
**Status:** Production Ready for Local Deployment  
**Deployment Method:** Ventoy USB Stick + Ansible Automation