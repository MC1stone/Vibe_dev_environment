# NIR_Mistral DeveloperAgent Framework - Installation Guide

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Prerequisites](#-prerequisites)
3. [Installation Methods](#-installation-methods)
4. [Method 1: Manual Installation](#-method-1-manual-installation)
5. [Method 2: Ansible Deployment (Recommended for Venty Stick)](#-method-2-ansible-deployment-recommended-for-venty-stick)
6. [Method 3: Docker Deployment](#-method-3-docker-deployment)
7. [Post-Installation Verification](#-post-installation-verification)
8. [Troubleshooting](#-troubleshooting)
9. [Uninstallation](#-uninstallation)
10. [Next Steps](#-next-steps)

---

## 🎯 Overview

This guide provides step-by-step instructions for installing the **NIR_Mistral DeveloperAgent Framework** on various platforms, with special focus on **Venty stick** deployment.

### **Supported Installation Methods**

| Method | Platform | Complexity | Recommended For |
|--------|----------|------------|-----------------|
| **Manual** | Linux/macOS | Medium | Development, Testing |
| **Ansible** | Linux (Ubuntu/Debian) | Low | **Venty Stick**, Production |
| **Docker** | Any (Docker support) | Low | Containerized environments |

### **System Requirements**

| Component | Minimum | Recommended | Venty Stick |
|-----------|---------|-------------|-------------|
| **OS** | Ubuntu 20.04 / Debian 11 | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| **CPU** | 2 cores | 4+ cores | 4 cores |
| **RAM** | 4GB | 8+ GB | 8GB |
| **Storage** | 20GB | 50+ GB SSD | 64GB USB 3.0 |
| **Python** | 3.8+ | 3.11+ | 3.11 |
| **Docker** | - | 20.10+ | 24.0+ |
| **Network** | - | Stable connection | Ethernet |

---

## 🔧 Prerequisites

### **Common Prerequisites (All Methods)**

#### 1. **Git**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y git

# macOS
brew install git

# Verify
git --version
```

#### 2. **Python**
```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip python3-venv

# macOS
brew install python@3.11

# Verify
python3 --version  # Should be 3.8+
pip3 --version
```

#### 3. **Clone Repository**
```bash
# Clone the NIR_Mistral project
git clone https://github.com/martin/Development/vsCode_Environment/NIR_Mistral.git
cd NIR_Mistral

# Check out the main branch
git checkout main
```

#### 4. **SSH Key Setup (For Venty Stick)**
```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -f ~/.ssh/venty_stick_key -C "nir@venty-stick"

# Set correct permissions
chmod 600 ~/.ssh/venty_stick_key
chmod 644 ~/.ssh/venty_stick_key.pub
```

---

## 🚀 Installation Methods

---

## 📦 Method 1: Manual Installation

### **Step 1: Create Virtual Environment**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# Linux/macOS
source venv/bin/activate

# Windows
# venv\Scripts\activate
```

### **Step 2: Install Dependencies**
```bash
# Install core dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r dev_requirements.txt
```

### **Step 3: Verify Installation**
```bash
# Check Python packages
pip list | grep -E "(flask|fastapi|pydantic|docker|psycopg2)"

# Test framework import
python -c "from dev_framework import __version__; print(f'Framework version: {__version__}')"
```

### **Step 4: Run Framework**
```bash
# Start the framework
python -m dev_framework info

# Validate agents
python -m dev_framework validate
```

### **Step 5: (Optional) Install Quality Tools**
```bash
# Install quality enforcement tools
pip install black flake8 isort mypy pytest pytest-cov

# Verify installation
black --version
flake8 --version
isort --version
mypy --version
pytest --version
```

---

## 🎯 Method 2: Ansible Deployment (Recommended for Venty Stick)

### **Step 1: Install Ansible**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y ansible python3-pip

# macOS
brew install ansible

# Verify
ansible --version
```

### **Step 2: Install Ansible Requirements**
```bash
# Navigate to ansible directory
cd ansible

# Install Python requirements for Ansible
pip install -r requirements.txt

# Install Ansible Galaxy collections
ansible-galaxy install -r galaxy_requirements.yml

# Return to project root
cd ..
```

### **Step 3: Configure Inventory**

Edit `ansible/inventory/hosts.yml`:

```yaml
venty_stick:
  hosts:
    venty-stick:
      ansible_host: 192.168.1.100  # Replace with your Venty stick IP
      ansible_user: ubuntu
      ansible_ssh_private_key_file: ~/.ssh/venty_stick_key
      is_venty_stick: true
      deployment_type: "stick"
      storage_type: "usb"
```

### **Step 4: Test Connectivity**
```bash
# Test SSH connection to Venty stick
ansible -i ansible/inventory/hosts.yml venty_stick -m ping
```

### **Step 5: Run Setup Playbook**
```bash
# Full setup (takes 10-30 minutes)
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/setup_venty_stick.yml

# For Venty stick only
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/setup_venty_stick.yml --limit venty_stick

# With verbose output
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/setup_venty_stick.yml -v
```

### **Step 6: Verify Deployment**
```bash
# SSH into Venty stick
ssh -i ~/.ssh/venty_stick_key ubuntu@192.168.1.100

# Check framework status
sudo systemctl status nir_framework

# Check Docker containers
docker ps

# Test framework commands
cd /opt/NIR_Mistral
source venv/bin/activate
python -m dev_framework info
```

---

## 🐳 Method 3: Docker Deployment

### **Step 1: Install Docker**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Verify
sudo docker run hello-world
```

### **Step 2: Build Docker Image**
```bash
# Build the framework image
docker build -t nir-mistral-framework .

# Check images
docker images
```

### **Step 3: Create Docker Compose File**

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  framework:
    build: .
    container_name: nir_framework
    ports:
      - "8080:8080"
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    environment:
      - FRAMEWORK_PORT=8080
      - API_PORT=8000
      - LOG_LEVEL=INFO
    restart: unless-stopped
    networks:
      - nir_network

  postgresql:
    image: postgres:15
    container_name: nir_postgresql
    ports:
      - "5432:5432"
    volumes:
      - ./data/postgresql:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=nir_user
      - POSTGRES_PASSWORD=nir_password_2026
      - POSTGRES_DB=nir_mistral
    restart: unless-stopped
    networks:
      - nir_network

  weaviate:
    image: semitechnologies/weaviate:1.23
    container_name: nir_weaviate
    ports:
      - "8081:8080"
      - "50051:50051"
    volumes:
      - ./data/weaviate:/var/lib/weaviate
    environment:
      - QUERY_DEFAULTS_LIMIT=25
      - AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true
      - PERSISTENCE_DATA_PATH=/var/lib/weaviate
    restart: unless-stopped
    networks:
      - nir_network

networks:
  nir_network:
    driver: bridge
```

### **Step 4: Start Services**
```bash
# Start all services
docker-compose up -d

# Check running containers
docker-compose ps

# View logs
docker-compose logs -f framework
```

### **Step 5: Test Framework**
```bash
# Test framework endpoint
curl http://localhost:8080/health

# Run framework commands inside container
docker exec -it nir_framework python -m dev_framework info
```

---

## ✅ Post-Installation Verification

### **1. Framework Verification**
```bash
# Check framework version
python -m dev_framework info

# Validate all agents
python -m dev_framework validate

# Check quality
python -m dev_framework quality --check --all
```

### **2. Agent Verification**
```bash
# List all agents
python -m dev_framework info | grep -A 20 "Agents:"

# Test agent generation
python -m dev_framework generate agent TestAgent --force

# Verify generated agent
python -c "from agents.test_agent import TestAgent; print('Agent import successful')"
```

### **3. Service Verification**
```bash
# Check framework service (Ansible deployment)
sudo systemctl status nir_framework

# Check Docker containers (Docker deployment)
docker ps

# Check ports
ss -tulnp | grep -E "(8080|8000|5432|8081|9090|3000)"
```

### **4. Database Verification**
```bash
# Test PostgreSQL connection
psql -h localhost -U nir_user -d nir_mistral -c "SELECT version();"

# Test Weaviate connection
curl http://localhost:8081/v1/.well-known/ready
```

### **5. Monitoring Verification**
```bash
# Check Prometheus
curl http://localhost:9090/-

# Check Grafana
curl http://localhost:3000/api/health
```

---

## 🔍 Troubleshooting

### **Common Issues and Solutions**

#### **1. Python Import Errors**

**Error**: `ModuleNotFoundError: No module named 'dev_framework'`

**Solution**:
```bash
# Ensure you're in the project directory
cd /path/to/NIR_Mistral

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

#### **2. Permission Denied Errors**

**Error**: `Permission denied` when running commands

**Solution**:
```bash
# Check file permissions
ls -la /opt/NIR_Mistral/

# Fix permissions
sudo chown -R $USER:$USER /opt/NIR_Mistral/
sudo chmod -R 755 /opt/NIR_Mistral/
```

#### **3. Docker Connection Errors**

**Error**: `Cannot connect to the Docker daemon`

**Solution**:
```bash
# Start Docker service
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and log back in
logout
```

#### **4. Port Already in Use**

**Error**: `Address already in use` or `Port already allocated`

**Solution**:
```bash
# Find process using port
sudo lsof -i :8080

# Kill the process
sudo kill -9 <PID>

# Or change framework port
python -m dev_framework serve --port 8081
```

#### **5. Database Connection Errors**

**Error**: `Connection refused` for PostgreSQL/Weaviate

**Solution**:
```bash
# Check if containers are running
docker ps

# Start containers if stopped
docker start nir_postgresql nir_weaviate

# Check container logs
docker logs nir_postgresql
docker logs nir_weaviate
```

#### **6. Ansible Connection Issues**

**Error**: `Failed to connect to the host via ssh`

**Solution**:
```bash
# Test SSH connection manually
ssh -i ~/.ssh/venty_stick_key ubuntu@192.168.1.100

# Check SSH key permissions
chmod 600 ~/.ssh/venty_stick_key

# Test Ansible ping
ansible -i ansible/inventory/hosts.yml venty_stick -m ping -v
```

#### **7. Missing Dependencies**

**Error**: `ImportError: No module named 'docker'` or similar

**Solution**:
```bash
# Install missing dependencies
pip install docker psycopg2-binary requests

# Or reinstall all dependencies
pip install -r requirements.txt
```

#### **8. Virtual Environment Issues**

**Error**: `Command not found` for Python commands

**Solution**:
```bash
# Check if virtual environment exists
ls -la venv/bin/python

# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🗑️ Uninstallation

### **Manual Installation**
```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment
rm -rf venv/

# Remove project files (optional)
rm -rf NIR_Mistral/
```

### **Ansible Deployment**
```bash
# Stop framework service
ansible -i ansible/inventory/hosts.yml venty_stick -a "sudo systemctl stop nir_framework"

# Remove Docker containers
ansible -i ansible/inventory/hosts.yml venty_stick -a "docker stop nir_framework nir_postgresql nir_weaviate || true"
ansible -i ansible/inventory/hosts.yml venty_stick -a "docker rm nir_framework nir_postgresql nir_weaviate || true"

# Remove project directory
ansible -i ansible/inventory/hosts.yml venty_stick -a "sudo rm -rf /opt/NIR_Mistral"

# Remove systemd service
ansible -i ansible/inventory/hosts.yml venty_stick -a "sudo rm /etc/systemd/system/nir_framework.service"
ansible -i ansible/inventory/hosts.yml venty_stick -a "sudo systemctl daemon-reload"
```

### **Docker Deployment**
```bash
# Stop and remove containers
docker-compose down

# Remove volumes
docker volume prune -f

# Remove images
docker rmi nir-mistral-framework

# Remove project files
rm -rf NIR_Mistral/ docker-compose.yml
```

---

## 🎯 Next Steps

### **After Successful Installation**

1. **Run Framework Validation**
   ```bash
   python -m dev_framework validate
   ```

2. **Generate Your First Agent**
   ```bash
   python -m dev_framework generate agent MyFirstAgent --template analysis
   ```

3. **Test the Framework**
   ```bash
   python -m dev_framework test --agent MyFirstAgent
   ```

4. **Check Quality**
   ```bash
   python -m dev_framework quality --check --all
   ```

5. **Start Development Server**
   ```bash
   python -m dev_framework serve
   ```

### **For Venty Stick Users**

1. **Access Framework**
   - Open browser: `http://<venty-stick-ip>:8080`

2. **Monitor Services**
   - Prometheus: `http://<venty-stick-ip>:9090`
   - Grafana: `http://<venty-stick-ip>:3000` (admin/nir_admin_2026)

3. **Manage Services**
   ```bash
   # Start framework
   sudo systemctl start nir_framework
   
   # Stop framework
   sudo systemctl stop nir_framework
   
   # Check status
   sudo systemctl status nir_framework
   
   # View logs
   journalctl -u nir_framework -f
   ```

### **For Development**

1. **Set Up Development Environment**
   ```bash
   # Install development dependencies
   pip install -r dev_requirements.txt
   
   # Install pre-commit hooks (optional)
   pip install pre-commit
   pre-commit install
   ```

2. **Run Tests**
   ```bash
   # Run all tests
   pytest tests/ -v
   
   # Run with coverage
   pytest tests/ --cov=dev_framework --cov-report=html
   ```

3. **Code Quality**
   ```bash
   # Run all quality checks
   python -m dev_framework quality --fix --all
   
   # Individual tools
   black dev_framework/
   flake8 dev_framework/
   isort dev_framework/
   mypy dev_framework/
   ```

---

## 📚 Additional Resources

- [DeveloperAgent Framework Documentation](../dev_framework/README.md)
- [Project Finalization Report](../PROJECT_FINALIZATION_REPORT.md)
- [System Test Report](../SYSTEM_TEST_REPORT.md)
- [Ansible Setup Documentation](../ansible/README.md)
- [Configuration Guide](../config/README.md)

---

## 🤝 Support

For issues or questions:

1. **Check this guide** for installation issues
2. **Review the troubleshooting section** for common problems
3. **Consult the System Test Report** for known issues
4. **Open an issue** in the project repository

---

## 📄 License

This installation guide is part of the **NIR_Mistral DeveloperAgent Framework** and is licensed under the same terms as the main project.

---

## 🏁 Conclusion

You have successfully installed the **NIR_Mistral DeveloperAgent Framework**! The framework is now ready for:

- ✅ **Agent Development**: Create and manage NIR spectroscopy agents
- ✅ **Quality Enforcement**: Automatic code quality checking
- ✅ **Testing**: Comprehensive test framework
- ✅ **Deployment**: Easy deployment to Venty sticks and servers
- ✅ **Monitoring**: Built-in monitoring and logging

**Next**: Proceed to the [First Time Usage Guide](./FIRST_TIME_USAGE_GUIDE.md) to start using the framework.