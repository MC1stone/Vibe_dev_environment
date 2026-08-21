# NIR_Mistral DeveloperAgent Framework - Django Web Interface

A comprehensive Django-based web interface for the NIR_Mistral DeveloperAgent Framework, providing an easy-to-use UI for NIR spectroscopy analysis, agent management, and data visualization.

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Features](#-features)
3. [Installation](#-installation)
4. [Project Structure](#-project-structure)
5. [Configuration](#-configuration)
6. [Usage](#-usage)
7. [API Documentation](#-api-documentation)
8. [Integration with NIR_TEST Environment](#-integration-with-nir_test-environment)
9. [Deployment](#-deployment)
10. [Troubleshooting](#-troubleshooting)
11. [Contributing](#-contributing)
12. [License](#-license)

---

## 🎯 Overview

The NIR_Mistral Django Web Interface provides a modern, responsive web application for managing and analyzing NIR spectroscopy data using the NIR_Mistral DeveloperAgent Framework. The interface allows users to:

- Upload, view, and manage NIR spectra
- Run analysis using various framework agents
- Monitor analysis jobs and results
- Manage user profiles and preferences
- Access comprehensive documentation

The application is built with Django 4.2+, Bootstrap 5, and modern JavaScript libraries for an optimal user experience.

---

## ✨ Features

### Core Features
- **User Management**: User registration, authentication, and profile management
- **Spectra Management**: Upload, view, edit, and delete NIR spectroscopy data
- **Agent Management**: View available agents, their capabilities, and execute analysis
- **Job Management**: Create, monitor, and manage analysis jobs
- **Analysis Tools**: Multiple analysis types (peak detection, quality control, statistical analysis)
- **Data Visualization**: Interactive charts and graphs for spectrum visualization

### Advanced Features
- **JWT Authentication**: Secure API authentication with JSON Web Tokens
- **Real-time Updates**: Auto-refresh for active jobs and system status
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Comprehensive API**: RESTful API for programmatic access
- **Test Environment Integration**: Full integration with NIR_TEST environment

### User Interface Components
- **Dashboard**: Overview of system status, recent activity, and quick access
- **Spectra Page**: Complete spectra management with filtering and search
- **Analysis Page**: Run and monitor analysis jobs with various methods
- **Jobs Page**: View and manage all analysis jobs
- **Agents Page**: Browse and execute available agents
- **Settings Page**: Configure user preferences and system settings
- **Documentation Page**: Comprehensive documentation with examples

---

## 🚀 Installation

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- Node.js (optional, for frontend development)
- PostgreSQL or SQLite (for database)
- Modern web browser

### Quick Installation

1. **Clone the repository** (if not already cloned):
   ```bash
   git clone https://github.com/martin/Development/vsCode_Environment/NIR_Mistral.git
   cd NIR_Mistral/django_project
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup database**:
   ```bash
   python manage.py migrate
   ```

5. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```

6. **Start development server**:
   ```bash
   python manage.py runserver
   ```

7. **Access the application**:
   Open your browser and navigate to: `http://localhost:8000`

### Production Installation

For production deployments:

1. **Install additional dependencies**:
   ```bash
   pip install gunicorn psycopg2-binary
   ```

2. **Configure database** (PostgreSQL recommended):
   Update `nir_web/settings.py` with your database configuration:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'nir_mistral',
           'USER': 'nir_user',
           'PASSWORD': 'your_password',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```

3. **Collect static files**:
   ```bash
   python manage.py collectstatic
   ```

4. **Run with Gunicorn**:
   ```bash
   gunicorn nir_web.wsgi:application --bind 0.0.0.0:8000
   ```

---

## 🗂️ Project Structure

```
django_project/
├── manage.py                 # Django management script
├── nir_web/                 # Main Django project directory
│   ├── __init__.py
│   ├── settings.py           # Django settings
│   ├── urls.py              # URL routing
│   ├── wsgi.py              # WSGI configuration
│   └── asgi.py              # ASGI configuration
│
├── core/                    # Core application
│   ├── migrations/          # Database migrations
│   ├── __init__.py
│   ├── admin.py             # Admin interface configuration
│   ├── apps.py              # App configuration
│   ├── models.py            # Data models
│   ├── serializers.py       # API serializers
│   ├── views.py             # API views
│   └── urls.py              # App URL routing
│
├── api/                     # API application
│   ├── __init__.py
│   ├── serializers.py       # API serializers
│   ├── views.py             # API views
│   └── urls.py              # API URL routing
│
├── visualization/           # Visualization application
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   └── urls.py
│
├── templates/               # HTML templates
│   ├── base.html            # Base template
│   ├── dashboard.html       # Dashboard page
│   ├── agents.html          # Agents management page
│   ├── spectra.html         # Spectra management page
│   ├── analysis.html        # Analysis page
│   ├── jobs.html            # Jobs management page
│   ├── settings.html        # Settings page
│   └── documentation.html   # Documentation page
│
├── static/                  # Static files
│   ├── css/
│   │   └── style.css        # Custom CSS styles
│   ├── js/
│   │   └── main.js          # Main JavaScript file
│   └── images/              # Image assets
│
├── media/                   # Uploaded media files
│
├── scripts/                 # Utility scripts
│   └── setup_test_environment.py  # Test environment setup script
│
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root for environment-specific configuration:

```bash
# Database
DB_NAME=nir_mistral
DB_USER=nir_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# JWT Authentication
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# File Upload
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_FILE_TYPES=.txt,.csv,.json

# NIR_TEST Environment
NIR_TEST_PATH=/path/to/NIR_TEST
NIR_TEST_ENVIRONMENT=True
```

### Django Settings

Key settings in `nir_web/settings.py`:

- **Database Configuration**: Configure your database connection
- **Static Files**: Configure static and media file paths
- **Authentication**: JWT authentication settings
- **CORS**: Cross-Origin Resource Sharing settings
- **Logging**: Configure logging levels and handlers
- **Email**: SMTP email configuration for notifications

---

## 🎯 Usage

### Starting the Application

1. **Development Server**:
   ```bash
   python manage.py runserver
   ```
   Access at: `http://localhost:8000`

2. **Production Server** (using Gunicorn):
   ```bash
   gunicorn nir_web.wsgi:application --bind 0.0.0.0:8000
   ```

3. **Production Server** (using uWSGI):
   ```bash
   uwsgi --http :8000 --module nir_web.wsgi
   ```

### Command Line Management

- **Create superuser**:
  ```bash
  python manage.py createsuperuser
  ```

- **Run migrations**:
  ```bash
  python manage.py migrate
  ```

- **Make migrations**:
  ```bash
  python manage.py makemigrations
  ```

- **Collect static files**:
  ```bash
  python manage.py collectstatic
  ```

- **Run tests**:
  ```bash
  python manage.py test
  ```

- **Shell access**:
  ```bash
  python manage.py shell
  ```

### Using the Web Interface

1. **Login**: Navigate to the login page and enter your credentials
2. **Dashboard**: View system overview and recent activity
3. **Spectra**: Upload and manage NIR spectroscopy data
4. **Analysis**: Run analysis jobs using available agents
5. **Jobs**: Monitor and manage analysis jobs
6. **Agents**: View and execute available agents
7. **Settings**: Configure user preferences and system settings
8. **Documentation**: Access comprehensive documentation

---

## 📡 API Documentation

### Authentication

The API uses JWT (JSON Web Token) authentication. To authenticate:

1. **Obtain Token**:
   ```bash
   POST /api/token/
   {
       "username": "your_username",
       "password": "your_password"
   }
   ```

2. **Use Token**: Include the token in the Authorization header:
   ```bash
   Authorization: Bearer <your-token>
   ```

3. **Refresh Token**:
   ```bash
   POST /api/token/refresh/
   {
       "refresh": "your-refresh-token"
   }
   ```

### API Endpoints

#### Users
- `POST /api/users/register/` - Register a new user
- `GET /api/users/profile/` - Get user profile
- `PUT /api/users/profile/` - Update user profile
- `POST /api/users/change_password/` - Change password
- `DELETE /api/users/account/` - Delete account

#### Agents
- `GET /api/agents/` - List all agents
- `GET /api/agents/{name}/` - Get agent details
- `POST /api/agents/{name}/execute/` - Execute an agent

#### Spectra
- `GET /api/spectra/` - List all spectra
- `POST /api/spectra/` - Upload a new spectrum
- `GET /api/spectra/{id}/` - Get spectrum details
- `PUT /api/spectra/{id}/` - Update spectrum
- `DELETE /api/spectra/{id}/` - Delete spectrum
- `POST /api/spectra/{id}/analyze/` - Analyze spectrum

#### Jobs
- `GET /api/jobs/` - List all jobs
- `POST /api/jobs/` - Create a new job
- `GET /api/jobs/{id}/` - Get job details
- `POST /api/jobs/{id}/cancel/` - Cancel a job
- `DELETE /api/jobs/{id}/` - Delete a job
- `POST /api/jobs/clear_history/` - Clear job history

#### System
- `GET /api/health/` - Health check
- `POST /api/system/check/` - Run system check
- `GET /api/system/check_updates/` - Check for updates

### Request/Response Examples

**Upload Spectrum**:
```bash
POST /api/spectra/
Content-Type: multipart/form-data
Authorization: Bearer <token>

Form Data:
- sample_name: "Wheat Flour"
- sample_id: "001"
- spectral_type: "absorbance"
- file: <file content>
- description: "High-quality wheat flour sample"
- metadata: '{"instrument": "NIR-1000", "temperature": 25}'
```

**Create Analysis Job**:
```bash
POST /api/jobs/
Content-Type: application/json
Authorization: Bearer <token>

{
    "name": "Peak Detection Analysis",
    "analysis_type": "peak_detection",
    "spectrum": "uuid-of-spectrum",
    "agent": "NIR_Test_Agent",
    "description": "Analyzing wheat flour spectrum",
    "parameters": {
        "method": "local_maxima",
        "threshold": 0.1,
        "min_peak_height": 0.05
    }
}
```

---

## 🔬 Integration with NIR_TEST Environment

The Django web interface is fully integrated with the NIR_TEST environment for demonstration and testing purposes.

### Setup Test Environment

Run the automated setup script to configure the test environment:

```bash
cd django_project
python scripts/setup_test_environment.py
```

This script will:
1. Setup the NIR_TEST environment with test data
2. Configure Django for test environment integration
3. Create test users with different permission levels
4. Register test agents with the framework
5. Load test spectra into the database
6. Verify the complete setup

### Test Users

After running the setup script, you can log in with these test users:

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Superuser |
| testuser | testuser123 | Regular User |
| researcher | researcher123 | Staff User |

### Test Data

The setup script creates test spectra:

1. **Wheat Flour (ID: 001)** - Absorbance spectrum
   - Wavelength range: 700-2500 nm
   - Data points: 901
   - Contains characteristic peaks at 840, 1040, 1200, 1420, 1900 nm

2. **Corn Meal (ID: 002)** - Reflectance spectrum
   - Wavelength range: 700-2500 nm
   - Data points: 901
   - Contains characteristic peaks at 840, 1040, 1440, 1900 nm

### Test Agents

The following test agents are registered:

1. **NIR_Test_Agent** - Comprehensive test agent for NIR analysis
2. **Peak_Detector** - Specialized agent for peak detection
3. **Quality_Validator** - Agent for data quality validation
4. **Statistical_Analyzer** - Agent for statistical analysis

### Running the Demonstration

To run the complete NIR_TEST demonstration:

1. Start the Django development server:
   ```bash
   python manage.py runserver
   ```

2. Access the web interface at `http://localhost:8000`

3. Log in with the admin user (admin/admin123)

4. Navigate to the **Spectra** page to view the test data

5. Go to the **Analysis** page to run analysis jobs

6. Check the **Jobs** page to monitor progress

7. View results in the **Analysis Results** modal

Alternatively, you can run the test agent directly:

```bash
cd ../NIR_TEST
python run_test_environment.py run
```

---

## 🚀 Deployment

### Development Deployment

For local development:

```bash
# Start development server
python manage.py runserver

# Access at: http://localhost:8000
```

### Production Deployment with Gunicorn + Nginx

1. **Install Nginx and Gunicorn**:
   ```bash
   sudo apt update
   sudo apt install nginx gunicorn
   ```

2. **Configure Gunicorn**:
   Create `/etc/systemd/system/gunicorn.service`:
   ```ini
   [Unit]
   Description=gunicorn daemon
   After=network.target

   [Service]
   User=your_user
   Group=www-data
   WorkingDirectory=/path/to/django_project
   ExecStart=/path/to/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/path/to/django_project.sock nir_web.wsgi:application

   [Install]
   WantedBy=multi-user.target
   ```

3. **Configure Nginx**:
   Create `/etc/nginx/sites-available/nir_mistral`:
   ```nginx
   server {
       listen 80;
       server_name your_domain.com;

       location = /favicon.ico { access_log off; log_not_found off; }
       location /static/ {
           root /path/to/django_project;
       }

       location /media/ {
           root /path/to/django_project;
       }

       location / {
           include proxy_params;
           proxy_pass http://unix:/path/to/django_project.sock;
       }
   }
   ```

4. **Start Services**:
   ```bash
   sudo systemctl start gunicorn
   sudo systemctl enable gunicorn
   sudo systemctl restart nginx
   ```

### Docker Deployment

1. **Build Docker image**:
   ```bash
   docker build -t nir-mistral-web .
   ```

2. **Run container**:
   ```bash
   docker run -d -p 8000:8000 --name nir-mistral-web nir-mistral-web
   ```

3. **With Docker Compose**:
   Create `docker-compose.yml`:
   ```yaml
   version: '3.8'

   services:
     web:
       build: .
       command: gunicorn nir_web.wsgi:application --bind 0.0.0.0:8000
       volumes:
         - .:/code
       ports:
         - "8000:8000"
       environment:
         - DJANGO_SETTINGS_MODULE=nir_web.settings.production
     
     db:
       image: postgres:15
       environment:
         - POSTGRES_DB=nir_mistral
         - POSTGRES_USER=nir_user
         - POSTGRES_PASSWORD=your_password
       volumes:
         - postgres_data:/var/lib/postgresql/data/

   volumes:
     postgres_data:
   ```

   Run with:
   ```bash
   docker-compose up -d
   ```

### Venty Stick Deployment

For deployment on Venty Stick devices:

1. **Use Ansible playbooks** from the main project:
   ```bash
   cd ../ansible
   ansible-playbook -i inventory/hosts.yml playbooks/setup_venty_stick.yml
   ```

2. **Manual deployment**:
   - Copy the Django project to the Venty Stick
   - Install dependencies
   - Configure database
   - Set up systemd service for automatic startup

---

## 🔧 Troubleshooting

### Common Issues

**1. Database connection errors**
- Check database credentials in `settings.py`
- Verify database server is running
- Test connection manually

**2. Static files not loading**
- Run `python manage.py collectstatic`
- Check `STATIC_ROOT` and `STATIC_URL` settings
- Verify Nginx configuration for static files

**3. Migration errors**
- Delete migration files and recreate:
  ```bash
  rm -rf */migrations/
  python manage.py makemigrations
  python manage.py migrate
  ```

**4. Authentication errors**
- Verify JWT secret key is consistent
- Check token expiration settings
- Test token endpoints with Postman or curl

**5. File upload errors**
- Check file size limits in settings
- Verify allowed file types
- Check file permissions on upload directory

**6. Agent execution errors**
- Verify agent module paths are correct
- Check agent dependencies are installed
- Test agent execution from command line

### Debug Mode

Enable debug mode in `settings.py`:
```python
DEBUG = True
```

This provides detailed error pages and debugging information.

### Logging

Check application logs:
```bash
# Django logs
python manage.py shell
import logging
logger = logging.getLogger(__name__)
logger.error("Test error message")

# Gunicorn logs
journalctl -u gunicorn -f

# Nginx logs
tail -f /var/log/nginx/error.log
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/your-feature`)
3. **Commit your changes** (`git commit -m 'Add some feature'`)
4. **Push to the branch** (`git push origin feature/your-feature`)
5. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 style guide for Python code
- Use descriptive commit messages
- Include tests for new features
- Update documentation for changes
- Keep changes focused and minimal

### Running Tests

```bash
# Run all tests
python manage.py test

# Run tests for specific app
python manage.py test core

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

---

## 🏁 Conclusion

The NIR_Mistral Django Web Interface provides a complete, user-friendly solution for managing and analyzing NIR spectroscopy data. With its comprehensive features, modern design, and full integration with the NIR_Mistral DeveloperAgent Framework, it offers everything needed for both development and production use.

**Key Benefits**:
- ✅ Easy-to-use web interface for NIR spectroscopy analysis
- ✅ Complete integration with NIR_TEST environment for demonstration
- ✅ Comprehensive API for programmatic access
- ✅ Modern, responsive design that works on all devices
- ✅ Full-featured user management and authentication
- ✅ Extensive documentation and examples

**Next Steps**:
1. [Install the framework](#-installation)
2. [Run the test environment setup](#-integration-with-nir_test-environment)
3. [Start the development server](#-usage)
4. [Explore the web interface](http://localhost:8000)

For more information, visit the [main project documentation](../docs/) or check out the [GitHub repository](https://github.com/martin/Development/vsCode_Environment/NIR_Mistral).