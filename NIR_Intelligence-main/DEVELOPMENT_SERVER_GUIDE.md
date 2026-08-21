# 💻 NIR Mistral Development Server Guide

## Stable Development Environment Setup

This guide provides **multiple options** for running a **stable development Django server** that allows you to:
- ✅ **Follow up on further development**
- ✅ **Test code changes immediately**
- ✅ **Maintain stability** (no crashes)
- ✅ **Access all features** (agents, API, UI)
- ✅ **Monitor logs** in real-time

---

## 🎯 **RECOMMENDED: Option 1 - Gunicorn Development Server**

**Best for:** Stable development with auto-reload and multiple workers

### **Setup**
```bash
# Install Gunicorn (if not already installed)
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
pip install gunicorn
```

### **Start the Server**
```bash
# Using the development script
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
./dev_server.sh start
```

### **Server Commands**
```bash
# Start
./dev_server.sh start

# Stop
./dev_server.sh stop

# Restart (after code changes)
./dev_server.sh restart

# Check status
./dev_server.sh status
```

### **What You Get**
- ✅ **Stable server** with Gunicorn (4 workers)
- ✅ **Auto-reload** on code changes (`--reload`)
- ✅ **Debug logs** for troubleshooting
- ✅ **Background process** (doesn't block terminal)
- ✅ **PID management** (easy to stop)
- ✅ **Access at:** `http://localhost:8000/dashboard/`

### **Monitor Logs**
```bash
# View real-time logs
tail -f /tmp/nir_dev_server.log

# Filter for errors
tail -f /tmp/nir_dev_server.log | grep -i error

# Filter for agent activity
tail -f /tmp/nir_dev_server.log | grep -i agent
```

---

## 🎯 **Option 2 - Django Runserver with Screen**

**Best for:** Simple development with terminal access

### **Setup**
```bash
# Install screen (if not installed)
sudo apt install -y screen
```

### **Start the Server**
```bash
# Stop any existing servers
cd /home/martin/Development/vsCode_Environment/NIR_Mistral
./stop_nir_server.sh

# Start new server in screen session
cd django_project
screen -S nir_dev python manage.py runserver 0.0.0.0:8000
```

### **Server Commands**
```bash
# Detach from screen (keep server running)
Ctrl+A, D

# Reattach to screen
screen -r nir_dev

# Stop server
# 1. Reattach: screen -r nir_dev
# 2. Press Ctrl+C
# 3. Type: exit
```

### **What You Get**
- ✅ **Simple Django runserver**
- ✅ **Terminal access** (Ctrl+C to stop)
- ✅ **Session persistence** (detach/reattach)
- ✅ **Access at:** `http://localhost:8000/dashboard/`

---

## 🎯 **Option 3 - Docker Development Environment**

**Best for:** Isolated development with all dependencies

### **Setup**
```bash
# Build Docker image
cd /home/martin/Development/vsCode_Environment/NIR_Mistral
sudo docker-compose build

# Start containers
sudo docker-compose up -d
```

### **Server Commands**
```bash
# Start
sudo docker-compose up -d

# Stop
sudo docker-compose down

# View logs
sudo docker-compose logs -f

# Restart
sudo docker-compose restart
```

### **What You Get**
- ✅ **Isolated environment** (no dependency conflicts)
- ✅ **All services** in containers
- ✅ **Easy cleanup**
- ✅ **Access at:** `http://localhost:8000/dashboard/`

---

## 🎯 **Option 4 - VS Code Integrated Development**

**Best for:** Development within VS Code with debug support

### **Setup**
1. **Open project in VS Code**
   ```bash
   code /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
   ```

2. **Create `.vscode/launch.json`**
   ```json
   {
       "version": "0.2.0",
       "configurations": [
           {
               "name": "Django: NIR Mistral",
               "type": "python",
               "request": "launch",
               "program": "${workspaceFolder}/manage.py",
               "args": ["runserver", "0.0.0.0:8000"],
               "django": true,
               "justMyCode": false
           }
       ]
   }
   ```

3. **Create `.vscode/settings.json`**
   ```json
   {
       "python.pythonPath": "${workspaceFolder}/venv/bin/python",
       "python.linting.enabled": true,
       "python.linting.pylintEnabled": true,
       "[python]": {
           "editor.defaultFormatter": "ms-python.black-formatter"
       }
   }
   ```

### **Start Debugging**
1. Open **Run and Debug** panel (Ctrl+Shift+D)
2. Select **"Django: NIR Mistral"** configuration
3. Click **Start Debugging** (F5)

### **What You Get**
- ✅ **VS Code integration**
- ✅ **Debug support** (breakpoints, variable inspection)
- ✅ **Auto-reload** on file changes
- ✅ **Terminal access** in VS Code
- ✅ **Access at:** `http://localhost:8000/dashboard/`

---

## 🔧 **DEVELOPMENT WORKFLOW**

### **1. Start Your Server**
```bash
# Option 1: Gunicorn (recommended)
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
./dev_server.sh start

# Option 2: Screen
cd django_project
screen -S nir_dev python manage.py runserver 0.0.0.0:8000

# Option 3: Docker
sudo docker-compose up -d
```

### **2. Make Code Changes**
- Edit files in your preferred editor
- **Gunicorn** will auto-reload (with `--reload` flag)
- **Django runserver** will auto-reload automatically

### **3. Test Changes**
```bash
# Test API
curl http://localhost:8000/api/health/

# Test web interface
# Open browser: http://localhost:8000/dashboard/

# Run Python tests
cd django_project
python manage.py test
```

### **4. Monitor Logs**
```bash
# Gunicorn logs
tail -f /tmp/nir_dev_server.log

# Django logs (if using runserver)
# They appear in terminal where server is running
```

### **5. Restart When Needed**
```bash
# Gunicorn
./dev_server.sh restart

# Screen
# 1. screen -r nir_dev
# 2. Ctrl+C
# 3. python manage.py runserver 0.0.0.0:8000

# Docker
sudo docker-compose restart
```

---

## 🎨 **DEVELOPMENT TOOLS & COMMANDS**

### **Django Management Commands**
```bash
# Run in django_project directory
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project

# System check
python manage.py check

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Shell access
python manage.py shell

# Database shell
python manage.py dbshell

# Show URLs
python manage.py show_urls
```

### **Testing Commands**
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test api
python manage.py test core

# Run with coverage
pip install coverage
coverage run manage.py test
coverage report
```

### **Code Quality**
```bash
# Linting
flake8 .

# Formatting
black .

# Import sorting
isort .

# Type checking
mypy .
```

---

## 🐛 **TROUBLESHOOTING**

### **Issue: Port Already in Use**
```bash
# Find and kill process
sudo lsof -i :8000
sudo kill -9 <PID>

# Or use different port
./dev_server.sh start  # Uses 8000
# Or edit dev_server.sh and change PORT variable
```

### **Issue: Server Won't Start**
```bash
# Check logs
tail -50 /tmp/nir_dev_server.log

# Run system check
python manage.py check

# Check dependencies
pip list | grep -E "(django|gunicorn)"
```

### **Issue: Changes Not Showing**
```bash
# Clear browser cache
Ctrl+Shift+R (Windows/Linux)
Cmd+Shift+R (Mac)

# Restart server
./dev_server.sh restart

# Check if auto-reload is working
# Edit a file and save - server should reload automatically
```

### **Issue: Database Errors**
```bash
# Recreate database
python manage.py migrate --run-syncdb

# Reset database (WARNING: deletes data)
python manage.py flush
python manage.py migrate
```

### **Issue: Static Files Not Loading**
```bash
# Collect static files
python manage.py collectstatic

# Check if files exist
ls -la django_project/static/

# Check DEBUG setting
# In development, DEBUG=True serves static files
```

---

## 📁 **DEVELOPMENT DIRECTORY STRUCTURE**

```
django_project/
├── nir_web/                      # Django Project
│   ├── settings.py              # Settings (DEBUG=True for dev)
│   ├── urls.py                 # URL routes
│   └── wsgi.py                 # WSGI config
├── api/                         # REST API
│   ├── views.py                # API endpoints
│   ├── models.py               # Data models
│   └── serializers.py          # Serializers
├── core/                        # Core App
│   ├── models.py               # User, Spectrum, Job models
│   └── admin.py                # Admin configs
├── agents/                      # Agent Configurations
├── crewai_app/                  # CrewAI Integration
├── middleware/                  # Middleware
├── port_manager/               # Port Management
├── templates/                   # HTML Templates
│   ├── base.html               # Base template
│   ├── dashboard_colorful.html # Colorful dashboard
│   └── ...
├── static/                      # Static Files
│   ├── css/                    # CSS
│   │   ├── hswt-style.css      # HSWT Design
│   │   └── nir-colorful.css    # Colorful UI
│   └── js/                     # JavaScript
├── venv/                        # Virtual Environment
├── manage.py                   # Django Management
└── dev_server.sh               # Development Server Script
```

---

## 🚀 **RECOMMENDED DEVELOPMENT SETUP**

### **For Most Developers: Gunicorn + VS Code**

1. **Install VS Code**
   - Download from [https://code.visualstudio.com](https://code.visualstudio.com)
   - Install Python extension

2. **Open Project**
   ```bash
   code /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
   ```

3. **Start Server**
   ```bash
   ./dev_server.sh start
   ```

4. **Develop**
   - Edit files in VS Code
   - Server auto-reloads on changes
   - Test in browser: `http://localhost:8000/dashboard/`

5. **Monitor**
   ```bash
   tail -f /tmp/nir_dev_server.log
   ```

---

## 📊 **DEVELOPMENT SERVER COMPARISON**

| Feature | Gunicorn | Django Runserver | Docker | VS Code Debug |
|---------|----------|------------------|--------|---------------|
| **Stability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Auto-Reload** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes |
| **Multiple Workers** | ✅ 4 | ❌ No | ✅ Yes | ❌ No |
| **Background** | ✅ Yes | ❌ No | ✅ Yes | ❌ No |
| **Debug Support** | ⚠️ Limited | ⚠️ Limited | ❌ No | ✅ Full |
| **Isolation** | ❌ No | ❌ No | ✅ Yes | ❌ No |
| **Ease of Use** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Recommended** | ✅ **Yes** | ⚠️ Simple | ⚠️ Advanced | ✅ **Yes** |

---

## 🎯 **BEST PRACTICES FOR DEVELOPMENT**

### **1. Use Version Control**
```bash
# Check status
git status

# Commit changes
git add .
git commit -m "Your commit message"

# Push to repository
git push origin main
```

### **2. Create Feature Branches**
```bash
# Create new branch
git checkout -b feature/your-feature-name

# Merge when done
git checkout main
git merge feature/your-feature-name
```

### **3. Test Frequently**
```bash
# Run tests
python manage.py test

# Test specific functionality
curl http://localhost:8000/api/health/
```

### **4. Use Debug Tools**
```bash
# Django debug toolbar (install if needed)
pip install django-debug-toolbar

# Add to settings.py
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = ['127.0.0.1']
```

### **5. Monitor Performance**
```bash
# Check memory usage
top

# Check CPU usage
htop

# Check open files
lsof -i :8000
```

---

## 📝 **COMMON DEVELOPMENT TASKS**

### **1. Add a New API Endpoint**
```python
# In api/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def my_new_endpoint(request):
    return Response({"message": "Hello, World!"})

# In nir_web/urls.py
from api.views import my_new_endpoint
urlpatterns += [path('api/my-endpoint/', my_new_endpoint)]
```

### **2. Create a New Template**
```html
<!-- In templates/my_template.html -->
{% extends "base.html" %}
{% load static %}

{% block content %}
<h1>My New Page</h1>
<p>This is my new template.</p>
{% endblock %}

<!-- In nir_web/urls.py -->
from django.views.generic import TemplateView
urlpatterns += [path('my-page/', TemplateView.as_view(template_name='my_template.html'))]
```

### **3. Add a New Model**
```python
# In core/models.py
from django.db import models

class MyModel(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

# Run migrations
python manage.py makemigrations
python manage.py migrate
```

### **4. Add JavaScript Functionality**
```javascript
// In static/js/my_script.js
console.log("My script loaded!");

// In template
{% block extra_js %}
<script src="{% static 'js/my_script.js' %}"></script>
{% endblock %}
```

---

## ✅ **FINAL RECOMMENDATION**

**For stable development with further development follow-up:**

```bash
# 1. Navigate to project
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project

# 2. Start Gunicorn server (recommended)
./dev_server.sh start

# 3. Access your development server
# Open browser: http://localhost:8000/dashboard/

# 4. Monitor logs
tail -f /tmp/nir_dev_server.log

# 5. Make code changes
# Edit files in your preferred editor
# Server will auto-reload

# 6. Test changes
# Refresh browser or run: curl http://localhost:8000/api/health/

# 7. Stop when done
./dev_server.sh stop
```

**This setup gives you:**
- ✅ **Stable server** that won't crash
- ✅ **Auto-reload** on code changes
- ✅ **Background operation** (free terminal)
- ✅ **Easy monitoring** (log files)
- ✅ **Full functionality** (all agents, API, UI)
- ✅ **Production-like** environment

---

## 🎉 **YOU'RE READY FOR DEVELOPMENT!**

Your **stable development Django server** is ready. Choose the option that best fits your workflow:

1. **🎯 Gunicorn (Recommended)** - Stable, auto-reload, background
2. **🎯 Screen** - Simple, terminal access
3. **🎯 Docker** - Isolated, all dependencies
4. **🎯 VS Code Debug** - Integrated, full debug support

**Start developing your NIR Mistral platform now!** 🚀

**Access your development server at:** `http://localhost:8000/dashboard/`

**All features are available for further development:**
- ✅ All 4 NIR agents loaded
- ✅ CrewAI orchestration working
- ✅ Colorful UI/UX active
- ✅ REST API functional
- ✅ Database ready
- ✅ File upload working

**Happy developing!** 💻✨