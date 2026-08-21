# NIR_Mistral DeveloperAgent Framework - Ansible Setup

## 🚀 Overview

This directory contains **Ansible playbooks** for deploying and managing the **NIR_Mistral DeveloperAgent Framework** on **Venty sticks** and other servers. The playbooks automate the complete setup, configuration, and management of the framework.

---

## 📁 Directory Structure

```
ansible/
├── ansible.cfg                    # Ansible configuration
├── galaxy_requirements.yml        # Galaxy collections requirements
├── requirements.txt               # Python requirements for Ansible
├── inventory/
│   └── hosts.yml                  # Inventory with all hosts
├── group_vars/
│   ├── all.yml                    # Global variables
│   └── venty_stick.yml            # Venty stick specific variables
├── playbooks/
│   ├── setup_venty_stick.yml      # Main setup playbook
│   ├── deploy_framework.yml       # Framework deployment playbook
│   └── backup_framework.yml       # Backup playbook
└── templates/                     # Jinja2 templates
    ├── docker_daemon.json.j2
    ├── framework.service.j2
    ├── start_framework.sh.j2
    ├── stop_framework.sh.j2
    ├── framework.env.j2
    ├── framework_profile.sh.j2
    ├── logrotate.conf.j2
    ├── fail2ban.local.j2
    ├── network_interfaces.j2
    └── backup_manifest.txt.j2
```

---

## 🎯 Prerequisites

### 1. **Control Machine Requirements**
- **Ansible**: Version 8.0.0 or higher
- **Python**: Version 3.8 or higher
- **Operating System**: Linux (Ubuntu/Debian recommended)
- **SSH Access**: SSH key-based authentication to target machines

### 2. **Target Machine Requirements**
- **Operating System**: Ubuntu 22.04 LTS or Debian 11+ (recommended for Venty stick)
- **Hardware**: 
  - Minimum: 4 CPU cores, 8GB RAM, 64GB storage
  - Recommended: 8 CPU cores, 16GB RAM, 128GB SSD/USB 3.0
- **Network**: Stable internet connection for package installation
- **SSH**: SSH server with key-based authentication

### 3. **Venty Stick Specific Requirements**
- **USB 3.0 Port**: For optimal performance
- **Power Supply**: Stable power source
- **Network**: Ethernet connection recommended (more reliable than WiFi)

---

## 🚀 Quick Start

### 1. **Install Ansible and Dependencies**

```bash
# Install Ansible
sudo apt update
sudo apt install -y ansible python3-pip

# Install required Python packages
pip install -r ansible/requirements.txt

# Install Ansible Galaxy collections
ansible-galaxy install -r ansible/galaxy_requirements.yml
```

### 2. **Configure SSH Access**

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -f ~/.ssh/venty_stick_key

# Copy SSH key to Venty stick
ssh-copy-id -i ~/.ssh/venty_stick_key ubuntu@venty-stick-ip

# Test SSH connection
ssh -i ~/.ssh/venty_stick_key ubuntu@venty-stick-ip
```

### 3. **Configure Inventory**

Edit `ansible/inventory/hosts.yml` and update the Venty stick configuration:

```yaml
venty_stick:
  hosts:
    venty-stick:
      ansible_host: 192.168.1.100  # Change to your Venty stick IP
      ansible_user: ubuntu
      ansible_ssh_private_key_file: ~/.ssh/venty_stick_key
```

### 4. **Run the Setup Playbook**

```bash
# Test connectivity
ansible -i inventory/hosts.yml venty_stick -m ping

# Run full setup (takes 10-30 minutes)
ansible-playbook -i inventory/hosts.yml playbooks/setup_venty_stick.yml
```

---

## 📋 Available Playbooks

### 1. **setup_venty_stick.yml** - Main Setup Playbook

**Description**: Complete setup of Venty stick with DeveloperAgent Framework

**Phases**:
1. System Preparation (packages, timezone, hostname, swap)
2. Python Environment Setup (Python, pip, virtualenv, dependencies)
3. Docker Setup (Docker Engine, configuration, network)
4. Security Hardening (SSH, firewall, fail2ban, users)
5. Framework Deployment (code, configs, services)
6. Database Services (PostgreSQL, Weaviate)
7. Monitoring Setup (Prometheus, Grafana)
8. Final Configuration and Verification

**Usage**:
```bash
# Full setup
ansible-playbook -i inventory/hosts.yml playbooks/setup_venty_stick.yml

# Only Venty stick
ansible-playbook -i inventory/hosts.yml playbooks/setup_venty_stick.yml --limit venty_stick

# With tags (run specific phases)
ansible-playbook -i inventory/hosts.yml playbooks/setup_venty_stick.yml --tags "python,docker"
```

### 2. **deploy_framework.yml** - Framework Deployment

**Description**: Deploy updates to existing framework installations

**Features**:
- Stop framework service
- Backup current installation
- Copy updated code
- Install new dependencies
- Run database migrations
- Validate and restart framework

**Usage**:
```bash
# Deploy to all framework servers
ansible-playbook -i inventory/hosts.yml playbooks/deploy_framework.yml

