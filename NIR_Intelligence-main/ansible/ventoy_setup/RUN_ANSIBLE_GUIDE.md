# 🚀 Running the Ansible Ventoy Setup - Complete Guide

## 📋 Overview

This guide explains how to run the Ansible playbook for setting up a Ventoy stick with Django server and Port Agent for the NIR_Mistral Framework.

## ⚠️ Prerequisites

### 1. Ansible Installation

First, ensure Ansible is installed:

```bash
# For Debian/Ubuntu
sudo apt update
sudo apt install ansible

# For RedHat/CentOS
sudo yum install ansible

# For macOS
brew install ansible
```

Verify installation:
```bash
ansible --version
```

### 2. Python and pip

Ensure Python 3 and pip are available:
```bash
python3 --version
pip3 --version
```

## 🔐 Sudo Configuration (Choose One Option)

### Option A: Passwordless Sudo (Recommended for Automation)

1. Edit sudoers file:
   ```bash
   sudo visudo
   ```

2. Add this line (replace `martin` with your username):
   ```
   martin ALL=(ALL) NOPASSWD:ALL
   ```

3. Save and exit (Ctrl+X, Y, Enter in nano)

### Option B: Use --ask-become-pass

Run the playbook with password prompt:
```bash
ansible-playbook site.yml --ask-become-pass
```

### Option C: Run as Root

```bash
sudo su -
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/ansible/ventoy_setup
ansible-playbook site.yml
```

## 🎯 Running the Playbook

### 1. Navigate to the Ventoy Setup Directory

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/ansible/ventoy_setup
```

### 2. Choose Your Deployment Method

#### 🔹 Full Deployment (Recommended)

```bash
# With passwordless sudo configured
ansible-playbook site.yml

# With password prompt
ansible-playbook site.yml --ask-become-pass
```

#### 🔹 Local Development (No Sudo Required)

```bash
ansible-playbook site_local.yml
```

This installs everything in your home directory without requiring sudo.

#### 🔹 Target Specific Components

```bash
# Only system preparation
ansible-playbook site.yml -e "skip_django=true skip_port_agent=true skip_ventoy=true"

# Only Django server
ansible-playbook site.yml -e "skip_dependencies=true skip_port_agent=true skip_ventoy=true"

# Only Port Agent
ansible-playbook site.yml -e "skip_dependencies=true skip_django=true skip_ventoy=true"

# Only Ventoy configuration
ansible-playbook site.yml -e "skip_dependencies=true skip_django=true skip_port_agent=true"
```

#### 🔹 Environment-Specific Deployment

```bash
# Development environment
ansible-playbook site.yml -e "environment=development"

# Production environment
ansible-playbook site.yml -e "environment=production"
```

### 3. Inventory and Host Configuration

The playbook uses the `inventory.ini` file. You can:

- **Use the default** (localhost):
  ```bash
  ansible-playbook site.yml -i inventory.ini
  ```

- **Target specific hosts**:
  ```bash
  ansible-playbook site.yml -l ventoy_stick
  ansible-playbook site.yml -l django_servers
  ansible-playbook site.yml -l port_agent_servers
  ```

- **Use a custom inventory**:
  ```bash
  ansible-playbook site.yml -i /path/to/your/inventory
  ```

## 🔍 Testing Before Full Deployment

### 1. Syntax Check

```bash
# Test YAML syntax of all files
./test_ansible_syntax.sh

# Or manually check specific files
python3 -c "import yaml; yaml.safe_load(open('site.yml')); print('site.yml: OK')"
```

### 2. Dry Run (Show what would happen)

```bash
ansible-playbook site.yml --check
```

### 3. List All Tasks

```bash
ansible-playbook site.yml --list-tasks
```

### 4. List All Hosts

```bash
ansible-playbook site.yml --list-hosts
```

## 🛠️ Troubleshooting

### Common Errors and Solutions

#### Error: "sudo: Ein Passwort ist notwendig" (Password required)

**Solution 1**: Configure passwordless sudo (recommended)
```bash
sudo visudo
# Add: martin ALL=(ALL) NOPASSWD:ALL
```

**Solution 2**: Use --ask-become-pass
```bash
ansible-playbook site.yml --ask-become-pass
```

**Solution 3**: Use the local version
```bash
ansible-playbook site_local.yml
```

#### Error: "ansible-playbook: command not found"

**Solution**: Install Ansible
```bash
sudo apt install ansible  # Debian/Ubuntu
sudo yum install ansible  # RedHat/CentOS
```

#### Error: "No module named yaml"

**Solution**: Install PyYAML
```bash
pip install pyyaml
```

#### Error: "Host not found in inventory"

**Solution**: Check your inventory file or use localhost
```bash
ansible-playbook site.yml -i inventory.ini
```

#### Error: "Connection failed: localhost"

**Solution**: Use local connection
```bash
ansible-playbook site.yml -c local
```

## 📊 Monitoring Progress

### View Detailed Output

```bash
# Verbose mode (-v for more details, -vvv for maximum)
ansible-playbook site.yml -v
ansible-playbook site.yml -vvv
```

### Run Specific Tags

```bash
# Only run system preparation tasks
ansible-playbook site.yml --tags "system"

