#!/bin/bash

# NIR_Mistral Complete Deployment Script
# This script provides a unified interface for deploying the NIR_Mistral framework
# on Ventoy sticks or any target system using Ansible

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ANSIBLE_DIR="$SCRIPT_DIR"
INVENTORY_FILE="$ANSIBLE_DIR/inventory.ini"
PLAYBOOK_FILE="$ANSIBLE_DIR/playbooks/deploy_complete.yml"

# Default values
TARGET_HOST="localhost"
DEPLOYMENT_TYPE="local"
ENVIRONMENT="production"
SKIP_VERIFICATION=false

# Functions
function print_banner() {
    echo -e "${BLUE}
============================================
    NIR_MISTRAL DEPLOYMENT SCRIPT
============================================
Version: 1.0.0
Project: NIR Intelligence Platform
Framework: DeveloperAgent v1.0.0
============================================${NC}"
}

function print_usage() {
    echo -e "${YELLOW}Usage: $0 [OPTIONS]${NC}"
    echo ""
    echo "Options:"
    echo "  -h, --help            Show this help message"
    echo "  -t, --target HOST     Target host for deployment (default: localhost)"
    echo "  -e, --environment ENV Environment type (development|production|staging)"
    echo "  -d, --deployment TYPE Deployment type (local|ventoy|remote)"
    echo "  -s, --skip-verification Skip health verification checks"
    echo "  -c, --check           Check deployment status only"
    echo "  -i, --install         Install Ansible and dependencies"
    echo "  -v, --verbose         Verbose output"
    echo ""
    echo "Examples:"
    echo "  $0 -t 192.168.1.100 -d ventoy -e production"
    echo "  $0 --target localhost --environment development"
    echo "  $0 --check"
    echo "  $0 --install"
}

function install_dependencies() {
    echo -e "${BLUE}Installing Ansible and dependencies...${NC}"
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}Warning: Some commands may require sudo privileges${NC}"
    fi
    
    # Install Ansible
    if command -v ansible &> /dev/null; then
        echo -e "${GREEN}Ansible is already installed: $(ansible --version | head -1)${NC}"
    else
        echo -e "${YELLOW}Installing Ansible...${NC}"
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y ansible python3-pip sshpass
        elif command -v yum &> /dev/null; then
            sudo yum install -y ansible python3-pip sshpass
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y ansible python3-pip sshpass
        else
            echo -e "${RED}Error: Unable to determine package manager${NC}"
            exit 1
        fi
    fi
    
    # Install Python dependencies for Ansible
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    pip3 install -r "$ANSIBLE_DIR/requirements.txt" 2>/dev/null || true
    
    # Install Ansible Galaxy collections
    echo -e "${YELLOW}Installing Ansible Galaxy collections...${NC}"
    ansible-galaxy install -r "$ANSIBLE_DIR/galaxy_requirements.yml" 2>/dev/null || true
    
    echo -e "${GREEN}Dependencies installed successfully!${NC}"
}

function check_ansible() {
    if ! command -v ansible &> /dev/null; then
        echo -e "${RED}Error: Ansible is not installed. Please run with -i or --install option.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Ansible version: $(ansible --version | head -1)${NC}"
}

function validate_inventory() {
    if [ ! -f "$INVENTORY_FILE" ]; then
        echo -e "${RED}Error: Inventory file not found: $INVENTORY_FILE${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Using inventory: $INVENTORY_FILE${NC}"
}

function validate_playbook() {
    if [ ! -f "$PLAYBOOK_FILE" ]; then
        echo -e "${RED}Error: Playbook file not found: $PLAYBOOK_FILE${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Using playbook: $PLAYBOOK_FILE${NC}"
}

function check_deployment() {
    echo -e "${BLUE}Checking deployment status...${NC}"
    
    # Test connectivity
    echo -e "${YELLOW}Testing connectivity to target hosts...${NC}"
    ansible -i "$INVENTORY_FILE" all -m ping
    
    # Check if services are running (if already deployed)
    echo -e "${YELLOW}Checking service status...${NC}"
    ansible -i "$INVENTORY_FILE" all -a "systemctl list-units --type=service | grep -E '(django|port_agent|weaviate|postgres)'" -b 2>/dev/null || true
    
    echo -e "${GREEN}Deployment check complete.${NC}"
}

function run_deployment() {
    echo -e "${BLUE}Starting NIR_Mistral deployment...${NC}"
    
    # Build Ansible command
    local ansible_cmd="ansible-playbook -i $INVENTORY_FILE $PLAYBOOK_FILE"
    
    # Add extra vars based on parameters
    if [ "$ENVIRONMENT" != "production" ]; then
        ansible_cmd+=" -e \"environment=$ENVIRONMENT\""
    fi
    
    if [ "$SKIP_VERIFICATION" = true ]; then
        ansible_cmd+=" -e \"skip_verification=true\""
    fi
    
    # Add deployment type specific variables
    case "$DEPLOYMENT_TYPE" in
        "ventoy")
            ansible_cmd+=" -e \"deployment_type=ventoy\""
            ;;
        "remote")
            ansible_cmd+=" -e \"deployment_type=remote\""
            ;;
        *)
            ansible_cmd+=" -e \"deployment_type=local\""
            ;;
    esac
    
    # Add verbose flag if requested
    if [ "$VERBOSE" = true ]; then
        ansible_cmd+=" -v"
    fi
    
    echo -e "${YELLOW}Executing: $ansible_cmd${NC}"
    echo -e "${BLUE}This may take 10-30 minutes depending on your system...${NC}"
    
    # Run the playbook
    eval $ansible_cmd
    
    echo -e "${GREEN}Deployment completed successfully!${NC}"
}

function main() {
    print_banner
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_usage
                exit 0
                ;;
            -t|--target)
                TARGET_HOST="$2"
                shift 2
                ;;
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -d|--deployment)
                DEPLOYMENT_TYPE="$2"
                shift 2
                ;;
            -s|--skip-verification)
                SKIP_VERIFICATION=true
                shift
                ;;
            -c|--check)
                check_deployment
                exit 0
                ;;
            -i|--install)
                install_dependencies
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                print_usage
                exit 1
                ;;
        esac
    done
    
    # Check if Ansible is installed
    check_ansible
    
    # Validate files
    validate_inventory
    validate_playbook
    
    # Run deployment
    run_deployment
    
    # Final summary
    echo -e "${GREEN}"
    echo "============================================"
    echo "    DEPLOYMENT SUMMARY"
    echo "============================================"
    echo "Target: $TARGET_HOST"
    echo "Environment: $ENVIRONMENT"
    echo "Deployment Type: $DEPLOYMENT_TYPE"
    echo "Verification: $(if [ "$SKIP_VERIFICATION" = true ]; then echo "Skipped"; else echo "Enabled"; fi)"
    echo "============================================"
    echo "Next Steps:"
    echo "1. Test the deployed services"
    echo "2. Check logs at /opt/nir_mistral/logs/"
    echo "3. Access Django at http://$TARGET_HOST:8000"
    echo "4. Access Port Agent at http://$TARGET_HOST:8001"
    echo "============================================${NC}"
}

# Run main function
main "$@"