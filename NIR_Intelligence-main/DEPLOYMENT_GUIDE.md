# NIR_Mistral Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the NIR_Mistral platform in various environments, from local development to production deployment on Ventoy bootable USB sticks.

## Deployment Options

### 1. Local Development Deployment

**Use Case**: Development and testing on a local machine.

**Prerequisites**:
- Docker >= 20.10.0
- Docker Compose >= 2.0.0
- Python >= 3.10.0
- Git >= 2.0.0
- Minimum 8GB RAM
- Minimum 50GB disk space

**Steps**:

```bash
# Clone the repository
git clone https://github.com/your-repo/NIR_Mistral.git
cd NIR_Mistral

# Start all services with Docker Compose
docker-compose up -d

# Wait for services to initialize (may take 5-10 minutes)
docker-compose logs -f

# Access the application
# Django Admin: http://localhost:8000/admin
# API: http://localhost:8000/api/
# Dashboard: http://localhost:8000/dashboard/

# Stop services
docker-compose down
```

**Service Ports**:
- Django: `8000`
- PostgreSQL: `5432`
- Weaviate: `8080`
- FAISS: `8081`
- Ollama: `11434`
- Redis: `6379`
- Quarto: `8083`
- Flower (Federated Learning): `5555-5556`

### 2. Production Deployment with Docker

**Use Case**: Production deployment on a server.

**Prerequisites**:
- Docker >= 20.10.0
- Docker Compose >= 2.0.0
- Minimum 16GB RAM
- Minimum 100GB SSD storage
- Linux (Ubuntu 22.04+ recommended)

**Steps**:

```bash
# Clone the repository
git clone https://github.com/your-repo/NIR_Mistral.git
cd NIR_Mistral

# Create .env file for environment variables
cp .env.example .env
# Edit .env with your configuration

# Build and start services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Initialize database
docker-compose exec django_app python django_project/manage.py migrate

# Create superuser
docker-compose exec django_app python django_project/manage.py createsuperuser

# Collect static files
docker-compose exec django_app python django_project/manage.py collectstatic --noinput

# Restart services
docker-compose restart
```

### 3. Ventoy USB Stick Deployment

**Use Case**: Portable deployment on a bootable USB stick for field use or demonstrations.

**Prerequisites**:
- Ventoy bootable USB stick (minimum 64GB)
- Ubuntu 22.04 ISO file
- Target system with USB boot capability

**Steps**:

#### A. Prepare Ventoy Stick

1. **Download Ventoy**:
   ```bash
   wget https://github.com/ventoy/Ventoy/releases/latest/download/ventoy-1.0.96-linux.tar.gz
   tar -xvf ventoy-1.0.96-linux.tar.gz
   cd ventoy-1.0.96
   ```

2. **Install Ventoy on USB**:
   ```bash
   # Identify your USB device (BE CAREFUL - this will erase the device)
   lsblk
   
   # Install Ventoy (replace /dev/sdX with your USB device)
   sudo ./Ventoy2Disk.sh -i /dev/sdX
   ```

3. **Copy Ubuntu ISO**:
   - Download Ubuntu 22.04 LTS ISO
   - Copy to Ventoy USB stick

#### B. Install Ubuntu on Ventoy

1. Boot from Ventoy USB
2. Select Ubuntu ISO and install
3. Choose "Install alongside Ventoy" or manual partitioning
4. Ensure persistent storage is configured

#### C. Deploy NIR_Mistral

```bash
# After Ubuntu installation, open terminal

# Install prerequisites
sudo apt update
sudo apt install -y git docker.io docker-compose ansible python3-pip

# Clone NIR_Mistral
mkdir -p ~/Development
cd ~/Development
git clone https://github.com/your-repo/NIR_Mistral.git
cd NIR_Mistral

# Run Ansible deployment
sudo ansible-playbook ansible/deploy_nir_mistral.yml --ask-become-pass

# Or use the deployment script
sudo ./ansible/ventoy_setup/EXECUTE_DEPLOYMENT.sh -d ventoy
```

### 4. Manual Deployment (Without Docker)

**Use Case**: Deployment on systems where Docker is not available.

**Prerequisites**:
- Python >= 3.10.0
- PostgreSQL >= 14.0
- Redis >= 7.0
- Minimum 8GB RAM

**Steps**:

