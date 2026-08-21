# NIR_MISTRAL Docker Infrastructure

This document provides comprehensive instructions for setting up and running the NIR_MISTRAL application using Docker.

## 📋 Overview

The NIR_MISTRAL Docker infrastructure includes:

- **Django Web Application** - Main NIR spectroscopy analysis platform
- **PostgreSQL Database** - Production-ready database for data storage
- **Weaviate Vector Database** - Vector search for spectral data similarity
- **Faiss Similarity Search** - Efficient similarity search for documentation
- **Ollama with Mistral** - Local LLM for analysis and recommendations
- **Redis** - Caching and task queue for Celery
- **Celery Workers** - Async task processing
- **Flower Server** - Federated learning framework
- **Quarto** - Report generation
- **Nginx** - Reverse proxy (optional for production)
- **Prometheus & Grafana** - Monitoring and observability

## 🚀 Quick Start

### Prerequisites

- Docker (version 20.10+)
- Docker Compose (version 1.29+)
- At least 8GB RAM (16GB recommended)
- 20GB+ free disk space

### 1. Clone the Repository

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral
```

### 2. Set Up Environment Variables

Copy the example environment file:

```bash
cp .env.docker .env
```

Edit `.env` to configure your settings (especially `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD`).

### 3. Build and Start the Containers

For **development** (uses existing docker-compose.yml):

```bash
docker-compose up -d
```

For **production** (uses docker-compose.prod.yml):

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

### 4. Initialize the Database

Run Django migrations:

```bash
docker-compose exec django_app python django_project/manage.py migrate
```

Create a superuser:

```bash
docker-compose exec django_app python django_project/manage.py createsuperuser
```

### 5. Pull Mistral Model

Pull the Mistral model for Ollama:

```bash
docker-compose exec ollama ollama pull mistral
```

### 6. Access the Application

- **Web Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **Weaviate**: http://localhost:8080
- **Faiss**: http://localhost:8081
- **Ollama**: http://localhost:11434
- **Redis**: http://localhost:6379
- **Flower Server**: http://localhost:5555
- **Flower Management**: http://localhost:5556
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000

## 📁 File Structure

```
nir_mistral/
├── docker-compose.yml          # Development configuration
├── docker-compose.prod.yml     # Production configuration
├── Dockerfile.django           # Development Django Dockerfile
├── Dockerfile.prod             # Production Django Dockerfile
├── .env.docker                 # Environment variables template
├── services/
│   ├── faiss_server.py         # Faiss HTTP server
│   └── flower_server.py        # Flower federated learning server
├── scripts/
│   └── init-db.sql             # Database initialization script
├── config/
│   ├── nginx.conf              # Nginx reverse proxy configuration
│   └── prometheus.yml          # Prometheus monitoring configuration
└── data/
    └── faiss_index/            # Faiss index storage
```

## 🛠️ Configuration Options

### Development vs Production

| Feature | Development | Production |
|---------|-------------|------------|
| Web Server | Django dev server | Gunicorn |
| Database | PostgreSQL | PostgreSQL |
| Static Files | Served by Django | Served by Nginx |
| Debug Mode | True | False |
| Logging | Console | File + Console |
| Security Headers | Basic | Full |

### Environment Variables

Key environment variables you can configure:

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True/False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
POSTGRES_PASSWORD=your-password
DJANGO_DB_NAME=nir_mistral
DJANGO_DB_USER=nir_user

# AI Services
WEAVIATE_URL=http://weaviate:8080
OLLAMA_URL=http://ollama:11434
FAISS_URL=http://faiss:8081
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Quarto
QUARTO_ENABLED=True/False
QUARTO_PATH=/usr/bin/quarto
```

## 🔧 Common Commands

### Start Services

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d --build
```

### Stop Services

```bash
# Development
docker-compose down

# Production
docker-compose -f docker-compose.prod.yml down
```

### View Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f web
docker-compose logs -f postgres
docker-compose logs -f ollama
```

### Database Operations

```bash
# Run migrations
docker-compose exec django_app python django_project/manage.py migrate

# Create superuser
docker-compose exec django_app python django_project/manage.py createsuperuser

# Backup database
docker-compose exec postgres pg_dump -U nir_user nir_mistral > backup.sql

# Restore database
docker-compose exec postgres psql -U nir_user nir_mistral < backup.sql
```