# Only run Django tasks
ansible-playbook site.yml --tags "django"

# Skip specific tags
ansible-playbook site.yml --skip-tags "verification"
```

### Step-by-Step Execution

```bash
# Run one step at a time
ansible-playbook site.yml --step
```

## 🎉 Post-Deployment Verification

### 1. Check Services

```bash
# Check if Django is running
curl http://localhost:8000/api/health/

# Check if Port Agent is running  
curl http://localhost:8001/api/ports/
```

### 2. Check Logs

```bash
# View Django logs
tail -f ~/nir_mistral_ventoy/logs/django.log

# View Port Agent logs
tail -f ~/nir_mistral_ventoy/logs/port_agent.log
```

### 3. Manual Startup

If services didn't start automatically:

```bash
# Navigate to deployment directory
cd ~/nir_mistral_ventoy

# Start services manually
./start_nir_mistral.sh
```

## 📝 Configuration Options

### Custom Variables

You can override any variable using the `-e` flag:

```bash
# Custom ports
ansible-playbook site.yml -e "django_port=8080 port_agent_port=8081"

# Custom deployment location
ansible-playbook site.yml -e "deploy_root=/opt/nir_mistral"

# Disable specific features
ansible-playbook site.yml -e "create_systemd_services=false firewall_enabled=false"
```

### Available Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `deploy_root` | `/opt/nir_mistral` | Base deployment directory |
| `django_port` | 8000 | Django server port |
| `port_agent_port` | 8001 | Port Agent port |
| `environment` | `production` | Deployment environment |
| `django_debug` | `false` | Django debug mode |
| `create_systemd_services` | `true` | Create systemd services |
| `install_dependencies` | `true` | Install system dependencies |
| `firewall_enabled` | `false` | Enable firewall configuration |
| `install_docker` | `false` | Install Docker |
| `create_swap_file` | `true` | Create swap file |

## 🏁 Quick Start Commands

### For Local Development (No Sudo)
```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/ansible/ventoy_setup
ansible-playbook site_local.yml
```

### For Production (With Sudo)
```bash
# First configure passwordless sudo
sudo visudo
# Add: martin ALL=(ALL) NOPASSWD:ALL

# Then run the playbook
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/ansible/ventoy_setup
ansible-playbook site.yml
```

### For Testing
```bash
# Syntax check
./test_ansible_syntax.sh

# Dry run
ansible-playbook site.yml --check

# Limited run (just Django)
ansible-playbook site.yml -e "skip_dependencies=true skip_port_agent=true skip_ventoy=true"
```

## 🔗 Related Files

- `site.yml` - Main production playbook
- `site_local.yml` - Local development playbook (no sudo)
- `inventory.ini` - Host inventory configuration
- `ansible.cfg` - Ansible configuration
- `test_ansible_syntax.sh` - YAML syntax validation script
- `roles/` - Ansible roles directory

## 💡 Tips

1. **Start small**: Test with `site_local.yml` first to ensure everything works
2. **Use tags**: Run specific parts using `--tags` and `--skip-tags`
3. **Check logs**: Always check the logs in the deployment directory
4. **Verify services**: Use `curl` to test the API endpoints after deployment
5. **Backup**: Consider backing up important files before running the playbook

## 🎉 Success!

Once the playbook completes successfully, you should have:
- ✅ Django server running on port 8000
- ✅ Port Agent running on port 8001  
- ✅ All API endpoints available
- ✅ Proper logging configuration
- ✅ System services (if enabled)

Access your services:
- Django: http://localhost:8000
- Port Agent API: http://localhost:8001/api/ports/
- Health check: http://localhost:8000/api/health/