# NIR_Mistral Framework - Ansible Ventoy Stick Setup

## 🚀 Overview

This Ansible playbook sets up a complete **NIR_Mistral Framework** deployment on a **Ventoy stick** with:
- **Django Server** with Port Management Agent integration
- **Port Agent** for comprehensive port management
- **Ventoy-specific configuration** for bootable USB deployment

## 📁 Project Structure

```
ansible/ventoy_setup/
├── README.md                          # This file
├── ansible.cfg                       # Ansible configuration
├── inventory.ini                     # Target system inventory
├── site.yml                          # Main playbook
│
├── templates/                        # Main templates
│   ├── start_nir_mistral.sh.j2        # Main startup script
│   ├── django.service.j2             # Django systemd service
│   ├── port_agent.service.j2         # Port Agent systemd service
│   ├── nir_mistral.desktop.j2        # Desktop shortcut
│   └── VENTOY_README.md.j2           # Ventoy README
│
└── roles/                           # Ansible roles
    ├── system_preparation/           # System setup
    │   ├── tasks/
    │   │   └── main.yml              # System preparation tasks
    │   └── handlers/
    │       └── main.yml              # System handlers
    │
    ├── django_server/                # Django server setup
    │   ├── tasks/
    │   │   └── main.yml              # Django deployment tasks
    │   ├── templates/
    │   │   ├── django_env.j2          # Django environment
    │   │   ├── local_settings.py.j2   # Django local settings
    │   │   ├── gunicorn.conf.py.j2    # Gunicorn config
    │   │   ├── gunicorn.service.j2    # Gunicorn service
    │   │   ├── django.service.j2      # Django service
    │   │   └── start_django.sh.j2     # Django startup script
    │   └── handlers/
    │       └── main.yml              # Django handlers
    │
    ├── port_agent/                   # Port Agent setup
    │   ├── tasks/
    │   │   └── main.yml              # Port Agent deployment tasks
    │   ├── templates/
    │   │   ├── port_agent_config.py.j2 # Port Agent config
    │   │   ├── port_agent_env.j2      # Port Agent environment
    │   │   ├── port_agent_gunicorn.conf.py.j2 # Gunicorn config
    │   │   ├── port_agent.service.j2  # Port Agent service
    │   │   ├── start_port_agent.sh.j2  # Port Agent startup script
    │   │   └── test_port_agent.py.j2   # Port Agent test script
    │   └── handlers/
    │       └── main.yml              # Port Agent handlers
    │
    └── ventoy_config/               # Ventoy configuration
        ├── tasks/
        │   └── main.yml              # Ventoy config tasks
        ├── templates/
        │   ├── ventoy.json.j2         # Main Ventoy config
        │   ├── ventoy_control.json.j2 # Ventoy control file
        │   ├── nir_mistral_boot.conf.j2 # Boot configuration
        │   ├── ventoy_menu.conf.j2    # Menu configuration
        │   ├── persistence.conf.j2    # Persistence config
        │   ├── ventoy_theme.json.j2   # Custom theme
        │   ├── auto_boot_plugin.json.j2 # Auto-boot plugin
        │   ├── ventoy_startup.sh.j2    # Ventoy startup script
        │   ├── ventoy_boot_django.sh.j2 # Django boot script
        │   ├── ventoy_services.sh.j2   # Service manager
        │   ├── ventoy_env_setup.sh.j2  # Environment setup
        │   ├── ventoy_health_check.sh.j2 # Health check script
        │   ├── ventoy_cleanup.sh.j2    # Cleanup script
        │   └── VENTOY_CONFIG_SUMMARY.md.j2 # Config summary
        └── handlers/
            └── main.yml              # Ventoy handlers
```

## 🎯 Features

