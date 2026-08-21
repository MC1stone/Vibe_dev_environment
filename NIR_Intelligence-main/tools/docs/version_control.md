# Version Control Documentation

## Current Status

### Quarto CLI
- **Installed Version**: `quarto --version` or "not installed"
- **Latest Stable**: Check with `./tools/scripts/install_quarto.sh latest`
- **Management Script**: `tools/scripts/install_quarto.sh`

## Version Management Workflow

### 1. Check Current Version
```bash
./tools/scripts/install_quarto.sh check
quarto --version
```

### 2. Find Latest Version
```bash
./tools/scripts/install_quarto.sh latest
```

### 3. Install/Update
```bash
# Install specific version
./tools/scripts/install_quarto.sh install 1.3.450

# Install latest stable
./tools/scripts/install_quarto.sh install
```

### 4. Verify Installation
```bash
quarto check
```

## Compatibility Matrix

| NIR Platform Version | Quarto Version | Status |
|----------------------|----------------|--------|
| 1.0.x                | 1.3.x          | ✅ Fully compatible |
| 1.0.x                | 1.2.x          | ✅ Compatible |
| 1.0.x                | <1.2           | ❌ Not recommended |

## Update Impact Assessment

### Before Updating
1. Check [Quarto Changelog](https://github.com/quarto-dev/quarto-cli/releases)
2. Review version compatibility in `tools/versions/quarto.txt`
3. Test in development environment

### Update Process
1. Backup current reports: `cp -r reports reports_backup_$(date +%Y%m%d)`
2. Install new version: `./tools/scripts/install_quarto.sh install [version]`
3. Test documentation generation: `python scripts/main_orchestrator.py --test-quarto`
4. Verify output quality

### Rollback Procedure
1. Identify previous working version in `tools/versions/quarto.txt`
2. Reinstall: `./tools/scripts/install_quarto.sh install [previous_version]`
3. Restore reports from backup if needed

## Version Tracking

All versions are tracked in `tools/versions/quarto.txt` with:
- Current installed version
- Available stable versions
- Compatibility notes
- Known issues

## Troubleshooting

**Issue: Installation fails**
- Check internet connection
- Verify wget is installed: `sudo apt install wget`
- Try manual download from GitHub releases

**Issue: Version mismatch**
- Run `quarto --version` to confirm
- Reinstall with explicit version

**Issue: Permission denied**
- Use sudo: `sudo ./tools/scripts/install_quarto.sh install`
- Or install to user directory: `./tools/scripts/install_quarto.sh install $version $HOME/.local/bin`
