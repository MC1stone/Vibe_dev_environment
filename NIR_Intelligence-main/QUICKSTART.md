# 🚀 NIR Mistral Quick Start Guide

## Fastest Way to Start Your Colorful NIR Platform

---

## 🎯 **RECOMMENDED: Option 1 - Background Start**

**Best for:** Development, testing, normal use  
**Server runs in background, you can continue using terminal**

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral
./start_bg.sh 8001
```

**What happens:**
- ✅ Stops any existing servers
- ✅ Frees up port 8001
- ✅ Starts server in background
- ✅ Shows all access URLs
- ✅ Logs to `/tmp/nir_mistral_8001.log`

**Access your platform:**
- Dashboard: `http://localhost:8001/dashboard/`
- Agents: `http://localhost:8001/agents/`
- Spectra: `http://localhost:8001/spectra/`
- Analysis: `http://localhost:8001/analysis/`
- Jobs: `http://localhost:8001/jobs/`
- Admin: `http://localhost:8001/admin/`

---

## 🎯 **Option 2 - Foreground Start**

**Best for:** Debugging, seeing real-time logs  
**Server runs in foreground, press Ctrl+C to stop**

```bash
cd /home/martin/Development/vsCode_Environment/NIR_Mistral
./quickstart.sh 8001
```

**What happens:**
- ✅ Stops any existing servers
- ✅ Frees up port 8001
- ✅ Starts server in foreground
- ✅ Shows all access URLs
- ✅ You'll see Django logs in real-time

**To stop:** Press `Ctrl+C`

---

## 🎯 **Option 3 - Direct Command**

**For advanced users who want full control**

```bash
# Step 1: Stop existing servers
cd /home/martin/Development/vsCode_Environment/NIR_Mistral
./stop_nir_server.sh

# Step 2: Start new server
cd django_project
python manage.py runserver 0.0.0.0:8001
```

**To stop:** Press `Ctrl+C`

---

## 📋 **Quick Reference Card**

| Command | Purpose | Server Mode |
|---------|---------|-------------|
| `./start_bg.sh 8001` | Start in background | Background |
| `./quickstart.sh 8001` | Start with logs visible | Foreground |
| `./stop_nir_server.sh` | Stop all servers | - |
| `tail -f /tmp/nir_mistral_8001.log` | View logs | - |

---

## 🌐 **Access Points (After Starting)**

### Main Pages
| URL | Description | Colorful UI |
|-----|-------------|-------------|
| `/dashboard/` | Main dashboard with stats | ✅ **FULLY COLORFUL** |
| `/agents/` | AI agents management | ✅ **FULLY COLORFUL** |
| `/spectra/` | Spectral data management | ✅ **FULLY COLORFUL** |
| `/analysis/` | Spectral analysis interface | ✅ **FULLY COLORFUL** |
| `/jobs/` | Job monitoring | ✅ **FULLY COLORFUL** |
| `/admin/` | Django admin panel | Standard |

### API Endpoints
| URL | Description |
|-----|-------------|
| `/api/health/` | Health check |
| `/api/agents/` | List all agents |
| `/api/spectra/` | Spectral data API |
| `/api/jobs/` | Job management API |

---

## 🔧 **Troubleshooting**

### **Problem: Port already in use**
```bash
# Solution 1: Use a different port
./start_bg.sh 8002

# Solution 2: Free the port manually
./stop_nir_server.sh
./start_bg.sh 8001
```

### **Problem: Server won't start**
```bash
# Check what's wrong
cd django_project
tail -20 /tmp/nir_mistral_8001.log

# Or run system check
python manage.py check
```

### **Problem: CSS not loading**
```bash
# Collect static files
python manage.py collectstatic

# Verify file exists
ls -la static/css/nir-colorful.css
```

### **Problem: Templates not found**
```bash
# Check template directory
ls -la django_project/templates/

# Verify templates have {% load static %}
grep -l "load static" django_project/templates/*.html
```

---

## 🎨 **What You Get with the Colorful UI**

