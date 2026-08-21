# NIR Intelligence Platform - Developer Agent Framework
# Framework for accelerating agent development, testing, and deployment

"""
DeveloperAgent Framework (DAF) for NIR Intelligence Platform

This framework provides:
- Agent code generation from templates
- Automated testing and validation
- Code quality enforcement
- Dependency management
- Development server with hot-reload
- Documentation generation

Usage:
    python -m dev_framework generate agent NewAgent
    python -m dev_framework validate
    python -m dev_framework test
    python -m dev_framework serve
"""

__version__ = "1.0.0"
__author__ = "NIR Development Team"
__license__ = "MIT"

# Framework modules
from . import (
    generator,
    validator,
    tester,
    quality,
    server,
    docs,
    cli
)

__all__ = [
    'generator',
    'validator', 
    'tester',
    'quality',
    'server',
    'docs',
    'cli'
]