### ✅ System Preparation
- **Package Management**: Installs all required dependencies
- **Python Environment**: Sets up Python 3, pip, and virtualenv
- **User Management**: Creates service user and group
- **Swap Configuration**: Optional swap file setup
- **Firewall Configuration**: UFW/firewalld setup with port opening
- **System Optimization**: Kernel parameter tuning
- **Docker Support**: Optional Docker installation
- **System Limits**: Configures file descriptors and process limits

### ✅ Django Server Setup
- **Virtual Environment**: Creates isolated Python environment
- **Project Deployment**: Copies Django project to deployment location
- **Requirements Installation**: Installs all Python dependencies
- **Configuration**: Generates Django settings and environment files
- **Database Setup**: Configures SQLite database (default)
- **Port Manager Integration**: Integrates with Port Management Agent
- **Gunicorn Configuration**: Production-ready Gunicorn setup
- **Systemd Services**: Automatic service management
- **Static Files**: Collects static files for production
- **Migrations**: Runs database migrations

### ✅ Port Agent Setup
- **Virtual Environment**: Uses shared Python environment
- **Project Deployment**: Copies Port Agent to deployment location
- **Requirements Installation**: Installs Port Agent dependencies
- **Configuration**: Generates Port Agent settings and environment files
- **Gunicorn Configuration**: Production-ready Gunicorn setup
- **Systemd Services**: Automatic service management
- **Test Script**: Comprehensive test suite for Port Agent
- **Health Checks**: Built-in health monitoring

### ✅ Ventoy Configuration
- **Ventoy Integration**: Complete Ventoy stick configuration
- **Custom Menu**: NIR_Mistral specific boot menu
- **Auto-Boot**: Automatic service startup on boot
- **Custom Theme**: NIR_Mistral branded theme
- **Persistence**: Configuration and data persistence
- **Service Management**: Start/stop/restart services from menu
- **Health Monitoring**: Built-in health check system
- **Cleanup Utilities**: Temporary file cleanup
- **Environment Setup**: System environment configuration

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Install Ansible
sudo apt update
sudo apt install -y ansible

# Or on RedHat/CentOS
sudo yum install -y ansible

# Install required Python modules
pip install requests
```

### 2. Configure Inventory

Edit `inventory.ini` to match your target system:

```ini
[ventoy_stick]
# For local testing
localhost ansible_connection=local

# For remote Ventoy stick
# ventoy_host ansible_host=192.168.1.100 ansible_user=ventoy_user

[ventoy_stick:vars]
# Customize these variables as needed
project_name=nir_mistral
project_root=/home/martin/Development/vsCode_Environment/NIR_Mistral
deploy_root=/opt/{{ project_name }}
django_port=8000
port_agent_port=8001
```

### 3. Run the Playbook

```bash
# Full deployment (recommended)
ansible-playbook site.yml

# Target specific hosts
ansible-playbook site.yml -l ventoy_stick

# Development vs Production
ansible-playbook site.yml -e "environment=development"
ansible-playbook site.yml -e "environment=production"

