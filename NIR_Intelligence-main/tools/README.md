# Tools Directory

This directory manages external tools and dependencies required by the NIR Intelligence Platform.

## Structure

- `quarto/` - Quarto CLI installations and management
- `versions/` - Version tracking and changelogs
- `scripts/` - Management scripts for tools
- `docs/` - Documentation for each tool

## Version Control

Each tool has a version file tracking:
- Current installed version
- Available versions
- Compatibility notes
- Update impact assessment

## Quarto CLI Management

### Current Status
- Latest stable version: 1.3.450 (as of 2024)
- Installation script: `tools/scripts/install_quarto.sh`
- Verification script: `tools/scripts/verify_quarto.sh`

### Usage

```bash
# Install latest stable
./tools/scripts/install_quarto.sh install

# Install specific version
./tools/scripts/install_quarto.sh install 1.3.450

# Check installed version
./tools/scripts/install_quarto.sh check

# Find latest version
./tools/scripts/install_quarto.sh latest

# Verify installation
./tools/scripts/verify_quarto.sh
```

### Version History

Check `tools/versions/quarto.txt` for:
- Currently installed version
- Available stable versions
- Compatibility notes
- Update impact assessments

### Integration with NIR Platform

The Quarto agent uses the installed version for:
- Report generation (`quarto render`)
- Documentation creation
- Visualization output

Ensure the version is compatible with your NIR platform version.
