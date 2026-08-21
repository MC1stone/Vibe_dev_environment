Ma#!/bin/bash

# Quarto 1.10.184 Specific Installation Script

set -e

echo "Installing Quarto CLI version 1.10.184..."

# Download the specific version
wget -O quarto.deb "https://github.com/quarto-dev/quarto-cli/releases/download/v1.10.184/quarto-1.10.184-linux-amd64.deb"

# Install
sudo dpkg -i quarto.deb
rm quarto.deb

# Verify
installed_version=$(quarto --version 2>/dev/null | head -n1 | cut -d' ' -f2)
if [ "$installed_version" = "1.10.184" ]; then
    echo "✅ Quarto 1.10.184 installed successfully"
else
    echo "❌ Installation failed. Got version: $installed_version"
    exit 1
fi