### Django Management Commands

```bash
# Run any Django management command
docker-compose exec django_app python django_project/manage.py [command]

# Examples:
docker-compose exec django_app python django_project/manage.py collectstatic
docker-compose exec django_app python django_project/manage.py check --deploy
```

### AI Model Operations

```bash
# Pull Mistral model
docker-compose exec ollama ollama pull mistral

# List available models
docker-compose exec ollama ollama list

# Remove a model
docker-compose exec ollama ollama rm mistral
```

### Testing Services

```bash
# Test Weaviate
docker-compose exec weaviate curl http://localhost:8080/v1/.well-known/ready

# Test Faiss
docker-compose exec faiss curl http://localhost:8081/health

# Test Ollama
docker-compose exec ollama curl http://localhost:11434/api/tags

# Test Flower
docker-compose exec flower_server curl http://localhost:5556/health
```

## 🌐 Service Endpoints

### Django Application
- **Main App**: http://localhost:8000
- **Admin**: http://localhost:8000/admin
- **API**: http://localhost:8000/api/
- **Health Check**: http://localhost:8000/health/

### AI Services
- **Weaviate**: http://localhost:8080
- **Faiss**: http://localhost:8081
- **Ollama**: http://localhost:11434

### Monitoring
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### Federated Learning
- **Flower Server**: http://localhost:5555
- **Flower Management**: http://localhost:5556

### Cache & Queue
- **Redis**: http://localhost:6379

## 📊 Monitoring and Observability

### Prometheus Metrics

Prometheus is configured to scrape metrics from:
- Django application (`/metrics`)
- PostgreSQL (requires `postgres_exporter`)
- Redis (requires `redis_exporter`)
- Weaviate (`/v1/.well-known/metrics`)
- All custom services (`/health`)

### Grafana Dashboards

Access Grafana at http://localhost:3000 with credentials:
- Username: `admin`
- Password: `admin` (or as configured in `.env`)

## 🔄 Data Migration

### From SQLite to PostgreSQL

1. **Backup your SQLite database**:
   ```bash
   cp django_project/db.sqlite3 django_project/db.sqlite3.backup
   ```

2. **Start PostgreSQL container**:
   ```bash
   docker-compose up -d postgres
   ```

3. **Run migration script**:
   ```bash
   # Create a migration script
   cat > migrate_to_postgres.py << 'EOF'
   import os
   import django
   
   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
   django.setup()
   
   from django.core.management import execute_from_command_line
   from django.db import connection
   
   # Configure PostgreSQL connection
   os.environ['DJANGO_DB_ENGINE'] = 'postgresql'
   os.environ['DJANGO_DB_NAME'] = 'nir_mistral'
   os.environ['DJANGO_DB_USER'] = 'nir_user'
   os.environ['DJANGO_DB_PASSWORD'] = 'nir_password_2026'
   os.environ['DJANGO_DB_HOST'] = 'postgres'
   os.environ['DJANGO_DB_PORT'] = '5432'
   
   # Reconfigure Django database connection
   from django.conf import settings
   settings.DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'nir_mistral',
           'USER': 'nir_user',
           'PASSWORD': 'nir_password_2026',
           'HOST': 'postgres',
           'PORT': '5432',
       }
   }
   
   # Run migrations
   execute_from_command_line(['manage.py', 'migrate'])
   
   # Import data from SQLite (you would need to implement this)
   print("Migration complete. Manual data import may be required.")
   EOF
   
   docker-compose exec django_app python migrate_to_postgres.py
   ```

## 🛡️ Security Considerations

### Production Security Checklist

- [ ] Change all default passwords
- [ ] Set `DJANGO_SECRET_KEY` to a strong random value
- [ ] Set `DJANGO_DEBUG=False`
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Enable HTTPS with valid certificates
- [ ] Configure firewall rules
- [ ] Set up proper authentication
- [ ] Regularly update Docker images
- [ ] Monitor logs for suspicious activity
- [ ] Implement proper backup strategy

### HTTPS Configuration

