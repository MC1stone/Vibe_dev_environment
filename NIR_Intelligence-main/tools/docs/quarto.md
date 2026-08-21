# Quarto CLI Management

## Installation

```bash
./tools/scripts/install_quarto.sh [version]
```

## Version Tracking

All versions are tracked in `tools/versions/quarto.txt` with:
- Current installed version
- Available versions
- Compatibility matrix
- Update impact assessment

## Usage in NIR Platform

Quarto is used by the `quarto_agent` for:
- Report generation
- Documentation creation
- Visualization rendering

## Update Procedure

1. Check current version: `quarto --version`
2. Review update impact in version file
3. Run installation script with desired version
4. Test quarto_agent functionality
5. Update version tracking file
