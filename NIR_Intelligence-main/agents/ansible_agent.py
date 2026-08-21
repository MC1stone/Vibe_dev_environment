# NIR Intelligence Platform - Ansible Agent
# Handles infrastructure automation and configuration management

import os
import subprocess
from typing import Any, Dict, List

import yaml

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class AnsibleAgent(BaseAgent):
    """Agent for managing infrastructure using Ansible"""

    def __init__(self, **kwargs):
        super().__init__(name="AnsibleAgent", version="1.0.0", **kwargs)
        self.dependencies = ["ansible", "ansible-core"]
        self.playbook_directory = kwargs.get("playbook_directory", "ansible/playbooks")
        self.inventory_file = kwargs.get("inventory_file", "ansible/inventory.ini")
        self.ansible_version = kwargs.get("ansible_version", "2.14.0")
        self.deployment_modes = kwargs.get("deployment_modes", {})

    def _check_ansible_installed(self) -> bool:
        """Check if Ansible is installed"""
        try:
            result = subprocess.run(["ansible", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version_info = result.stdout.split("\n")[0]
                self.logger.info(f"Ansible installed: {version_info}")
                return True
            else:
                self.log_error(
                    "Ansible not found",
                    ErrorSeverity.CRITICAL,
                    {"suggested_fix": "Install Ansible using: pip install ansible ansible-core"},
                )
                return False
        except Exception as e:
            self.log_error(f"Failed to check Ansible installation: {str(e)}", ErrorSeverity.HIGH)
            return False

    def _check_playbook_directory(self) -> bool:
        """Check if playbook directory exists and contains playbooks"""
        if not os.path.exists(self.playbook_directory):
            self.log_error(
                f"Playbook directory not found: {self.playbook_directory}",
                ErrorSeverity.CRITICAL,
                {"suggested_fix": f"Create directory: mkdir -p {self.playbook_directory}"},
            )
            return False

        # Check for playbook files
        playbooks = [f for f in os.listdir(self.playbook_directory) if f.endswith(".yml") or f.endswith(".yaml")]
        if not playbooks:
            self.log_error(f"No playbook files found in {self.playbook_directory}", ErrorSeverity.CRITICAL)
            return False

        self.logger.info(f"Found {len(playbooks)} playbooks in {self.playbook_directory}")
        return True

    def _check_inventory_file(self) -> bool:
        """Check if inventory file exists and is valid"""
        if not os.path.exists(self.inventory_file):
            self.log_error(
                f"Inventory file not found: {self.inventory_file}",
                ErrorSeverity.CRITICAL,
                {"suggested_fix": "Create a basic inventory file"},
            )
            return False

        try:
            # Try to parse the inventory file
            with open(self.inventory_file, "r") as f:
                content = f.read()
                if not content.strip():
                    self.log_error(f"Inventory file is empty: {self.inventory_file}", ErrorSeverity.HIGH)
                    return False

            self.logger.info(f"Inventory file validated: {self.inventory_file}")
            return True
        except Exception as e:
            self.log_error(f"Failed to read inventory file: {str(e)}", ErrorSeverity.HIGH)
            return False

    def _run_playbook(self, playbook_name: str, extra_vars: Dict[str, Any] = None) -> bool:
        """Run a specific Ansible playbook"""
        playbook_path = os.path.join(self.playbook_directory, playbook_name)

        if not os.path.exists(playbook_path):
            self.log_error(f"Playbook not found: {playbook_name}", ErrorSeverity.HIGH)
            return False

        try:
            # Build Ansible command
            cmd = ["ansible-playbook", "-i", self.inventory_file, playbook_path]

            # Add extra vars if provided
            if extra_vars:
                for key, value in extra_vars.items():
                    cmd.extend(["-e", f"{key}={value}"])

            self.logger.info(f"Running playbook: {playbook_name}")
            self.logger.debug(f"Command: {' '.join(cmd)}")

            # Run playbook
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"Playbook {playbook_name} completed successfully")
                return True
            else:
                self.log_error(
                    f"Playbook {playbook_name} failed",
                    ErrorSeverity.HIGH,
                    {"stderr": result.stderr, "stdout": result.stdout, "return_code": result.returncode},
                )
                return False

        except Exception as e:
            self.log_error(f"Error running playbook {playbook_name}: {str(e)}", ErrorSeverity.HIGH)
            return False

    def _run_deployment_playbooks(self) -> Dict[str, bool]:
        """Run deployment playbooks based on configuration"""
        results = {}

        for mode_name, mode_config in self.deployment_modes.items():
            playbook = mode_config.get("playbook")
            if playbook:
                self.logger.info(f"Running deployment for {mode_name} mode")
                results[mode_name] = self._run_playbook(playbook, mode_config.get("extra_vars"))
            else:
                self.logger.warning(f"No playbook configured for {mode_name} mode")
                results[mode_name] = False

        return results

    def _validate_ansible_config(self) -> bool:
        """Validate Ansible configuration"""
        try:
            # Check ansible.cfg
            if os.path.exists("ansible.cfg"):
                self.logger.info("Found ansible.cfg configuration file")

            # Check for common configuration issues
            result = subprocess.run(["ansible", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                self.log_error("Ansible configuration validation failed", ErrorSeverity.MEDIUM)
                return False

            return True
        except Exception as e:
            self.log_error(f"Error validating Ansible configuration: {str(e)}", ErrorSeverity.MEDIUM)
            return False

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute Ansible agent workflow"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting Ansible agent execution")

            # Step 1: Check Ansible installation
            if not self._check_ansible_installed():
                return self._handle_error(Exception("Ansible check failed"))

            # Step 2: Check playbook directory
            if not self._check_playbook_directory():
                return self._handle_error(Exception("Playbook directory check failed"))

            # Step 3: Check inventory file
            if not self._check_inventory_file():
                return self._handle_error(Exception("Inventory file check failed"))

            # Step 4: Validate Ansible configuration
            if not self._validate_ansible_config():
                self.log_error("Ansible configuration validation failed", ErrorSeverity.MEDIUM)

            # Step 5: Run deployment playbooks
            deployment_results = self._run_deployment_playbooks()

            # Check if all deployments were successful
            all_successful = all(deployment_results.values())
            if not all_successful:
                failed_deployments = [mode for mode, success in deployment_results.items() if not success]
                self.log_error(
                    f"Some deployments failed: {', '.join(failed_deployments)}",
                    ErrorSeverity.MEDIUM,
                    {"deployment_results": deployment_results},
                )

            # All steps completed
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(
                {
                    "ansible_installed": True,
                    "playbooks_validated": True,
                    "inventory_validated": True,
                    "deployment_results": deployment_results,
                    "all_deployments_successful": all_successful,
                }
            )

        except Exception as e:
            return self._handle_error(e)
