# 🚀 NIR_MISTRAL Docker Startup Guide

This guide will help you start all Docker containers and verify that all services are available at their designated ports.

## 📋 Prerequisites

Before starting, ensure you have:

1. **Docker installed and running**
   - Docker version 20.10+
   - Docker Compose version 1.29+
   - At least 8GB RAM (16GB recommended)
   - 20GB+ free disk space

2. **Docker is running**
   ```bash
   # Check if Docker is running
   docker info
   
   # If not running, start Docker
   # Linux: sudo systemctl start docker
   # Mac: Open Docker Desktop
   # Windows: Start Docker Desktop
   ```

---

## 🎯 Step 1: Prepare Your Environment

### 1.1 Navigate to Project Directory

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral
```

### 1.2 Verify Project Structure

Run the path test to ensure everything is configured correctly:

```bash
./test_docker_paths.sh
```

You should see:
```
✅ django_project/manage.py exists
✅ Command 'python django_project/manage.py' should work
✅ django_project/nir_web/settings.py exists
✅ DJANGO_SETTINGS_MODULE=nir_web.settings is correct
✅ WSGI module path is correct
```

### 1.3 Check Environment Variables

```bash
./test_env.sh
```

This will show you the current environment variables and confirm they're loaded correctly.

---

## 🚀 Step 2: Start Docker Containers

### Option A: Development Mode (Recommended for Testing)

```bash
# Start all containers in development mode
docker-compose up -d
```

### Option B: Production Mode

```bash
# Start all containers in production mode
docker-compose -f docker-compose.prod.yml up -d --build
```

### 2.1 Monitor Startup Process

Watch the containers start up:

```bash
# View logs for all services
docker-compose logs -f

# Or view logs for specific services
docker-compose logs -f django_app
docker-compose logs -f postgres
docker-compose logs -f weaviate
docker-compose logs -f ollama
```

### 2.2 Check Container Status

```bash
# List all running containers
docker-compose ps

# Or for production mode
docker-compose -f docker-compose.prod.yml ps
```

You should see containers with status "Up" for:
- `django_app` (or `web` in production)
- `postgresql` (or `postgres`)
- `weaviate`
- `faiss`
- `ollama`
- `redis`
- And others depending on your configuration

---

## 🔍 Step 3: Verify Services Are Running

### 3.1 Run the Monitoring Script

```bash
# For development mode
./monitor_services.sh

# For production mode
./monitor_services.sh --production
# or
./monitor_services.sh -p
```

This script will:
1. ✅ Check if Docker is running
2. ✅ Check if all containers are running
3. ✅ Check if all ports are open
4. ✅ Check if all HTTP endpoints are responding
5. ✅ Provide detailed service information

### 3.2 Expected Output

If everything is working correctly, you should see:

```
🚀 NIR_MISTRAL Service Monitoring
================================

✅ Docker is running

📋 Mode: development
📄 Compose file: docker-compose.yml

🐳 Checking Docker containers...
--------------------------------
✅ Django Web Application container is running (Up 2 minutes)
✅ PostgreSQL Database container is running (Up 2 minutes)
✅ Weaviate Vector Database container is running (Up 2 minutes)
✅ Faiss Similarity Search container is running (Up 2 minutes)
✅ Ollama AI Service container is running (Up 2 minutes)
✅ Redis Cache container is running (Up 2 minutes)

📊 Container Summary: 6/6 containers running

🌐 Checking service ports...
----------------------------
✅ Django Web Application is available at localhost:8000
✅ PostgreSQL Database is available at localhost:5432
✅ Weaviate Vector Database is available at localhost:8080
✅ Faiss Similarity Search is available at localhost:8081
✅ Ollama AI Service is available at localhost:11434
✅ Redis Cache is available at localhost:6379

📊 Port Summary: 6/6 ports open

🔗 Checking HTTP endpoints...
-----------------------------
✅ Django Health Check HTTP endpoint http://localhost:8000/health/ is responding
✅ Weaviate Health HTTP endpoint http://localhost:8080/v1/.well-known/ready is responding
✅ Ollama API HTTP endpoint http://localhost:11434/api/tags is responding
✅ Faiss Health HTTP endpoint http://localhost:8081/health is responding