1. **Obtain SSL certificates** (e.g., from Let's Encrypt)
2. **Place certificates** in the `certs/` directory:
   - `fullchain.pem` - Full certificate chain
   - `privkey.pem` - Private key
3. **Uncomment HTTPS configuration** in `config/nginx.conf`
4. **Restart Nginx**:
   ```bash
   docker-compose restart nginx
   ```

## 🚨 Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Find and kill the process using the port
sudo lsof -i :8000
kill -9 <PID>
```

#### 2. Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps

# Check PostgreSQL logs
docker-compose logs postgres

# Test database connection
docker-compose exec postgres psql -U nir_user -d nir_mistral -c "SELECT 1;"
```

#### 3. Migration Errors

```bash
# Reset migrations (be careful!)
find django_project -name "*.pyc" -delete
find django_project -name "__pycache__" -type d -exec rm -r {} + 2>/dev/null
rm -rf django_project/*/migrations/0*.py

# Recreate migrations
docker-compose exec django_app python django_project/manage.py makemigrations
docker-compose exec django_app python django_project/manage.py migrate
```

#### 4. Missing Dependencies

```bash
# Install missing Python packages
docker-compose exec django_app pip install missing-package

# Rebuild container with updated requirements
docker-compose build --no-cache django_app
```

#### 5. Permission Issues

```bash
# Fix directory permissions
sudo chown -R $USER:$USER .
chmod -R 755 .
```

### Debugging Tools

```bash
# Enter a running container
docker-compose exec web bash

# Check container resource usage
docker stats

# Check disk usage
docker system df

# Clean up unused containers, networks, and images
docker system prune
```

## 📈 Performance Optimization

### Database Optimization

```bash
# Create indexes for frequently queried fields
# Add to your models:
# class YourModel(models.Model):
#     field = models.CharField(max_length=100, db_index=True)

# Run VACUUM and ANALYZE
docker-compose exec postgres vacuumdb --analyze -U nir_user nir_mistral
```

### Django Optimization

```bash
# Enable caching in settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Use cache in views
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Cache for 15 minutes
def your_view(request):
    # Your view logic
```

### Docker Optimization

```bash
# Use smaller base images
# FROM python:3.10-slim instead of python:3.10

# Multi-stage builds (already implemented in Dockerfile.prod)

# Clean up unused images
docker image prune -a

# Limit container resources
docker-compose up -d --scale celery_worker=2
```

## 🔄 Update and Maintenance

### Updating Docker Images

```bash
# Pull latest images
docker-compose pull

# Rebuild containers
docker-compose up -d --build

# Update specific service
# 1. Update the image version in docker-compose.yml
# 2. docker-compose pull service_name
# 3. docker-compose up -d service_name
```

### Regular Maintenance Tasks

```bash
# Backup databases
docker-compose exec postgres pg_dump -U nir_user nir_mistral > backup_$(date +%Y%m%d).sql

# Clean up old backups
find . -name "backup_*.sql" -mtime +30 -delete

# Update Python dependencies
pip freeze > requirements.txt

# Check for security vulnerabilities
# docker scan (requires Docker Desktop)
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Docker Documentation](https://docs.djangoproject.com/en/stable/howto/deployment/docker/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Weaviate Docker Image](https://hub.docker.com/r/semitechnologies/weaviate)
- [Ollama Documentation](https://github.com/jmorganca/ollama)
- [Flower Framework](https://flower.dev/)

## 🎯 Next Steps

After setting up the Docker infrastructure, you can:

1. **Test the application**: Access http://localhost:8000 and verify all features work
2. **Set up CI/CD**: Configure automated testing and deployment
3. **Configure monitoring**: Set up alerts and dashboards in Grafana
4. **Implement backups**: Set up regular database backups
5. **Scale services**: Add more Celery workers for heavy workloads
6. **Enable HTTPS**: Configure SSL certificates for production

## 📞 Support

For issues or questions:

1. Check the logs: `docker-compose logs -f`
2. Review this documentation
3. Check the main NIR_MISTRAL documentation
4. Consult the Docker and service-specific documentation

---

**Last Updated**: 2026-08-10
**Version**: 1.0.0