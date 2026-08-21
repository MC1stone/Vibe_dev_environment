#!/usr/bin/env python3
import pytest
import os
from pathlib import Path

# Fixtures available to all tests

@pytest.fixture
def project_root():
    return Path(__file__).parent.parent

@pytest.fixture
def agents_dir(project_root):
    return project_root / 'agents'

@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary test data directory"""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    return data_dir