```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3-pip python3-venv postgresql postgresql-contrib redis-server git

# Create Python virtual environment
python3 -m venv ~/nir_mistral_venv
source ~/nir_mistral_venv/bin/activate

# Clone and setup NIR_Mistral
git clone https://github.com/your-repo/NIR_Mistral.git
cd NIR_Mistral

# Install Python dependencies
pip install -r requirements.txt

# Configure PostgreSQL
sudo -u postgres psql
-- CREATE DATABASE nir_metadata;
-- CREATE USER nir_user WITH PASSWORD 'secure_password';
-- GRANT ALL PRIVILEGES ON DATABASE nir_metadata TO nir_user;
-- \q

# Configure Django
cp django_project/nir_web/settings.py.example django_project/nir_web/settings.py
# Edit settings.py with your database configuration

# Initialize database
python django_project/manage.py migrate
python django_project/manage.py createsuperuser

# Collect static files
python django_project/manage.py collectstatic

# Start services
# Terminal 1: Django
python django_project/manage.py runserver 0.0.0.0:8000

# Terminal 2: Celery worker (optional)
celery -A nir_web worker --loglevel=info

# Terminal 3: Redis (if not running as service)
redis-server
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Django Configuration
DEBUG=0
SECRET_KEY=your-very-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
DATABASE_URL=postgres://nir_user:secure_password@postgresql:5432/nir_metadata

# AI Services
WEAVIATE_URL=http://weaviate:8080
OLLAMA_URL=http://ollama:11434
REDIS_URL=redis://redis:6379/0

# Application Settings
MEDIA_ROOT=/app/media
STATIC_ROOT=/app/static
UPLOAD_LIMIT=104857600  # 100MB
ANALYSIS_TIMEOUT=300  # 5 minutes

# Federated Learning
FLOWER_SERVER_HOST=0.0.0.0
FLOWER_SERVER_PORT=5555
FLOWER_CLIENT_PORT=5556

# Email (for notifications)
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_USE_TLS=True
```

### Django Settings

Edit `django_project/nir_web/settings.py`:

```python
# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'nir_metadata'),
        'USER': os.getenv('DB_USER', 'nir_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'secure_password'),
        'HOST': os.getenv('DB_HOST', 'postgresql'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# AI Services
WEAVIATE_URL = os.getenv('WEAVIATE_URL', 'http://weaviate:8080')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://ollama:11434')
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')

# Security
SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key-change-in-production')
DEBUG = os.getenv('DEBUG', '0') == '1'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
```

## Service Management

### Docker Compose Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f django_app

# Restart specific service
docker-compose restart django_app

# Build and recreate containers
docker-compose up -d --build --force-recreate

# Execute command in container
docker-compose exec django_app python django_project/manage.py migrate

# Clean up unused containers and images
docker system prune -a
```

### Systemd Services (for production)

Create `/etc/systemd/system/nir_mistral.service`:

```ini
[Unit]
Description=NIR Mistral Django Application
After=docker.service network.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/nir_mistral
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
Restart=on-failure
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable nir_mistral
sudo systemctl start nir_mistral
```

## Database Management

### Backup

```bash
# PostgreSQL backup
docker-compose exec postgresql pg_dump -U nir_user -d nir_metadata > backup_$(date +%Y%m%d_%H%M%S).sql

# Or using Docker volume backup
docker run --rm --volumes-from nir_mistral_postgresql_1 -v $(pwd):/backup alpine tar cvf /backup/postgres_backup.tar /var/lib/postgresql/data
```

### Restore

```bash
# PostgreSQL restore
cat backup_file.sql | docker-compose exec -T postgresql psql -U nir_user -d nir_metadata

# Or using Docker volume restore
docker run --rm --volumes-from nir_mistral_postgresql_1 -v $(pwd):/backup alpine tar xvf /backup/postgres_backup.tar -C /
```

## Monitoring and Logging

### View Logs

```bash
# Django logs
docker-compose logs -f django_app

# PostgreSQL logs
docker-compose logs -f postgresql

# All services logs
docker-compose logs -f

# System logs (if using systemd)
journalctl -u nir_mistral -f
```

### Health Checks

```bash
# Check Django health
docker-compose exec django_app python django_project/manage.py check --deploy

# Check database connection
docker-compose exec django_app python -c "import psycopg2; conn = psycopg2.connect('postgresql://nir_user:secure_password@postgresql:5432/nir_metadata'); print('Database connection successful'); conn.close()"

# Check Weaviate
docker-compose exec weaviate curl -X GET http://localhost:8080/v1/.well-known/ready

# Check Ollama
docker-compose exec ollama curl -X GET http://localhost:11434/api/tags
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Find and kill process using port 8000
sudo lsof -i :8000
sudo kill -9 <PID>

# Or use the provided script
./stop_nir_server.sh
```

#### 2. Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps

# Check database logs
docker-compose logs postgresql

# Test connection manually
docker-compose exec django_app python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://nir_user:secure_password@postgresql:5432/nir_metadata')
    print('Connection successful')
    conn.close()
except Exception as e:
    print(f'Connection failed: {e}')
"
```

#### 3. Docker Build Issues

```bash
# Clean and rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

#### 4. Missing Dependencies

```bash
# Install missing Python packages
pip install missing-package

# Or rebuild Docker containers
docker-compose up -d --build
```

#### 5. Permission Issues

```bash
# Fix directory permissions
sudo chown -R $USER:$USER .
sudo chmod -R 755 .

# For Docker volumes
sudo chmod -R 777 data/ media/ logs/
```

### Debug Mode

To enable debug mode for development:

```bash
# In .env file
DEBUG=1

# Or in docker-compose.yml, add to django_app environment:
- DEBUG=1

