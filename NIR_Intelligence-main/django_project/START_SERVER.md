# NIR_Mistral Django Server - Quick Start Guide

## 🚀 Start Your Server in 30 Seconds

### **✅ Method 1: Simple Start (Recommended)**

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
./start.sh
```

**This will:**
- Use the virtual environment
- Start Django server on port 8000
- Display access information

### **✅ Method 2: Full Setup (First Time Only)**

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
./start_server_venv.sh
```

**This will:**
- Create virtual environment (if needed)
- Install all dependencies (if needed)
- Run database migrations
- Start Django server
- Display access information

### **✅ Method 3: Manual Startup**

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
source venv/bin/activate  # Activate virtual environment
python manage.py runserver 0.0.0.0:8000  # Start server
```

---

## 🌐 Access Points

Once the server is running, access these URLs:

| URL | Description | Authentication |
|-----|-------------|----------------|
| `http://localhost:8000/` | **Main Dashboard** - Overview, statistics, quick actions | ❌ None |
| `http://localhost:8000/admin/` | **Admin Panel** - User management, data administration | ✅ Required |
| `http://localhost:8000/agents/` | **Agents Page** - Browse and manage NIR analysis agents | ❌ None |
| `http://localhost:8000/spectra/` | **Spectra Management** - Upload, view, manage spectra | ❌ None |
| `http://localhost:8000/analysis/` | **Analysis Tools** - Run analysis jobs | ❌ None |
| `http://localhost:8000/jobs/` | **Jobs Management** - View and manage analysis jobs | ❌ None |
| `http://localhost:8000/settings/` | **Settings** - Configure application settings | ❌ None |
| `http://localhost:8000/documentation/` | **Documentation** - Complete system documentation | ❌ None |

---

## 🔐 Login Credentials

- **Username**: `admin`
- **Password**: `admin123`
- **Email**: `admin@nir-mistral.test`

## ⚠️ Resolving 401 Unauthorized Error

If you're getting a **401 Unauthorized** error, it means you need to authenticate with a JWT token.

### **Quick Fix:**

1. **Get a token first:**
   ```bash
   curl -X POST http://localhost:8000/api/token/ \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "admin123"}'
   ```

2. **Use the token in your requests:**
   ```bash
   curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     http://localhost:8000/api/agents/
   ```

### **Public Endpoints (No Token Required):**
- `POST /api/token/` - Get JWT token
- `POST /api/token/refresh/` - Refresh JWT token  
- `GET /api/health/` - Health check
- `GET /api/nir-test/info/` - NIR_TEST environment info
- `GET /api/nir-test/files/` - List test data files
- `GET /api/nir-test/report/` - Get test report
- `POST /api/users/register/` - User registration

### **Protected Endpoints (Require Token):**
All other `/api/*` endpoints require a valid JWT token in the `Authorization: Bearer <token>` header.

📖 **See AUTHENTICATION_GUIDE.md for complete authentication documentation**

---

## 🔌 API Endpoints

### **Authentication**

```bash
# Get JWT Token
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Response: {"access": "your_token_here", "refresh": "refresh_token_here"}
```

### **NIR_TEST Environment**

```bash
# Get environment info
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/nir-test/info/

# Run complete demonstration
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/nir-test/demo/

# Run specific test (load_data, analyze, validate, report)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/nir-test/run/load_data/

# Get test data files
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/nir-test/files/

# Get latest test report
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/nir-test/report/

# Setup test environment
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/nir-test/setup/

# Clean test environment
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/nir-test/clean/
```

### **Agents API**

```bash
# List all agents
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/agents/

# Get agent details
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/agents/agent_name/

# Execute agent
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/agents/agent_name/execute/
```

### **Spectra API**

```bash
# List all spectra
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/spectra/

# Upload spectrum
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@spectrum.txt" \
  http://localhost:8000/api/spectra/

# Get spectrum details
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/spectra/spectrum_id/
```

---

## 🧪 NIR_TEST Environment

### **Command Line Interface**

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/NIR_TEST

# Get environment info
python run_test_environment.py info

# Run complete demonstration
python run_test_environment.py run

# Run specific tests
python run_test_environment.py test load_data
python run_test_environment.py test analyze
python run_test_environment.py test validate
python run_test_environment.py test report

# Setup environment
python run_test_environment.py setup

# Clean environment
python run_test_environment.py clean
```

### **Expected Output**

```
============================================================
NIR TEST ENVIRONMENT - DEMONSTRATION SUMMARY
============================================================
Agent: NIR_Test_Agent v1.0.0
Test Date: 2026-08-03 14:30:00
Configuration: NIR_TEST

Loaded Spectra: 2
  - Wheat Flour (001): 902 data points
  - Corn Meal (002): 901 data points

Analysis Results:
  - Wheat Flour:
    Wavelength Range: 700-2500 nm
    Mean Absorbance: 1.072
    Peaks Found: 5
  - Corn Meal:
    Wavelength Range: 700-2500 nm
    Mean Absorbance: 1.219
    Peaks Found: 4

Quality Control:
  - Wheat Flour: PASS
  - Corn Meal: PASS