### Dashboard Features
- **6 Statistics Cards** with colorful icons and animations
- **4 Quick Action Cards** for main workflows
- **Recent Activity Feed** with color-coded status
- **System Status Monitor** with pulse animations
- **NIR Wavelength Range** visualization (700-2500 nm)
- **Hero Section** with gradient background

### UI/UX Features
- **Glass-morphism effects** on all cards
- **Vibrant color palette** (7 NIR-specific colors)
- **Smooth animations** on page load and hover
- **Responsive design** for all screen sizes
- **Professional styling** with depth and shadows

### Color Palette
- **HSWT Green**: `#7ab929` (Primary)
- **NIR Purple**: `#8b5cf6` (Spectral)
- **NIR Blue**: `#3b82f6` (Data)
- **NIR Cyan**: `#06b6d4` (Info)
- **NIR Emerald**: `#10b981` (Success)
- **NIR Orange**: `#f59e0b` (Warning)
- **NIR Red**: `#ef4444` (Error)

---

## 📝 **Server Management Commands**

### Start Server
```bash
# Background mode (recommended)
./start_bg.sh [port]

# Foreground mode
./quickstart.sh [port]

# Direct command
cd django_project && python manage.py runserver 0.0.0.0:[port]
```

### Stop Server
```bash
# Stop all Django servers
./stop_nir_server.sh

# Manual stop
pkill -f "manage.py runserver"
```

### Check Status
```bash
# Check running processes
ps aux | grep "manage.py runserver" | grep -v grep

# Test if server is responding
curl http://localhost:8001/api/health/

# Check if colorful CSS is loading
curl http://localhost:8001/dashboard/ | grep "nir-colorful"
```

### View Logs
```bash
# View server logs
tail -f /tmp/nir_mistral_8001.log

# View Django system check
cd django_project && python manage.py check
```

---

## 🎯 **Common Ports to Try**

| Port | Status | Notes |
|------|--------|-------|
| 8000 | Often in use | Default Django port |
| 8001 | Recommended | Usually available |
| 8002 | Alternative | Good backup |
| 8080 | Alternative | Common development port |
| 8888 | Alternative | Another common port |

---

## ✅ **Quick Verification Checklist**

- [ ] Server started without errors
- [ ] Can access `http://localhost:8001/dashboard/`
- [ ] Colorful UI is visible (not plain text)
- [ ] All navigation links work
- [ ] API endpoints respond (`/api/health/`)
- [ ] Can see statistics cards with colors
- [ ] Hover effects work on buttons and cards

---

## 🚀 **You're Ready!**

### **Recommended Workflow:**
1. **Start server**: `./start_bg.sh 8001`
2. **Open browser**: `http://localhost:8001/dashboard/`
3. **Explore**: Try all the colorful pages
4. **Stop when done**: `./stop_nir_server.sh`

### **For Development:**
1. **Start server**: `./quickstart.sh 8001`
2. **Watch logs**: See real-time Django output
3. **Stop with**: `Ctrl+C`

---

## 📞 **Need Help?**

### Check These Files:
- **UI/UX Design Guide**: `UI_UX_DESIGN_GUIDE.md`
- **Server Update Summary**: `SERVER_UPDATE_SUMMARY.md`
- **Installation Guide**: `INSTALLATION_COMPLETE.md`

### Common Issues:
- **Port conflicts**: Try different port numbers
- **Static files**: Run `python manage.py collectstatic`
- **Templates**: Ensure `{% load static %}` is in all templates
- **Dependencies**: Check `requirements.txt` is installed

---

## 🎉 **Enjoy Your Colorful NIR Mistral Platform!**

Your platform is now ready with:
- ✅ **Full Django web application**
- ✅ **4 specialized NIR agents**
- ✅ **CrewAI integration**
- ✅ **Federated learning**
- ✅ **REST API**
- ✅ **Colorful, modern UI/UX**
- ✅ **Professional glass-morphism design**
- ✅ **Smooth animations**
- ✅ **Fully responsive**

**Access now at: http://localhost:8001/dashboard/** 🚀✨