# Deploy to Venty stick only
ansible-playbook -i inventory/hosts.yml playbooks/deploy_framework.yml --limit venty_stick
```

### 3. **backup_framework.yml** - Backup Framework

**Description**: Create complete backups of framework, databases, and configurations

**Features**:
- Backup framework code
- Backup configuration files
- Backup PostgreSQL database
- Backup Weaviate database
- Create backup manifest
- Clean up old backups (retention policy)

**Usage**:
```bash
# Create backup
ansible-playbook -i inventory/hosts.yml playbooks/backup_framework.yml

# Create backup with custom retention
ansible-playbook -i inventory/hosts.yml playbooks/backup_framework.yml -e "backup_retention=30"
```

---

## 🔧 Configuration

### Inventory Configuration

The main inventory file is `inventory/hosts.yml`. It defines all target machines and their properties.

**Example Venty Stick Configuration**:
```yaml
venty_stick:
  hosts:
    venty-stick:
      ansible_host: 192.168.1.100
      ansible_user: ubuntu
      ansible_ssh_private_key_file: ~/.ssh/venty_stick_key
      is_venty_stick: true
      deployment_type: "stick"
      storage_type: "usb"
```

### Global Variables

Global variables are defined in `group_vars/all.yml`. These apply to all hosts.

**Key Variables**:
- `project_name`: NIR_Mistral
- `framework_version`: 1.0.0
- `python_version`: 3.11
- `docker_enabled`: true
- `log_dir`: /var/log/NIR_Mistral

### Venty Stick Specific Variables

Venty stick specific variables are in `group_vars/venty_stick.yml`.

**Key Variables**:
- `is_venty_stick`: true
- `deployment_type`: stick
- `storage_type`: usb
- `hardware`: CPU, memory, storage specs
- `performance`: Swap, tmpfs, I/O optimizations
- `databases`: PostgreSQL, Weaviate, FAISS configurations
- `security`: SSH, firewall, fail2ban settings

---

## 🎛️ Customization

### 1. **Custom Variables**

Override variables using command line:

```bash
# Override framework port
ansible-playbook -i inventory/hosts.yml playbooks/setup_venty_stick.yml -e "framework_port=9090"

# Override multiple variables
ansible-playbook -i inventory/hosts.yml playbooks/setup_venty_stick.yml \
  -e "framework_port=9090 docker_enabled=false"
```

### 2. **Custom Templates**

Add custom templates in the `templates/` directory. Use `.j2` extension for Jinja2 templates.

**Example**: Create `templates/custom_config.conf.j2`:
```jinja2
# Custom configuration
[framework]
name = {{ project_name }}
version = {{ framework_version }}
port = {{ framework.port }}
```

### 3. **Custom Roles**

Create custom roles in the `roles/` directory:

```bash
ansible-galaxy init roles/custom_role
```

Then include the role in your playbook:
```yaml
- name: Apply custom role
  hosts: venty_stick
  roles:
    - custom_role
```

---

## 🔍 Verification

### Check Setup Status

```bash
# Check if framework is running
ansible -i inventory/hosts.yml venty_stick -m uri -a "url=http://localhost:8080/health"

# Check service status
ansible -i inventory/hosts.yml venty_stick -a "systemctl status nir_framework"

# Check Docker containers
ansible -i inventory/hosts.yml venty_stick -a "docker ps"
```

### Test Framework Commands

```bash
# SSH into Venty stick
ssh -i ~/.ssh/venty_stick_key ubuntu@venty-stick-ip

# Activate virtual environment
source /opt/NIR_Mistral/venv/bin/activate

# Run framework commands
cd /opt/NIR_Mistral
python -m dev_framework info
python -m dev_framework validate
python -m dev_framework generate agent TestAgent
```

---

## 🛠️ Troubleshooting

### Common Issues

#### 1. **SSH Connection Failed**
```bash
# Test SSH connection
ssh -i ~/.ssh/venty_stick_key ubuntu@venty-stick-ip

# Check SSH config
ansible -i inventory/hosts.yml venty_stick -m ping
```

#### 2. **Permission Denied**
```bash
# Ensure SSH key has correct permissions
chmod 600 ~/.ssh/venty_stick_key

# Check user permissions on Venty stick
ssh -i ~/.ssh/venty_stick_key ubuntu@venty-stick-ip "ls -la /opt"
```

#### 3. **Docker Not Running**
```bash
# Start Docker manually
ssh -i ~/.ssh/venty_stick_key ubuntu@venty-stick-ip "sudo systemctl start docker"