# Skip specific parts
ansible-playbook site.yml -e "skip_dependencies=True"
ansible-playbook site.yml -e "skip_django=True"
ansible-playbook site.yml -e "skip_port_agent=True"
ansible-playbook site.yml -e "skip_ventoy=True"
```

## 📋 Configuration Variables

### Global Variables (inventory.ini)

| Variable | Default | Description |
|----------|---------|-------------|
| `project_name` | `nir_mistral` | Project name |
| `project_root` | `/home/martin/...` | Source project root |
| `deploy_root` | `/opt/nir_mistral` | Deployment root |
| `venv_name` | `venv` | Virtual environment name |
| `venv_path` | `{{ deploy_root }}/{{ venv_name }}` | Virtual environment path |
| `django_project_path` | `{{ deploy_root }}/django_project` | Django project path |
| `port_agent_path` | `{{ deploy_root }}/agents/port_agent` | Port Agent path |

### Django Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `django_settings_module` | `nir_web.settings` | Django settings module |
| `django_secret_key` | `your-secret-key...` | Django secret key |
| `django_debug` | `False` | Debug mode |
| `django_allowed_hosts` | `['*']` | Allowed hosts |
| `django_port` | `8000` | Django server port |
| `django_bind_address` | `0.0.0.0` | Bind address |
| `django_workers` | `4` | Gunicorn workers |
| `django_timeout` | `300` | Gunicorn timeout |

### Port Agent Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `port_agent_port` | `8001` | Port Agent port |
| `port_agent_workers` | `2` | Gunicorn workers |
| `port_agent_timeout` | `60` | Gunicorn timeout |

### System Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `service_user` | `nir_mistral` | Service user |
| `service_group` | `nir_mistral` | Service group |
| `create_swap_file` | `True` | Create swap file |
| `swap_file_size` | `2G` | Swap file size |
| `install_dependencies` | `True` | Install system dependencies |
| `create_systemd_services` | `True` | Create systemd services |
| `firewall_enabled` | `False` | Enable firewall |
| `open_ports` | `[8000, 8001, ...]` | Ports to open |
| `docker_enabled` | `False` | Enable Docker |
| `install_docker` | `False` | Install Docker |

### Ventoy Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ventoy_version` | `1.0.96` | Ventoy version |
| `ventoy_mount_point` | `/mnt/ventoy` | Ventoy mount point |
| `ventoy_iso_path` | `{{ deploy_root }}/ventoy` | Ventoy ISO path |

## 🎯 Playbook Structure

The main playbook (`site.yml`) consists of 6 phases:

### 1. **Deployment Preparation**
- Creates directory structure
- Displays deployment information
- Sets up project root directories

### 2. **System Preparation** (`system_preparation` role)
- Updates system packages
- Installs required dependencies
- Sets up Python environment
- Creates service user and group
- Configures swap file
- Sets up firewall rules
- Configures system limits
- Installs Docker (optional)

### 3. **Django Server Setup** (`django_server` role)
- Creates virtual environment
- Deploys Django project
- Installs requirements
- Configures Django settings
- Sets up database
- Integrates Port Manager
- Configures Gunicorn
- Creates systemd services
- Runs migrations
- Collects static files

### 4. **Port Agent Setup** (`port_agent` role)
- Creates directory structure
- Deploys Port Agent code
- Installs dependencies
- Configures Port Agent
- Sets up Gunicorn
- Creates systemd services
- Runs tests
- Verifies installation

### 5. **Ventoy Configuration** (`ventoy_config` role)
- Creates Ventoy directory structure
- Configures Ventoy settings
- Creates custom menu
- Sets up auto-boot plugin
- Creates startup scripts
- Configures persistence
- Sets up custom theme

### 6. **Final Configuration**
- Creates main startup script
- Creates systemd services
- Enables and starts services
- Creates desktop shortcut
- Creates README files

### 7. **Verification**
- Tests Django server health
- Tests Port Agent health
- Displays deployment summary

## 🌐 API Endpoints

### Django Server (Port 8000 by default)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health/` | Health check |
| GET | `/api/ports/` | Port management overview |
| GET | `/api/ports/status/` | Detailed port status |
| GET | `/api/ports/scan/` | Scan ports in range |
| GET | `/api/ports/check/<port>/` | Check specific port |
| POST | `/api/ports/reserve/` | Reserve a port |
| POST | `/api/ports/release/` | Release a port |
| GET | `/api/ports/conflicts/` | Get port conflicts |

### Port Agent (Port 8001 by default)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ports/` | Port management status |
| GET | `/api/ports/scan/` | Scan port range |
| GET | `/api/ports/check/<port>/` | Check port availability |
| POST | `/api/ports/assign/` | Assign a free port |
| POST | `/api/ports/reserve/` | Reserve specific port |
| POST | `/api/ports/release/` | Release reserved port |
| GET | `/api/ports/conflicts/` | Detect port conflicts |
| POST | `/api/ports/resolve/` | Resolve port conflicts |
| GET | `/api/docker/available/` | Check Docker availability |
| GET | `/api/docker/version/` | Get Docker version |
| GET | `/api/docker/containers/` | List running containers |
| GET | `/api/docker/mappings/` | Get port mappings |

