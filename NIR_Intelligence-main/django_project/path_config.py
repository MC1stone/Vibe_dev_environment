"""
Path configuration for NIR_Mistral Django project

This module ensures that all required paths are set up correctly
for importing agents and other modules from the main project.
"""

import os
import sys
from pathlib import Path

def setup_project_paths():
    """Setup Python paths for the NIR_Mistral project"""
    
    # Get the main project root from environment or calculate it
    framework_path = os.getenv('NIR_FRAMEWORK_PATH')
    
    if framework_path:
        project_root = Path(framework_path)
    else:
        # Calculate from this file's location
        this_file = Path(__file__).resolve()
        # Go up from django_project/path_config.py to main project root
        project_root = this_file.parent.parent
    
    # Add project root to path if not already there
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    # Add agents directory to path if not already there
    agents_path = project_root / "agents"
    agents_path_str = str(agents_path)
    if agents_path_str not in sys.path:
        sys.path.insert(0, agents_path_str)
    
    # Also add the main project directory to ensure it's found
    main_project_str = str(project_root)
    if main_project_str not in sys.path:
        sys.path.insert(0, main_project_str)

# Setup paths immediately when this module is imported
setup_project_paths()