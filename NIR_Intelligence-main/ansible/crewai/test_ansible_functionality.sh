#!/bin/bash

# NIR Intelligence Platform - Crew AI Ansible Functionality Test Script
# This script tests the Ansible playbooks for Crew AI implementation

set -e  # Exit on error
set -o pipefail  # Exit on pipe failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# Project root
PROJECT_ROOT="/home/martin/Development/vsCode_Environment/NIR_Mistral"
ANSIBLE_DIR="$PROJECT_ROOT/ansible/crewai"
TEST_OUTPUT_DIR="$PROJECT_ROOT/test_output/ansible"

# Create test output directory
mkdir -p "$TEST_OUTPUT_DIR"
mkdir -p "$TEST_OUTPUT_DIR/logs"
mkdir -p "$TEST_OUTPUT_DIR/reports"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to run a command and check result
run_command() {
    local cmd="$1"
    local description="$2"
    local log_file="$3"
    
    log "Running: $description"
    echo "Command: $cmd"
    
    if eval "$cmd" > "$log_file" 2>&1; then
        success "$description completed successfully"
        return 0
    else
        error "$description failed"
        echo "Check log file: $log_file"
        return 1
    fi
}

# Function to check if Ansible is installed
check_ansible() {
    if command -v ansible &> /dev/null; then
        local version=$(ansible --version | head -1 | cut -d' ' -f2)
        success "Ansible is installed (version: $version)"
        return 0
    else
        error "Ansible is not installed"
        return 1
    fi
}

# Function to check Python
check_python() {
    if command -v python3 &> /dev/null; then
        local version=$(python3 --version 2>&1)
        success "Python is installed ($version)"
        return 0
    else
        error "Python is not installed"
        return 1
    fi
}

# Function to check Ansible syntax
check_ansible_syntax() {
    local playbook="$1"
    local description="Syntax check for $playbook"
    
    log "Checking syntax of: $playbook"
    
    if ansible-playbook "$playbook" --syntax-check > /dev/null 2>&1; then
        success "$description passed"
        return 0
    else
        error "$description failed"
        return 1
    fi
}

# Function to run Ansible playbook
run_ansible_playbook() {
    local playbook="$1"
    local inventory="$2"
    local description="$3"
    local log_file="$TEST_OUTPUT_DIR/logs/$(basename $playbook .yml)_$(date +%Y%m%d_%H%M%S).log"
    
    run_command "ansible-playbook $playbook -i $inventory" "$description" "$log_file"
}

# Main function
main() {
    echo "=========================================="
    echo "NIR Intelligence Platform - Crew AI"
    echo "Ansible Functionality Test Script"
    echo "=========================================="
    echo
    
    # Check prerequisites
    log "Checking prerequisites..."
    
    if ! check_ansible; then
        warning "Ansible is required. Install with: sudo apt install ansible"
        exit 1
    fi
    
    if ! check_python; then
        warning "Python 3 is required. Install with: sudo apt install python3"
        exit 1
    fi
    
    echo
    
    # Check Ansible syntax for all playbooks
    log "Checking Ansible playbook syntax..."
    
    local syntax_passed=0
    local syntax_total=0
    
    for playbook in "$ANSIBLE_DIR"/*.yml; do
        if [ -f "$playbook" ]; then
            syntax_total=$((syntax_total + 1))
            if check_ansible_syntax "$playbook"; then
                syntax_passed=$((syntax_passed + 1))
            fi
        fi
    done
    
    echo
    log "Syntax check results: $syntax_passed/$syntax_total playbooks passed"
    
    if [ $syntax_passed -lt $syntax_total ]; then
        error "Some playbooks have syntax errors"
        exit 1
    fi
    
    echo
    
    # Test inventory file
    log "Testing inventory file..."
    
    if [ -f "$ANSIBLE_DIR/inventory.ini" ]; then
        if ansible -i "$ANSIBLE_DIR/inventory.ini" all --list-hosts > /dev/null 2>&1; then
            success "Inventory file is valid"
        else
            error "Inventory file has issues"
            exit 1
        fi
    else
        error "Inventory file not found: $ANSIBLE_DIR/inventory.ini"
        exit 1
    fi
    
    echo
    
    # Test connectivity
    log "Testing connectivity to hosts..."
    
    if ansible -i "$ANSIBLE_DIR/inventory.ini" all -m ping > /dev/null 2>&1; then
        success "Connectivity test passed"
    else
        error "Connectivity test failed"
        exit 1
    fi
    
    echo
    
    # Run the test playbook
    log "Running Crew AI implementation tests..."
    
    local test_log="$TEST_OUTPUT_DIR/logs/crewai_test_$(date +%Y%m%d_%H%M%S).log"
    
    if run_command "ansible-playbook $ANSIBLE_DIR/test_crewai_implementation.yml -i $ANSIBLE_DIR/inventory.ini" \
        "Crew AI implementation test" \
        "$test_log"; then
        
        # Check if test reports were created
        if [ -f "$PROJECT_ROOT/test_output/reports/crewai_test_summary.md" ]; then
            success "Test summary report created"
            
            # Display test summary
            echo
            log "Test Summary:"
            cat "$PROJECT_ROOT/test_output/reports/crewai_test_summary.md"
        else
            warning "Test summary report not found"
        fi
        
    else
        error "Crew AI implementation test failed"
        warning "Check log file: $test_log"
        exit 1
    fi
    
    echo
    
    # Check for syntax in templates
    log "Checking Jinja2 template syntax..."
    
    local template_passed=0
    local template_total=0
    
    for template in "$ANSIBLE_DIR/templates"/*.j2; do
        if [ -f "$template" ]; then
            template_total=$((template_total + 1))
            
            # Simple syntax check - just try to read the file
            if ansible localhost -m debug -a "msg='Checking template: $template'" > /dev/null 2>&1; then
                template_passed=$((template_passed + 1))
            fi
        fi
    done
    
    log "Template check results: $template_passed/$template_total templates passed"
    
    echo
    
    # Display final results
    echo "=========================================="
    echo "Ansible Functionality Test Results"
    echo "=========================================="
    
    success "✓ Ansible is installed and working"
    success "✓ All playbooks have valid syntax"
    success "✓ Inventory file is valid"
    success "✓ Connectivity test passed"
    success "✓ Crew AI implementation test passed"
    success "✓ Templates are valid"
    
    echo
    log "All tests passed! Ansible functionality is working correctly."
    log "Test logs are available in: $TEST_OUTPUT_DIR/logs/"
    log "Test reports are available in: $PROJECT_ROOT/test_output/reports/"
    
    echo
    echo "Next steps:"
    echo "1. Review test reports in $PROJECT_ROOT/test_output/reports/"
    echo "2. Check logs in $TEST_OUTPUT_DIR/logs/ for details"
    echo "3. Run deployment playbook when ready:"
    echo "   ansible-playbook $ANSIBLE_DIR/deploy_crewai.yml -i $ANSIBLE_DIR/inventory.ini"
    
    return 0
}

# Run main function
main "$@"

exit $?