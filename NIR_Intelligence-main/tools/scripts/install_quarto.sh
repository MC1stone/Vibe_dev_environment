#!/bin/bash

# Enhanced Quarto Installation Script with Version Awareness

set -e

# Configuration
QUARTO_VERSION="${1:-latest}"
INSTALL_DIR="${2:-$HOME/.local/bin}"
VERSION_FILE="tools/versions/quarto.txt"

# Function to get latest version from GitHub
get_latest_version() {
    curl -s https://api.github.com/repos/quarto-dev/quarto-cli/releases/latest | \
    grep '"tag_name":' | \
    sed -E 's/.*"v([^"]+)".*/\1/'
}

# Check current version
check_current_version() {
    if command -v quarto &> /dev/null; then
        quarto --version 2>/dev/null | head -n1 | cut -d' ' -f2
    else
        echo "none"
    fi
}

# Main installation logic
install_quarto() {
    local version=$1

    echo "=== Quarto Installation ==="
    echo "Target version: $version"
    echo "Install directory: $INSTALL_DIR"

    # Check if already installed
    current=$(check_current_version)
    if [ "$current" = "$version" ]; then
        echo "✅ Quarto $version is already installed"
        return 0
    fi

    if [ "$current" != "none" ]; then
        echo "⚠️  Updating from $current to $version"
    else
        echo "📥 Installing Quarto $version"
    fi

    # Download appropriate version
    if [ "$version" = "latest" ]; then
        version=$(get_latest_version)
        echo "🔍 Latest version detected: $version"
    fi

    # Download and install
    echo "Downloading Quarto $version..."
    wget -O quarto.deb "https://github.com/quarto-dev/quarto-cli/releases/download/v$version/quarto-$version-linux-amd64.deb"

    echo "Installing..."
    sudo dpkg -i quarto.deb
    rm quarto.deb

    # Verify installation
    installed_version=$(check_current_version)
    if [ "$installed_version" = "$version" ]; then
        echo "✅ Quarto $version installed successfully"
        sed -i "s/CURRENT_VERSION:.*/CURRENT_VERSION: $version/" "$VERSION_FILE"
        return 0
    else
        echo "❌ Installation failed. Expected $version, got $installed_version"
        return 1
    fi
}

# Main execution
case $1 in
    install)
        install_quarto "${2:-latest}"
        ;;
    check)
        current=$(check_current_version)
        if [ "$current" = "none" ]; then
            echo "Quarto is not installed"
            exit 1
        else
            echo "Current Quarto version: $current"
        fi
        ;;
    latest)
        echo "Latest available version: $(get_latest_version)"
        ;;
    *)
        echo "Usage: $0 [install|check|latest] [version]"
        exit 1
        ;;
esac
