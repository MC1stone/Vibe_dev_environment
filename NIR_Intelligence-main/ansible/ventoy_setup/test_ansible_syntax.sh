#!/bin/bash

# Test script to verify Ansible YAML syntax for Ventoy setup

echo "Testing Ansible YAML syntax for Ventoy setup..."
echo "================================================"

# Test all YAML files
YAML_FILES=(
    "site.yml"
    "roles/system_preparation/tasks/main.yml"
    "roles/system_preparation/handlers/main.yml"
    "roles/django_server/tasks/main.yml"
    "roles/django_server/handlers/main.yml"
    "roles/port_agent/tasks/main.yml"
    "roles/port_agent/handlers/main.yml"
    "roles/ventoy_config/tasks/main.yml"
    "roles/ventoy_config/handlers/main.yml"
)

PASSED=0
FAILED=0

for file in "${YAML_FILES[@]}"; do
    if [ -f "$file" ]; then
        if python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            echo "✅ $file : YAML syntax OK"
            ((PASSED++))
        else
            echo "❌ $file : YAML syntax ERROR"
            ((FAILED++))
        fi
    else
        echo "⚠️  $file : File not found"
        ((FAILED++))
    fi
done

echo ""
echo "================================================"
echo "Results: $PASSED passed, $FAILED failed"

if [ $FAILED -eq 0 ]; then
    echo "🎉 All YAML files are syntactically valid!"
    exit 0
else
    echo "❌ Some YAML files have syntax errors"
    exit 1
fi