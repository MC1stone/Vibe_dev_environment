# NIR Intelligence Platform - Quick Start Guide

## ⚠️ Important Notes for Debian/Ubuntu Users

### 1. Python Environment Issue
Your system has an **externally-managed Python environment**. You must use a **virtual environment**:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Now install dependencies
pip install -r requirements.txt
```

### 2. Docker Image Issues
The Quarto image has been removed from the docker-compose file. The platform works without it.

### 3. Use python3 instead of python
Debian/Ubuntu use `python3` instead of `python`. Update all commands accordingly.

---

## 🚀 Quick Setup (Fixed for Debian/Ubuntu)

### Step 1: Clone Repository
```bash
git clone https://github.com/MC1stone/Vibe_dev_environment
cd Vibe_dev_environment/nir_platform
```

### Step 2: Create Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate it (do this every time you work with the project)
source venv/bin/activate

# Your prompt should now show (venv)
```

### Step 3: Install Dependencies
```bash
# Upgrade pip first
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

### Step 4: Start Docker Services
```bash
# Navigate to docker directory
cd docker

# Start containers (this may take several minutes)
docker compose up -d

# Wait for containers to initialize (check status)
docker ps
```

**Expected Containers:**
- `nir_django` - Django web application
- `nir_postgres` - PostgreSQL database
- `nir_qdrant` - Qdrant vector database
- `nir_ollama` - Ollama with Mistral model
- `nir_n8n` - n8n workflow automation
- `nir_mcp` - MCP server

### Step 5: Pull Mistral Model
```bash
# Pull the Mistral model (this may take a while)
curl -X POST http://localhost:11434/api/pull -d '{"name": "mistral"}' -H "Content-Type: application/json"

# Check if model is ready
curl http://localhost:11434/api/tags
```

### Step 6: Set Up Django
```bash
# Navigate to django_app
cd ../django_app

# Create directories
mkdir -p uploads reports static media

# Run migrations
python3 manage.py migrate

# Create superuser (optional)
python3 manage.py createsuperuser
```

### Step 7: Start Django Server
```bash
# Make sure virtual environment is activated
source ../venv/bin/activate

# Start server
python3 manage.py runserver
```

### Step 8: Access the Platform
Open your browser and navigate to:
- **Django UI**: http://localhost:8000
- **n8n**: http://localhost:5678 (username: admin, password: nir2024)
- **Ollama**: http://localhost:11434

---

## 🐳 Docker Troubleshooting

### If Docker Images Fail to Pull

#### Issue: "pull access denied for quarto/quarto"
**Solution:** This image has been removed from docker-compose.yml. The platform works without it.

#### Issue: "Image qdrant/qdrant:v1.7.0 Interrupted"
**Solution:** Use the updated docker-compose.yml which uses v1.8.0:
```bash
cd docker
docker compose pull
```

#### Issue: Containers won't start
```bash
# Check logs
docker compose logs

# Restart containers
docker compose down
docker compose up -d
```

### Check Container Status
```bash
docker ps -a
```

All containers should show:
- Status: `Up X seconds` or `Up X minutes`
- Ports: Correctly mapped

---

## 🐍 Python Troubleshooting

### If you get "externally-managed-environment" error

**Solution:** Always use the virtual environment:
```bash
# Activate virtual environment
source venv/bin/activate

# Then run pip commands
pip install package_name
```

### If "python: command not found"
**Solution:** Use `python3` instead:
```bash
python3 manage.py runserver
```

### Check Python Version
```bash
python3 --version
# Should be Python 3.8+
```

---

## 🌐 Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Django | http://localhost:8000 | - |
| n8n | http://localhost:5678 | admin / nir2024 |
| Ollama | http://localhost:11434 | - |
| PostgreSQL | localhost:5432 | postgres / postgres |
| Qdrant | http://localhost:6333 | - |
| MCP Server | http://localhost:8001 | - |

---

## 📝 Common Commands

### Start All Services
```bash
cd docker
docker compose up -d
```

### Stop All Services
```bash
cd docker
docker compose down
```

### View Logs
```bash
cd docker
docker compose logs -f
```

### Restart Specific Service
```bash
cd docker
docker compose restart django
```

### Update Docker Images
```bash
cd docker
docker compose pull
docker compose up -d
```

---

## 🎯 First Steps After Setup

1. **Upload spectral data** via the Django web interface
2. **Wait for analysis** to complete (may take a few minutes)
3. **View results** in the analysis detail page
4. **Generate reports** with Quarto
5. **Chat with AI** agents for questions

---

## 🔧 Additional Configuration

### Configure Database
Edit `django_app/nir_platform/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nir_db',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Configure Agent Settings
Edit `django_app/nir_platform/settings.py`:
```python
AGENT_CONFIG = {
    'mcp_server_url': 'http://localhost:8001',
    'crewai_url': 'http://localhost:8002',
    'qdrant_url': 'http://localhost:6333',
    'faiss_url': 'http://localhost:5001',
    'ollama_url': 'http://localhost:11434',
    'n8n_url': 'http://localhost:5678'
}
```

---

## 📞 Support

If you encounter issues:

1. **Check logs**: `docker compose logs`
2. **Verify containers**: `docker ps`
3. **Test connections**:
   ```bash
   curl http://localhost:8000
   curl http://localhost:11434/api/tags
   ```
4. **Check database**:
   ```bash
   psql -h localhost -U postgres -d nir_db
   ```

---

## 🎉 Success!

Once everything is running, you should be able to:
- ✅ Access Django at http://localhost:8000
- ✅ Upload spectral data files
- ✅ View analysis results
- ✅ Generate comprehensive reports
- ✅ Chat with AI agents
- ✅ Manage your data

**Enjoy using the NIR Intelligence Platform!**
