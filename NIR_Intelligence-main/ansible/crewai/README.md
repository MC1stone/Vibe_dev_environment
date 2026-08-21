# NIR Intelligence Platform - Crew AI Ansible Implementation

This directory contains Ansible playbooks for testing and deploying the Crew AI implementation of the NIR Intelligence Platform.

## 📁 Directory Structure

```
ansible/crewai/
├── README.md                    # This file
├── inventory.ini               # Ansible inventory file
├── main.yml                    # Main playbook
├── test_crewai_implementation.yml  # Test playbook
├── deploy_crewai.yml           # Deployment playbook
└── templates/                  # Configuration templates
    ├── gunicorn.conf.py.j2
    ├── supervisor.conf.j2
    └── nginx.conf.j2
```

## 🚀 Quick Start

### Prerequisites

- Ansible 2.9+
- Python 3.8+
- SSH access to target servers (for remote deployment)

### Installation

```bash
# Install Ansible
sudo apt update
sudo apt install ansible

# Or using pip
pip install ansible
```

## 🧪 Testing the Crew AI Implementation

### Run Tests on Localhost

```bash
# Navigate to the project root
cd /home/martin/Development/vsCode_Environment/NIR_Mistral

# Run the test playbook
ansible-playbook ansible/crewai/test_crewai_implementation.yml -i ansible/crewai/inventory.ini
```

### Run Tests with Custom Inventory

```bash
ansible-playbook ansible/crewai/test_crewai_implementation.yml -i path/to/your/inventory.ini
```

### Run Tests with Verbose Output

```bash
ansible-playbook ansible/crewai/test_crewai_implementation.yml -i ansible/crewai/inventory.ini -v
```

### Run Tests with Very Verbose Output

```bash
ansible-playbook ansible/crewai/test_crewai_implementation.yml -i ansible/crewai/inventory.ini -vvv
```

## 📋 Test Playbook Overview

The `test_crewai_implementation.yml` playbook performs comprehensive testing of all Crew AI components:

### Tested Components

1. **Spectral Analysis Agent**
   - Tests spectral data validation
   - Tests quality assessment
   - Tests parameter recommendations
   - Tests preprocessing functionality

2. **Metadata Quality Agent**
   - Tests metadata extraction from various formats
   - Tests quality assessment against multiple standards
   - Tests validation and recommendations

3. **Reporting Agent**
   - Tests report generation
   - Tests template rendering
   - Tests file creation and preview

4. **NIR Analysis Crew**
   - Tests complete analysis workflow
   - Tests agent orchestration
   - Tests privacy controls
   - Tests batch processing

5. **Django API Integration**
   - Tests API endpoint imports
   - Tests Django integration

### Test Output

- **Test Reports**: Saved to `test_output/reports/`
- **Test Logs**: Saved to `test_output/logs/`
- **Summary Report**: `test_output/reports/crewai_test_summary.md`

## 🎯 Deployment Playbook Overview

The `deploy_crewai.yml` playbook deploys the Crew AI implementation to production servers:

### Deployment Features

- **System Setup**:
  - Creates dedicated user and group
  - Creates required directories
  - Installs system dependencies

- **Python Environment**:
  - Creates virtual environment
  - Installs Python packages
  - Configures Python path

- **Web Server**:
  - Configures Nginx as reverse proxy
  - Configures Gunicorn as application server
  - Configures Supervisor for process management

- **Application Setup**:
  - Runs Django migrations
  - Collects static files
  - Creates initial superuser

- **Services**:
  - Django application server
  - Celery worker for background tasks
  - Flower for task monitoring
  - Quarto server for report rendering

### Deployment Configuration

Edit the variables in `deploy_crewai.yml` to customize:

```yaml
# Project paths
project_root: "/opt/nir_mistral"
venv_path: "{{ project_root }}/venv"

# System user
nir_user: "nir_mistral"
nir_group: "nir_mistral"

# Service configuration
django_port: 8000
gunicorn_workers: 4

# Required packages
required_packages:
  - python3
  - python3-venv
  - nginx
  - supervisor
  - quarto
  - pandoc
```

## 🌐 Inventory Configuration

### Local Testing

The default `inventory.ini` is configured for localhost testing:

```ini
[localhost]
127.0.0.1 ansible_connection=local

[crewai_test:children]
localhost
```

### Remote Servers

Add your remote servers to the inventory:

```ini
[crewai_servers]
crewai-server-1 ansible_host=192.168.1.101
crewai-server-2 ansible_host=192.168.1.102

[crewai_production:children]
crewai_servers
```

### Custom Variables

