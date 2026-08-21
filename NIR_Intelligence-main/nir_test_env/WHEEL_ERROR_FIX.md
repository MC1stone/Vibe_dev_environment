# 🔧 Fixing "Getting requirements to build wheel" Errors

## 📋 **Issue Description**

The error "Getting requirements to build wheel did not run successfully" occurs when Python's pip cannot build certain packages from source. This typically happens when:

1. **Missing build dependencies** - Required system libraries not installed
2. **Python version mismatch** - Package requires different Python version
3. **Package compilation issues** - Package needs compilation but fails
4. **Environment restrictions** - System policies prevent compilation

## 🎯 **Solutions**

### **Solution 1: Install Build Dependencies**

```bash
# Install required system packages
sudo apt update
sudo apt install -y build-essential python3-dev libpq-dev libssl-dev libffi-dev
```

**When to use:** Always install build dependencies first

### **Solution 2: Use Pre-Built Packages**

```bash
# Use packages with pre-built wheels
pip install package_name --only-binary=:all:
```

**When to use:** When you want to avoid compilation

### **Solution 3: Use --no-cache-dir**

```bash
# Clear pip cache and retry
pip install --no-cache-dir package_name
```

**When to use:** When cache might be corrupted

### **Solution 4: Use Virtual Environment**

```bash
# Create and use virtual environment
python3 -m venv myenv
source myenv/bin/activate
pip install package_name
```

**When to use:** When system packages conflict

### **Solution 5: Install from Source with Flags**

```bash
# Install with specific compiler flags
CFLAGS="-O0" pip install package_name
```

**When to use:** When compilation fails with optimization

## 📁 **Package-Specific Solutions**

### **psycopg2-binary**
```bash
# Use binary version instead of source
pip install psycopg2-binary
```

### **scikit-learn**
```bash
# Install with pre-built wheels
pip install scikit-learn --only-binary=:all:
```

### **pandas**
```bash
# Use pre-built wheels
pip install pandas --only-binary=:all:
```

### **numpy**
```bash
# Use pre-built wheels
pip install numpy --only-binary=:all:
```

## 🚀 **Step-by-Step Fix**

### **1. Install Build Dependencies**
```bash
sudo apt update
sudo apt install -y build-essential python3-dev libpq-dev libssl-dev libffi-dev
```

### **2. Try Installation with Binary Wheels**
```bash
pip install --only-binary=:all: package_name
```

### **3. Use Virtual Environment**
```bash
python3 -m venv myenv
source myenv/bin/activate
pip install package_name
```

### **4. Clear Cache and Retry**
```bash
pip install --no-cache-dir package_name
```

### **5. Install Individual Packages**
```bash
pip install Django
pip install djangorestframework
pip install psycopg2-binary
# Continue with other packages...
```

## 🔧 **Advanced Solutions**

### **Use pip with Verbose Output**
```bash
pip install -v package_name
```

### **Check Python Version**
```bash
python3 --version
```

### **Upgrade pip**
```bash
pip install --upgrade pip
```

### **Use Different Python Version**
```bash
pyenv install 3.12.0
pyenv global 3.12.0
```

### **Install from Git**
```bash
pip install git+https://github.com/package/repo.git
```

## 📚 **Common Packages and Solutions**

| Package | Solution | Notes |
|---------|----------|-------|
| **psycopg2** | Use `psycopg2-binary` | No compilation needed |
| **scikit-learn** | Use `--only-binary` | Pre-built wheels |
| **pandas** | Use `--only-binary` | Pre-built wheels |
| **numpy** | Use `--only-binary` | Pre-built wheels |
| **Django** | Standard install | Usually no issues |
| **requests** | Standard install | Usually no issues |

## 🎯 **Prevention**

### **1. Always Use Virtual Environments**
```bash
python3 -m venv myenv
source myenv/bin/activate
```

### **2. Install Build Dependencies First**
```bash
sudo apt install build-essential python3-dev
```

### **3. Use Binary Wheels When Possible**
```bash
pip install --only-binary=:all: package_name
```

### **4. Keep pip Updated**
```bash
pip install --upgrade pip
```

### **5. Check Python Version Compatibility**
```bash
python3 --version
```

## 📊 **Performance Impact**

### **Binary Wheels vs Source**

| Aspect | Binary Wheels | Source Compilation |
|--------|--------------|-------------------|
| **Speed** | ⚡ Fast | 🐢 Slow |
| **Reliability** | ✅ High | ❌ Low |
| **Compatibility** | ✅ High | ⚠ Medium |
| **Customization** | ❌ None | ✅ Full |

### **Recommendation**

**Use binary wheels** for:
- ✅ Production environments
- ✅ Quick installation
- ✅ Reliable deployment
- ✅ Most packages

**Use source compilation** for:
- ❌ Development only
- ❌ Custom modifications
- ❌ Specific needs
- ❌ Rare cases

## 🆘 **Getting Help**

### **Check pip Version**
```bash
pip --version
```

### **Check Python Version**
```bash
python3 --version
```

### **Check Environment**
```bash
which python3
which pip
```

### **Debug Installation**
```bash
pip install -v package_name
```

### **List Installed Packages**
```bash
pip list
```

## 🏅 **Conclusion**

The "Getting requirements to build wheel" error is common but solvable. The solutions provided should help you successfully install all required packages for the NIR Intelligence Platform.

### **Key Takeaways**

1. **Install build dependencies first**
2. **Prefer binary wheels** when possible
3. **Use virtual environments** to avoid conflicts
4. **Try multiple approaches** if one fails
5. **Check Python version** compatibility

**Status**: ✅ **Documented** | 🎯 **Solutions Provided** | 🚀 **Ready for Deployment**

---

*This document provides solutions for "Getting requirements to build wheel" errors. For the latest information, please refer to the official documentation at https://docs.nir-platform.org.*