📊 HTTP Endpoint Summary: 4/4 endpoints responding

🎉 ALL SERVICES ARE RUNNING CORRECTLY! 🎉

You can now access:
  - Web Application: http://localhost:8000
  - Admin Panel: http://localhost:8000/admin
  - All AI services at their respective ports
```

---

## 🌐 Step 4: Access Services

Once all services are running, you can access them at these URLs:

### 🏠 Core Application
| Service | URL | Description |
|---------|-----|-------------|
| **Web Application** | [http://localhost:8000](http://localhost:8000) | Main NIR_MISTRAL application |
| **Admin Panel** | [http://localhost:8000/admin](http://localhost:8000/admin) | Django admin interface |
| **Health Check** | [http://localhost:8000/health/](http://localhost:8000/health/) | Service health status |
| **API Documentation** | [http://localhost:8000/api/](http://localhost:8000/api/) | API endpoints and documentation |

### 🤖 AI Services
| Service | URL | Description |
|---------|-----|-------------|
| **Weaviate** | [http://localhost:8080](http://localhost:8080) | Vector database for spectral data |
| **Weaviate Health** | [http://localhost:8080/v1/.well-known/ready](http://localhost:8080/v1/.well-known/ready) | Weaviate health check |
| **Faiss** | [http://localhost:8081](http://localhost:8081) | Similarity search service |
| **Faiss Health** | [http://localhost:8081/health](http://localhost:8081/health) | Faiss health check |
| **Ollama** | [http://localhost:11434](http://localhost:11434) | Local LLM service |
| **Ollama API** | [http://localhost:11434/api/tags](http://localhost:11434/api/tags) | Ollama API endpoints |

### 🗄️ Data Services
| Service | URL | Description |
|---------|-----|-------------|
| **PostgreSQL** | localhost:5432 | Database service (not HTTP) |
| **Redis** | localhost:6379 | Cache and task queue (not HTTP) |

### 🌐 Federated Learning
| Service | URL | Description |
|---------|-----|-------------|
| **Flower Server** | localhost:5555 | Flower federated learning server |
| **Flower Management** | [http://localhost:5556](http://localhost:5556) | Flower HTTP management API |
| **Flower Health** | [http://localhost:5556/health](http://localhost:5556/health) | Flower health check |

### 📊 Monitoring (Production Only)
| Service | URL | Description |
|---------|-----|-------------|
| **Prometheus** | [http://localhost:9090](http://localhost:9090) | Metrics collection |
| **Grafana** | [http://localhost:3000](http://localhost:3000) | Dashboards (admin/admin) |
| **Nginx** | [http://localhost:80](http://localhost:80) | Reverse proxy |

---

## 🔧 Step 5: Initialize the Application

### 5.1 Run Database Migrations

```bash
# For development mode
docker-compose exec django_app python django_project/manage.py migrate

# For production mode
docker-compose -f docker-compose.prod.yml exec web python django_project/manage.py migrate
```

### 5.2 Create Superuser (Admin)

```bash
# For development mode
docker-compose exec django_app python django_project/manage.py createsuperuser

# For production mode
docker-compose -f docker-compose.prod.yml exec web python django_project/manage.py createsuperuser
```

Follow the prompts to create an admin user.

### 5.3 Pull Mistral Model for Ollama

```bash
# Check if Mistral model is already downloaded
docker-compose exec ollama ollama list

# If Mistral is not listed, download it
docker-compose exec ollama ollama pull mistral
```

This may take a while (several minutes) depending on your internet connection.

---

## 🧪 Step 6: Test the Services

### 6.1 Test Django Application

```bash
# Test health endpoint
curl http://localhost:8000/health/

# Test API root
curl http://localhost:8000/api/
```

### 6.2 Test Database Connection

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U nir_user -d nir_mistral

# Run a test query
SELECT 1;

# Exit
\q
```

### 6.3 Test AI Services

```bash
# Test Weaviate
curl http://localhost:8080/v1/.well-known/ready

# Test Faiss
curl http://localhost:8081/health

# Test Ollama
curl http://localhost:11434/api/tags

# Test Redis
docker-compose exec redis redis-cli ping
```

---

## 🛠️ Troubleshooting