Demonstration completed successfully!
Detailed report saved to: output/test_report.txt
============================================================
```

---

## 🎨 HSWT Design System

The Django frontend uses a **professional design system** inspired by **HSWT.de**:

### **Color Palette**
- **Primary Green**: `#7ab929` (HSWT brand color)
- **Dark Green**: `#225933` (Complementary dark)
- **Success**: `#28a745`
- **Warning**: `#ffc107`
- **Danger**: `#dc3545`
- **Info**: `#17a2b8`

### **Component Classes**
- **Cards**: `c-card`, `c-card__header`, `c-card__body`, `c-card__footer`
- **Buttons**: `c-button`, `c-button--primary`, `c-button--secondary`, etc.
- **Tables**: `c-table`, `c-table--hover`, `c-table-responsive`
- **Forms**: `c-form-group`, `c-input`, `c-select`, `c-textarea`
- **Modals**: `c-modal`, `c-modal__dialog`, `c-modal__content`
- **Statistics**: `c-stat`, `c-stat__icon`, `c-stat__content`
- **Badges**: `c-badge`, `c-badge--success`, `c-badge--danger`

---

## 📋 Troubleshooting

### **🔴 "ModuleNotFoundError: No module named 'django'"**

**Solution**: Use the virtual environment Python

```bash
# Use the venv Python directly
venv/bin/python manage.py runserver 0.0.0.0:8000

# Or activate the venv first
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

### **🔴 Port Already in Use**

**Solution**: Kill the existing process or use a different port

```bash
# Find and kill process using port 8000
sudo lsof -i :8000
sudo kill -9 <PID>

# Or use a different port
./start.sh 8001
```

### **🔴 Database Errors**

**Solution**: Reset database and re-run migrations

```bash
rm -f db.sqlite3
venv/bin/python manage.py migrate
```

### **🔴 Static Files Not Loading**

**Solution**: Collect static files

```bash
venv/bin/python manage.py collectstatic
```

### **🔴 Login Issues**

**Solution**: Use the correct credentials or create a new superuser

```bash
# Use existing credentials
# Username: admin
# Password: admin123

# Or create a new superuser
venv/bin/python manage.py createsuperuser
```

---

## 🏗️ System Architecture

```
NIR_Mistral Framework
├── NIR_TEST/                          # Test Environment
│   ├── agents/                        # Test agents
│   │   └── nir_test_agent.py         # Main test agent
│   ├── data/raw/                     # Test data files
│   ├── run_test_environment.py      # CLI interface
│   └── output/test_report.txt        # Generated reports
│
├── django_project/                   # Django Frontend
│   ├── venv/                          # Virtual environment
│   ├── nir_web/                       # Django project
│   │   ├── settings.py               # Django settings
│   │   ├── urls.py                   # URL routing
│   │   └── wsgi.py                   # WSGI config
│   ├── core/                          # Core app
│   │   ├── models.py                 # Custom User model
│   │   └── signals.py                # Signal handlers
│   ├── api/                           # API app
│   │   ├── views.py                  # Original API views
│   │   └── nir_test_views.py         # NIR_TEST API views
│   ├── templates/                    # HTML templates
│   │   ├── base.html                 # Base template
│   │   ├── agents.html               # Agents page
│   │   ├── dashboard.html            # Dashboard
│   │   └── ...                       # Other pages
│   └── static/                        # Static files
│       └── css/                       # CSS files
│           ├── hswt-style.css        # HSWT Design System
│           └── style.css              # Additional styles
│
└── db.sqlite3                        # SQLite database
```

---

## 📚 Additional Resources

- **Full Documentation**: `/NIR_TEST/TEST_ENVIRONMENT_DOCUMENTATION.md`
- **Installation Guide**: `/docs/INSTALLATION_GUIDE.md`
- **Django Project Docs**: `/django_project/README.md`
- **HSWT Design System**: `/django_project/static/css/hswt-style.css`

---

## 🎯 Next Steps

1. **Start the server**: `./start.sh`
2. **Explore the web interface**: `http://localhost:8000/`
3. **Test the NIR_TEST environment**: Run demonstrations via web or CLI
4. **Extend functionality**: Add new agents, test data, or features
5. **Deploy to production**: Use Gunicorn, Nginx, PostgreSQL

---

## ✅ System Status: READY TO USE!

Your **NIR_Mistral DeveloperAgent Framework** is now **fully operational** with:

- ✅ **Django Frontend** - Professional web interface with HSWT design
- ✅ **NIR_TEST Environment** - Complete test suite with real NIR data
- ✅ **RESTful API** - Full programmatic access with JWT authentication
- ✅ **Data Analysis** - Spectral analysis, peak detection, quality control
- ✅ **User Management** - Admin panel with custom User model
- ✅ **Comprehensive Documentation** - Complete guides and examples

### **🚀 START YOUR SERVER NOW!**

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
./start.sh
```

**Then open your browser to: [http://localhost:8000/](http://localhost:8000/)** 🎉

---

*Last updated: 2026-08-03*
*NIR_Mistral DeveloperAgent Framework v1.0.0*