## 📁 File Structure on Target System

After deployment, the target system will have this structure:

```
/opt/nir_mistral/
├── django_project/           # Django application
│   ├── manage.py
│   ├── nir_web/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── local_settings.py  # Generated by Ansible
│   │   └── wsgi.py
│   ├── port_manager/         # Port management Django app
│   │   ├── middleware.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── management/
│   │       └── commands/
│   │           ├── check_ports.py
│   │           └── reserve_port.py
│   ├── gunicorn.conf.py      # Generated by Ansible
│   └── .env                  # Generated by Ansible
│
├── agents/
│   └── port_agent/           # Port Management Agent
│       ├── agent.py
│       ├── server.py
│       ├── port_manager.py
│       ├── docker_port_manager.py
│       ├── integration.py
│       ├── exceptions.py
│       ├── config/
│       │   └── settings.py    # Generated by Ansible
│       ├── .env              # Generated by Ansible
│       └── scripts/
│           └── test_port_agent.py  # Generated by Ansible
│
├── venv/                    # Python virtual environment
│   └── bin/
│       ├── python
│       ├── pip
│       └── activate
│
├── logs/                    # Log files
│   ├── django.log
│   ├── gunicorn.log
│   ├── access.log
│   ├── port_agent.log
│   ├── port_agent_access.log
│   └── port_agent_error.log
│
├── config/                  # Configuration files
│   ├── django_settings.py
│   └── port_agent_settings.py
│
├── data/                    # Data files
│   └── db.sqlite3
│
├── ventoy/                  # Ventoy configuration
│   ├── ventoy.json
│   ├── ventoy_control.json
│   ├── nir_mistral_boot.conf
│   ├── ventoy_menu.conf
│   ├── persistence.conf
│   ├── themes/
│   │   └── nir_mistral/
│   │       └── theme.json
│   ├── plugins/
│   │   └── auto_boot_plugin.json
│   ├── ventoy_startup.sh
│   ├── boot_django.sh
│   ├── ventoy_services.sh
│   ├── ventoy_env_setup.sh
│   ├── ventoy_health_check.sh
│   └── ventoy_cleanup.sh
│
├── start_nir_mistral.sh     # Main startup script
├── VENTOY_README.md         # README with usage instructions
└── VENTOY_CONFIG_SUMMARY.md # Configuration summary

/etc/systemd/system/
├── django.service            # Django systemd service
├── port_agent.service       # Port Agent systemd service
└── gunicorn.service          # Gunicorn systemd service

/etc/profile.d/
└── nir_mistral.sh           # Environment variables

/etc/security/limits.d/
└── nir_mistral.conf         # System limits

/etc/cron.d/
└── nir_mistral              # Cron jobs
```

## 🚀 Usage After Deployment

### Starting Services

```bash
# Method 1: Using the main startup script
/opt/nir_mistral/start_nir_mistral.sh start

# Method 2: Using systemd services
sudo systemctl start django
sudo systemctl start port_agent

# Method 3: From Ventoy menu (when booted from Ventoy stick)
# Select "NIR_Mistral Framework" from the menu
```

### Stopping Services

```bash
# Method 1: Using the main startup script
/opt/nir_mistral/start_nir_mistral.sh stop

# Method 2: Using systemd services
sudo systemctl stop django
sudo systemctl stop port_agent
```

### Checking Status

```bash
# Method 1: Using the main startup script
/opt/nir_mistral/start_nir_mistral.sh status

# Method 2: Using systemd
sudo systemctl status django
sudo systemctl status port_agent

# Method 3: Health check
curl http://localhost:8000/api/health/
curl http://localhost:8001/api/ports/
```