# Then restart
docker-compose down
docker-compose up -d
```

## Performance Optimization

### Docker Resource Limits

Edit `docker-compose.yml` to limit resource usage:

```yaml
services:
  django_app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
    mem_limit: 2g
    memswap_limit: 4g
```

### Database Optimization

```bash
# Optimize PostgreSQL
docker-compose exec postgresql psql -U nir_user -d nir_metadata

-- Run VACUUM ANALYZE
VACUUM ANALYZE;

-- Check table sizes
SELECT table_name, pg_size_pretty(pg_total_relation_size(table_name)) FROM information_schema.tables WHERE table_schema = 'public';
```

### Caching

Enable Redis caching in Django settings:

```python
# In settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://redis:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Use cache for sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

## Security Considerations

### SSL/TLS Configuration

For production, configure HTTPS:

```bash
# Generate self-signed certificate (for testing)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Configure in Django settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### Firewall Configuration

```bash
# Allow necessary ports
sudo ufw allow 8000/tcp  # Django
sudo ufw allow 5432/tcp  # PostgreSQL (if external access needed)
sudo ufw allow 11434/tcp # Ollama
sudo ufw allow 22/tcp    # SSH

# Enable firewall
sudo ufw enable
```

### Regular Maintenance

```bash
# Update Docker images regularly
docker-compose pull
docker-compose up -d --build

# Clean up old images and containers
docker system prune -a

# Update system packages
sudo apt update && sudo apt upgrade -y
```

## Upgrading

### Version Upgrade

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose pull
docker-compose up -d --build

# Run migrations
docker-compose exec django_app python django_project/manage.py migrate
```

### Dependency Upgrade

```bash
# Update Python packages
pip freeze > requirements_old.txt
pip install --upgrade -r requirements.txt
pip freeze > requirements_new.txt

# Or in Docker
docker-compose build --no-cache
```

## Uninstallation

### Docker Deployment

```bash
# Stop and remove containers
docker-compose down -v

# Remove Docker images
docker rmi nir_mistral_django_app nir_mistral_postgresql nir_mistral_weaviate

# Remove volumes
docker volume prune

# Remove project directory
rm -rf NIR_Mistral
```

### Manual Deployment

```bash
# Stop services
pkill -f "python django_project/manage.py"
pkill -f celery

# Remove files
rm -rf ~/nir_mistral_venv
rm -rf ~/Development/NIR_Mistral

# Remove database (if using PostgreSQL)
sudo -u postgres dropdb nir_metadata
sudo -u postgres dropuser nir_user
```

## Support

### Getting Help

1. **Check Logs**: Most issues can be diagnosed by checking logs
2. **Review Configuration**: Verify all environment variables and settings
3. **Consult Documentation**: Check this guide and the FINALIZATION_REPORT.md
4. **Community Support**: Join the NIR_Mistral community forum

### Useful Commands

```bash
# Check disk usage
docker system df

# Check running containers
docker ps -a

# Check container resource usage
docker stats

# Inspect container
docker inspect nir_mistral_django_app_1

# View container processes
docker top nir_mistral_django_app_1
```

## Appendix A: Sample Data

The system comes with sample spectral data for testing:

```bash
# Load sample data
docker-compose exec django_app python django_project/manage.py load_sample_data

# Or manually upload via web interface
```

## Appendix B: API Endpoints

### Main Endpoints
- `GET /api/` - API root
- `GET /api/spectra/` - List all spectra
- `POST /api/spectra/` - Upload new spectrum
- `GET /api/spectra/{id}/` - Get specific spectrum
- `POST /api/analyze/` - Analyze spectrum
- `GET /api/analysis/{id}/` - Get analysis results
- `GET /api/reports/{id}/` - Get report

### Agent Endpoints
- `GET /api/agents/` - List available agents
- `POST /api/agents/{name}/execute/` - Execute agent
- `GET /api/agents/{name}/status/` - Get agent status

### Health Check
- `GET /api/health/` - Health check endpoint

## Appendix C: Environment Configuration Examples

### Development Environment
```bash
# .env.development
DEBUG=1
SECRET_KEY=dev-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
WEAVIATE_URL=http://localhost:8080
OLLAMA_URL=http://localhost:11434
```

### Production Environment
```bash
# .env.production
DEBUG=0
SECRET_KEY=prod-secret-key-change-this
ALLOWED_HOSTS=your-domain.com,api.your-domain.com
DATABASE_URL=postgres://nir_user:secure_password@postgresql:5432/nir_metadata
WEAVIATE_URL=http://weaviate:8080
OLLAMA_URL=http://ollama:11434
REDIS_URL=redis://redis:6379/0
```

### Docker Environment
```bash
# .env.docker
DEBUG=0
SECRET_KEY=docker-secret-key
ALLOWED_HOSTS=*
DATABASE_URL=postgres://nir_user:secure_password@postgresql:5432/nir_metadata
WEAVIATE_URL=http://weaviate:8080
OLLAMA_URL=http://ollama:11434
REDIS_URL=redis://redis:6379/0
```

---

**Documentation Version**: 1.0.0  
**Last Updated**: 2026-08-07  
**Maintainer**: NIR_Mistral Development Team