### Common Issues and Solutions

#### 1. Port Already in Use

**Error:** `Error: Address already in use`

**Solution:**
```bash
# Find which process is using the port
sudo lsof -i :8000

# Kill the process (replace PID with actual process ID)
kill -9 PID

# Or stop all containers and restart
docker-compose down
docker-compose up -d
```

#### 2. Database Connection Issues

**Error:** `Connection refused` or `database does not exist`

**Solution:**
```bash
# Check if PostgreSQL container is running
docker-compose ps

# Check PostgreSQL logs
docker-compose logs postgres

# Wait for database to be ready (may take 30-60 seconds)
sleep 30

# Test database connection
docker-compose exec postgres psql -U nir_user -d nir_mistral -c "SELECT 1;"
```

#### 3. Migration Errors

**Error:** `No such file or directory` or migration conflicts

**Solution:**
```bash
# Remove old migrations (be careful!)
find django_project -name "*.pyc" -delete
find django_project -name "__pycache__" -type d -exec rm -r {} + 2>/dev/null || true

# Recreate migrations
docker-compose exec django_app python django_project/manage.py makemigrations
docker-compose exec django_app python django_project/manage.py migrate
```

#### 4. Missing Dependencies

**Error:** `ModuleNotFoundError` or import errors

**Solution:**
```bash
# Install missing packages in the container
docker-compose exec django_app pip install missing-package

# Or rebuild the container
docker-compose build --no-cache django_app
docker-compose up -d
```

#### 5. Permission Issues

**Error:** `Permission denied`

**Solution:**
```bash
# Fix directory permissions
sudo chown -R $USER:$USER .
chmod -R 755 .

# Or run as root (not recommended)
sudo docker-compose up -d
```

---

## 📊 Step 7: Monitor and Manage Services

### 7.1 View Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f django_app
docker-compose logs -f postgres
docker-compose logs -f weaviate

# View last 100 lines of logs
docker-compose logs --tail=100
```

### 7.2 Check Resource Usage

```bash
# View container resource usage
docker stats

# View disk usage
docker system df
```

### 7.3 Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart django_app
```

### 7.4 Stop Services

```bash
# Stop all containers
docker-compose down

# Stop and remove containers, networks, and volumes
docker-compose down -v
```

---

## 🎉 Step 8: Verify Everything is Working

Run the comprehensive monitoring script:

```bash
./monitor_services.sh
```

If you see `🎉 ALL SERVICES ARE RUNNING CORRECTLY! 🎉`, then everything is working properly!

---

## 📋 Quick Reference Commands

### Start Services
```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d --build
```

### Stop Services
```bash
docker-compose down
```

### View Status
```bash
./monitor_services.sh
docker-compose ps
```

### View Logs
```bash
docker-compose logs -f
```

### Run Management Commands
```bash
docker-compose exec django_app python django_project/manage.py [command]
```

### Access Database
```bash
docker-compose exec postgres psql -U nir_user -d nir_mistral
```

---

## 🚨 Emergency Stop

If something goes wrong and you need to stop everything:

```bash
# Stop all containers
docker-compose down

# Remove all containers, networks, and volumes
docker-compose down -v

# Remove all Docker containers, networks, images, and volumes
# WARNING: This will remove ALL Docker containers, not just NIR_MISTRAL
docker system prune -a --volumes
```

---

## 📚 Next Steps

Once all services are running correctly, you can:

1. **Test the web interface** at [http://localhost:8000](http://localhost:8000)
2. **Log in to the admin panel** at [http://localhost:8000/admin](http://localhost:8000/admin)
3. **Test the API endpoints** using curl or Postman
4. **Upload spectral data** and test the analysis features
5. **Set up monitoring** with Prometheus and Grafana (production mode)
6. **Configure CI/CD** for automated deployments

---

## 💬 Support

If you encounter any issues:

1. **Check the logs**: `docker-compose logs -f`
2. **Run the monitoring script**: `./monitor_services.sh`
3. **Check this guide** for troubleshooting tips
4. **Review the Docker documentation** for your specific issue

---

**Last Updated**: 2026-08-10  
**Version**: 1.0.0  
**Status**: Ready for Docker deployment 🚀