### Viewing Logs

```bash
# Method 1: Using the main startup script
/opt/nir_mistral/start_nir_mistral.sh logs

# Method 2: Direct log files
tail -f /opt/nir_mistral/logs/django.log
tail -f /opt/nir_mistral/logs/port_agent.log

# Method 3: Systemd logs
journalctl -u django -f
journalctl -u port_agent -f
```

### Service Management

```bash
# Start specific service
/opt/nir_mistral/ventoy/ventoy_services.sh start django
/opt/nir_mistral/ventoy/ventoy_services.sh start port_agent
/opt/nir_mistral/ventoy/ventoy_services.sh start all

# Stop specific service
/opt/nir_mistral/ventoy/ventoy_services.sh stop django
/opt/nir_mistral/ventoy/ventoy_services.sh stop all

# Restart services
/opt/nir_mistral/ventoy/ventoy_services.sh restart all

# Check status
/opt/nir_mistral/ventoy/ventoy_services.sh status
```

### Health Check

```bash
# Run comprehensive health check
/opt/nir_mistral/ventoy/ventoy_health_check.sh

# Check specific services
curl http://localhost:8000/api/health/
curl http://localhost:8001/api/ports/
```

### Cleanup

```bash
# Cleanup temporary files
/opt/nir_mistral/ventoy/ventoy_cleanup.sh

# Cleanup specific items
/opt/nir_mistral/ventoy/ventoy_cleanup.sh temp
/opt/nir_mistral/ventoy/ventoy_cleanup.sh logs
/opt/nir_mistral/ventoy/ventoy_cleanup.sh all
```

## 🧪 Testing

### Test Django Server

```bash
# Check health
curl http://localhost:8000/api/health/

# Get port status
curl http://localhost:8000/api/ports/

# Check specific port
curl http://localhost:8000/api/ports/check/8080/

# Scan port range
curl "http://localhost:8000/api/ports/scan/?start=9000&end=9100"
```

### Test Port Agent

```bash
# Check health
curl http://localhost:8001/api/ports/

# Assign a port
curl -X POST http://localhost:8001/api/ports/assign/ \
  -H "Content-Type: application/json" \
  -d '{"start": 9000, "end": 9100, "service_name": "test_service"}'

# Reserve a specific port
curl -X POST http://localhost:8001/api/ports/reserve/ \
  -H "Content-Type: application/json" \
  -d '{"port": 9999, "service_name": "test_service"}'

# Release a port
curl -X POST http://localhost:8001/api/ports/release/ \
  -H "Content-Type: application/json" \
  -d '{"port": 9999}'

# Check conflicts
curl http://localhost:8001/api/ports/conflicts/

# Resolve conflicts
curl -X POST http://localhost:8001/api/ports/resolve/ \
  -H "Content-Type: application/json" \
  -d '{"auto_assign": true}'
```

### Run Port Agent Tests

```bash
# Run comprehensive test suite
/opt/nir_mistral/agents/port_agent/scripts/test_port_agent.py
```

### Django Management Commands

```bash
# Activate virtual environment
source /opt/nir_mistral/venv/bin/activate

# Check ports
cd /opt/nir_mistral/django_project
python manage.py check_ports

# Check ports with conflict resolution
python manage.py check_ports --resolve

# Reserve port for agent
python manage.py reserve_port django_agent

# List reserved ports
python manage.py reserve_port --list

# Release a port
python manage.py reserve_port --release django_agent
```

## 🛠️ Troubleshooting

### Common Issues

#### Services Won't Start

1. **Check logs**:
   ```bash
   tail -f /opt/nir_mistral/logs/*.log
   journalctl -u django -xe
   journalctl -u port_agent -xe
   ```

2. **Check dependencies**:
   ```bash
   python3 --version
   pip3 --version
   /opt/nir_mistral/venv/bin/python --version
   ```