```ini
[all:vars]
ansible_user=ubuntu
ansible_python_interpreter=/usr/bin/python3
project_root=/opt/nir_mistral
admin_password=your_secure_password
```

## 📊 Running the Deployment

### Deploy to Localhost

```bash
ansible-playbook ansible/crewai/deploy_crewai.yml -i ansible/crewai/inventory.ini --limit localhost
```

### Deploy to Production Servers

```bash
ansible-playbook ansible/crewai/deploy_crewai.yml -i ansible/crewai/inventory.ini --limit crewai_production
```

### Deploy with Custom Variables

```bash
ansible-playbook ansible/crewai/deploy_crewai.yml -i ansible/crewai/inventory.ini \
  -e "admin_password=your_password" \
  -e "django_port=8080"
```

## 🔧 Configuration Templates

### Gunicorn Configuration

The `templates/gunicorn.conf.py.j2` template configures:
- Worker processes and threads
- Socket binding
- Timeout settings
- Logging configuration
- Security settings

### Supervisor Configuration

The `templates/supervisor.conf.j2` template configures:
- Gunicorn process management
- Celery worker management
- Flower service management
- Quarto server management
- Logging and restart policies

### Nginx Configuration

The `templates/nginx.conf.j2` template configures:
- Reverse proxy to Django
- Static and media file serving
- Security headers
- Timeout settings
- Logging configuration

## 🧩 Integration with Existing Ansible

The Crew AI Ansible playbooks can be integrated with the existing NIR Mistral Ansible infrastructure:

### Include in Main Ansible Playbook

```yaml
# In your main ansible playbook
- name: Deploy Crew AI Implementation
  import_playbook: ansible/crewai/deploy_crewai.yml
  when: deploy_crewai | default(false)

- name: Test Crew AI Implementation
  import_playbook: ansible/crewai/test_crewai_implementation.yml
  when: test_crewai | default(false)
```

### Use Existing Variables

The playbooks are designed to work with the existing NIR Mistral Ansible variables and can be customized as needed.

## 📝 Environment Variables

### Required for Deployment

- `admin_password`: Django admin password (set during deployment)
- `VENV_PATH`: Path to Python virtual environment
- `PROJECT_ROOT`: Root directory for NIR Mistral

### Optional Variables

- `django_port`: Port for Django application (default: 8000)
- `gunicorn_workers`: Number of Gunicorn workers (default: 4)
- `nir_user`: System user for NIR Mistral (default: nir_mistral)
- `nir_group`: System group for NIR Mistral (default: nir_mistral)

## 🔍 Troubleshooting

### Common Issues

1. **Python Version Issues**
   ```bash
   # Check Python version
   python3 --version
   
   # Install required Python version
   sudo apt install python3.8 python3.8-venv python3.8-dev
   ```

2. **Missing Dependencies**
   ```bash
   # Install missing system packages
   sudo apt install python3-pip python3-venv nginx supervisor
   ```

3. **Permission Issues**
   ```bash
   # Check directory permissions
   ls -la /opt/nir_mistral
   
   # Fix permissions
   sudo chown -R nir_mistral:nir_mistral /opt/nir_mistral
   ```

4. **Port Conflicts**
   ```bash
   # Check for port conflicts
   sudo netstat -tulnp | grep 8000
   
   # Kill conflicting process
   sudo kill -9 <PID>
   ```

### Debug Mode

Run Ansible in debug mode for detailed output:

```bash
ansible-playbook ansible/crewai/test_crewai_implementation.yml -i ansible/crewai/inventory.ini -vvv
```

## 📚 Documentation

- [Ansible Documentation](https://docs.ansible.com/)
- [NIR Intelligence Platform Documentation](../README.md)
- [Crew AI Implementation](../../agents/nir_analysis_crew.py)

## 🎯 Next Steps

1. **Test the Implementation**: Run the test playbook to verify all components work
2. **Customize Configuration**: Edit the variables in the playbooks for your environment
3. **Deploy to Production**: Run the deployment playbook on your production servers
4. **Monitor Services**: Check service status and logs after deployment
5. **Integrate with CI/CD**: Add Ansible playbooks to your CI/CD pipeline

## 🏁 Conclusion

The Ansible playbooks provide a complete solution for testing and deploying the Crew AI implementation of the NIR Intelligence Platform. They handle:

- ✅ Comprehensive testing of all Crew AI components
- ✅ Production-ready deployment configuration
- ✅ Service management and monitoring
- ✅ Security and performance optimization
- ✅ Easy customization and integration

**The Crew AI implementation is now ready for automated testing and deployment using Ansible!** 🚀