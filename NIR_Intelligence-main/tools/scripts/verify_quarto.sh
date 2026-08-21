#!/bin/bash

# Quarto Verification Script

echo "=== Quarto Verification ==="

# Check installation
if ! command -v quarto &> /dev/null; then
    echo "❌ Quarto is not installed"
    exit 1
fi

# Get version
version=$(quarto --version 2>/dev/null | head -n1 | cut -d' ' -f2)
echo "Installed version: $version"

# Check against known versions
known_versions=("1.3.450" "1.3.420" "1.3.395" "1.2.376")

if printf '%s\n' "${known_versions[@]}" | grep -q "^$version$"; then
    echo "✅ Version $version is in known stable versions"
else
    echo "⚠️  Version $version not in known stable versions"
fi

# Test basic functionality
echo "Testing basic functionality..."
if quarto check &> /dev/null; then
    echo "✅ Quarto check passed"
else
    echo "❌ Quarto check failed"
fi

# Test render capability
echo "Testing render capability..."
temp_file=$(mktemp)
echo "# Test" > "$temp_file"
if quarto render "$temp_file" -o /dev/null &> /dev/null; then
    echo "✅ Render test passed"
    rm "$temp_file"
else
    echo "❌ Render test failed"
    rm "$temp_file"
fi

echo "Verification complete"