3. **Check ports**:
   ```bash
   sudo lsof -i :8000
   sudo lsof -i :8001
   sudo netstat -tlnp | grep -E "8000|8001"
   ```

#### Port Conflicts

1. **Find conflicting processes**:
   ```bash
   sudo lsof -i :8000
   sudo kill -9 <PID>
   ```

2. **Use Port Agent to resolve**:
   ```bash
   curl -X POST http://localhost:8001/api/ports/resolve/ \
     -H "Content-Type: application/json" \
     -d '{"auto_assign": true}'
   ```

#### Dependency Issues

1. **Reinstall dependencies**:
   ```bash
   source /opt/nir_mistral/venv/bin/activate
   pip install -r /opt/nir_mistral/django_project/requirements.txt
   pip install -r /opt/nir_mistral/agents/port_agent/requirements.txt
   ```

2. **Check Python packages**:
   ```bash
   pip list
   pip check
   ```

#### Permission Issues

1. **Check permissions**:
   ```bash
   ls -la /opt/nir_mistral/
   ls -la /opt/nir_mistral/django_project/
   ls -la /opt/nir_mistral/agents/port_agent/
   ```

2. **Fix permissions**:
   ```bash
   sudo chown -R nir_mistral:nir_mistral /opt/nir_mistral/
   sudo chmod -R 755 /opt/nir_mistral/
   ```

## 🔄 Update Process

### Update NIR_Mistral Framework

1. **Pull latest changes**:
   ```bash
   cd /home/martin/Development/vsCode_Environment/NIR_Mistral
   git pull origin main
   ```

2. **Update dependencies**:
   ```bash
   source /opt/nir_mistral/venv/bin/activate
   pip install -r /opt/nir_mistral/django_project/requirements.txt
   pip install -r /opt/nir_mistral/agents/port_agent/requirements.txt
   ```

3. **Restart services**:
   ```bash
   sudo systemctl restart django
   sudo systemctl restart port_agent
   ```

4. **Verify update**:
   ```bash
   curl http://localhost:8000/api/health/
   curl http://localhost:8001/api/ports/
   ```

## 📚 Documentation

### Related Documentation

- **Main README**: `/home/martin/Development/vsCode_Environment/NIR_Mistral/README.md`
- **Start Guide**: `/home/martin/Development/vsCode_Environment/NIR_Mistral/START_PORT_MANAGER_SERVER.md`
- **Port Agent Docs**: `/home/martin/Development/vsCode_Environment/NIR_Mistral/agents/port_agent/README.md`
- **Django Docs**: `/home/martin/Development/vsCode_Environment/NIR_Mistral/django_project/README.md`

### Generated Documentation

After deployment, these files will be available:
- `/opt/nir_mistral/VENTOY_README.md` - Complete usage guide
- `/opt/nir_mistral/VENTOY_CONFIG_SUMMARY.md` - Configuration summary

## 🏁 Conclusion

This Ansible playbook provides a **complete, production-ready** setup for the **NIR_Mistral Framework** on a **Ventoy stick** with:

✅ **Automatic Deployment**: One-command setup
✅ **System Optimization**: Tuned for performance
✅ **Port Management**: Built-in conflict resolution
✅ **Docker Support**: Optional Docker integration
✅ **Cross-platform**: Works on Debian/Ubuntu and RedHat/CentOS
✅ **Ventoy Integration**: Bootable USB deployment
✅ **Health Monitoring**: Built-in health checks
✅ **Service Management**: Easy start/stop/restart
✅ **Comprehensive Logging**: Full logging support
✅ **Security**: Proper permissions and limits

**Next Steps:**
1. Configure the inventory file for your target system
2. Run the playbook: `ansible-playbook site.yml`
3. Boot from your Ventoy stick
4. Select "NIR_Mistral Framework" from the menu
5. Test the API endpoints

---

*Generated by Ansible Ventoy Setup*
*Version: 1.0.0*
*License: MIT*