# Check Docker status
ssh -i ~/.ssh/venty_stick_key ubuntu@venty-stick-ip "sudo systemctl status docker"
```

#### 4. **Python Virtual Environment Issues**
```bash
# Recreate virtual environment
ssh -i ~/.ssh/venty_stick_key ubuntu@venty-stick-ip "rm -rf /opt/NIR_Mistral/venv"
ansible-playbook -i inventory/hosts.yml playbooks/setup_venty_stick.yml --tags "python"
```

### Debug Mode

Run playbooks in debug mode for detailed output:

```bash
# Verbose mode (-v for more details)
ansible-playbook -i inventory/hosts.yml playbooks/setup_venty_stick.yml -v

# Very verbose mode
ansible-playbook -i inventory/hosts.yml playbooks/setup_venty_stick.yml -vvv

# Debug specific task
ansible-playbook -i inventory/hosts.yml playbooks/setup_venty_stick.yml --step
```

---

## 📊 Monitoring and Maintenance

### Check Framework Health

```bash
# Check framework service
ansible -i inventory/hosts.yml venty_stick -a "systemctl status nir_framework"

# Check logs
ansible -i inventory/hosts.yml venty_stick -a "tail -n 50 /var/log/NIR_Mistral/framework.log"

# Check disk usage
ansible -i inventory/hosts.yml venty_stick -a "df -h"

# Check memory usage
ansible -i inventory/hosts.yml venty_stick -a "free -h"
```

### Update Framework

```bash
# Pull latest code
cd /path/to/local/repo
git pull origin main

# Deploy updates
ansible-playbook -i inventory/hosts.yml playbooks/deploy_framework.yml
```

### Create Backup

```bash
# Create backup
ansible-playbook -i inventory/hosts.yml playbooks/backup_framework.yml

# List backups
ansible -i inventory/hosts.yml venty_stick -a "ls -la /opt/NIR_Mistral/backups/"
```

---

## 🔒 Security Best Practices

### 1. **SSH Security**
- Use SSH keys instead of passwords
- Disable root login
- Disable password authentication
- Use non-standard SSH port

### 2. **Firewall Configuration**
- Enable UFW firewall
- Only allow necessary ports
- Set default policy to DROP

### 3. **Fail2Ban**
- Enable fail2ban for SSH protection
- Configure appropriate ban times
- Whitelist trusted IP addresses

### 4. **Regular Updates**
- Keep system packages updated
- Update Docker images regularly
- Update Python dependencies

---

## 📚 Additional Resources

### Ansible Documentation
- [Ansible Official Documentation](https://docs.ansible.com/)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)
- [Ansible Galaxy](https://galaxy.ansible.com/)

### DeveloperAgent Framework
- [Framework Documentation](../dev_framework/README.md)
- [Project Finalization Report](../PROJECT_FINALIZATION_REPORT.md)
- [System Test Report](../SYSTEM_TEST_REPORT.md)

---

## 🎯 Access Information After Setup

After successful setup, you can access the following services:

| Service | URL | Port | Credentials |
|---------|-----|------|-------------|
| Framework | `http://<venty-stick-ip>:8080` | 8080 | - |
| API | `http://<venty-stick-ip>:8000` | 8000 | - |
| PostgreSQL | `<venty-stick-ip>:5432` | 5432 | nir_user / nir_password_2026 |
| Weaviate | `http://<venty-stick-ip>:8081` | 8081 | - |
| Prometheus | `http://<venty-stick-ip>:9090` | 9090 | - |
| Grafana | `http://<venty-stick-ip>:3000` | 3000 | admin / nir_admin_2026 |

---

## 🏁 Conclusion

The Ansible playbooks in this directory provide a **complete, automated solution** for deploying and managing the **NIR_Mistral DeveloperAgent Framework** on **Venty sticks** and other servers. 

**Key Benefits**:
- ✅ **Automated Setup**: Complete setup in minutes
- ✅ **Consistent Configuration**: Same configuration across all deployments
- ✅ **Easy Updates**: Simple deployment of framework updates
- ✅ **Backup and Restore**: Complete backup and restore capabilities
- ✅ **Scalable**: Works with single Venty sticks or multiple servers
- ✅ **Secure**: Built-in security hardening
- ✅ **Monitored**: Integrated monitoring and logging

**Next Steps**:
1. [Install Ansible](#-quick-start)
2. [Configure SSH Access](#-configure-ssh-access)
3. [Edit Inventory](#-configure-inventory)
4. [Run Setup Playbook](#-run-the-setup-playbook)

---

## 📄 License

This Ansible setup is part of the **NIR_Mistral DeveloperAgent Framework** and is licensed under the same terms as the main project.

## 🤝 Support

For issues or questions:
- Check the [troubleshooting section](#-troubleshooting)
- Review the [System Test Report](../SYSTEM_TEST_REPORT.md)
- Consult the [Project Finalization Report](../PROJECT_FINALIZATION_REPORT.md)
- Open an issue in the project repository