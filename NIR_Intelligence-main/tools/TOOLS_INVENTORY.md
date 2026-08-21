# Tools Inventory

## Current Tools

| Tool | Purpose | Current Version | Status |
|------|---------|-----------------|--------|
| Quarto | Documentation/Reporting | Check with `quarto --version` | Required |

## Installation Methods

1. **Automatic**: `./tools/scripts/manage_tools.sh install [tool] [version]`
2. **Manual**: Follow tool-specific instructions in `docs/`

## Version Control

Each tool has:
- Version tracking file in `versions/`
- Installation scripts in `scripts/`
- Documentation in `docs/`
- Compatibility notes

## Update Policy

1. Test updates in development environment first
2. Review impact assessment in version file
3. Update version tracking after successful install
4. Document any breaking changes
