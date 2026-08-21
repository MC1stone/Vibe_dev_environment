#!/usr/bin/env python3
"""
NIR Intelligence Platform - HSWTStylingAgent
Agent for applying HSWT.de styling to Django templates and UI components
"""

import logging
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from .base_agent import BaseAgent, AgentOutput, AgentStatus, ErrorSeverity, AgentError


@dataclass
class HSWTColorScheme:
    """HSWT.de color scheme configuration"""
    primary: str = "#006699"
    secondary: str = "#0099CC"
    accent: str = "#FF6600"
    background: str = "#FFFFFF"
    text: str = "#333333"
    text_light: str = "#666666"
    border: str = "#CCCCCC"
    success: str = "#28A745"
    warning: str = "#FFC107"
    error: str = "#DC3545"
    info: str = "#17A2B8"


@dataclass
class HSWTTypography:
    """HSWT.de typography configuration"""
    font_family: str = "'Open Sans', 'Helvetica Neue', Arial, sans-serif"
    heading_font: str = "'Open Sans', 'Helvetica Neue', Arial, sans-serif"
    base_size: str = "16px"
    heading_sizes: Dict[str, str] = field(default_factory=lambda: {
        "h1": "2.5rem",
        "h2": "2rem", 
        "h3": "1.75rem",
        "h4": "1.5rem",
        "h5": "1.25rem",
        "h6": "1rem"
    })


@dataclass
class StyleComponent:
    """Represents a generated CSS component"""
    name: str
    css: str
    dependencies: List[str] = field(default_factory=list)


class HSWTStylingAgent(BaseAgent):
    """
    Agent for applying HSWT.de styling to Django templates and UI components
    
    Features:
    - Generate HSWT.de compliant CSS framework
    - Apply styling to Django templates
    - Adapt ILIAS interface elements to HSWT.de style
    - Create responsive design components
    - Generate theme variables and mixins
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="HSWTStylingAgent", version="2.0.0", **kwargs)
        self.dependencies = ['jinja2', 'cssutils']
        self.logger = logging.getLogger(f"Agent.HSWTStylingAgent")
        
        # Configuration
        self.color_scheme = HSWTColorScheme()
        self.typography = HSWTTypography()
        self.output_dir = kwargs.get('output_dir', 'static/css/hswt')
        self.template_dir = kwargs.get('template_dir', 'templates')
        
        # Initialize agent-specific attributes
        self._initialize_attributes()
    
    def _initialize_attributes(self):
        """Initialize agent-specific attributes"""
        self.components: Dict[str, StyleComponent] = {}
        self.generated_files: List[str] = []
        self.stats = {
            'css_files_generated': 0,
            'templates_styled': 0,
            'components_created': 0,
            'errors': 0
        }
    
    def generate_color_variables(self) -> str:
        """Generate CSS custom properties for HSWT color scheme"""
        variables = [
            f"--hswt-primary: {self.color_scheme.primary};",
            f"--hswt-secondary: {self.color_scheme.secondary};",
            f"--hswt-accent: {self.color_scheme.accent};",
            f"--hswt-background: {self.color_scheme.background};",
            f"--hswt-text: {self.color_scheme.text};",
            f"--hswt-text-light: {self.color_scheme.text_light};",
            f"--hswt-border: {self.color_scheme.border};",
            f"--hswt-success: {self.color_scheme.success};",
            f"--hswt-warning: {self.color_scheme.warning};",
            f"--hswt-error: {self.color_scheme.error};",
            f"--hswt-info: {self.color_scheme.info};",
            "--hswt-primary-light: #E6F2FF;",
            "--hswt-primary-dark: #004466;",
            "--hswt-secondary-light: #E6F7FF;",
            "--hswt-secondary-dark: #006688;"
        ]
        
        return "\n".join([f"  {var}" for var in variables])
    
    def generate_typography_variables(self) -> str:
        """Generate CSS custom properties for HSWT typography"""
        variables = [
            f"--hswt-font-family: {self.typography.font_family};",
            f"--hswt-heading-font: {self.typography.heading_font};",
            f"--hswt-base-size: {self.typography.base_size};",
        ]
        
        for heading, size in self.typography.heading_sizes.items():
            variables.append(f"--hswt-{heading}-size: {size};")
        
        return "\n".join([f"  {var}" for var in variables])
    
    def generate_base_styles(self) -> str:
        """Generate base CSS styles for HSWT.de"""
        return """
/* HSWT.de Base Styles */
:root {
  /* Color Variables */
{{color_variables}}

  /* Typography Variables */
{{typography_variables}}
}

/* Reset and Base Styles */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-size: var(--hswt-base-size);
  scroll-behavior: smooth;
}

body {
  font-family: var(--hswt-font-family);
  color: var(--hswt-text);
  background-color: var(--hswt-background);
  line-height: 1.6;
  min-height: 100vh;
}

a {
  color: var(--hswt-primary);
  text-decoration: none;
  transition: color 0.3s ease;
}

a:hover {
  color: var(--hswt-primary-dark);
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
  font-family: var(--hswt-heading-font);
  font-weight: 600;
  line-height: 1.2;
  margin-bottom: 0.5em;
  color: var(--hswt-text);
}

h1 { font-size: var(--hswt-h1-size); }
h2 { font-size: var(--hswt-h2-size); }
h3 { font-size: var(--hswt-h3-size); }
h4 { font-size: var(--hswt-h4-size); }
h5 { font-size: var(--hswt-h5-size); }
h6 { font-size: var(--hswt-h6-size); }

p {
  margin-bottom: 1em;
}

/* Buttons */
.btn {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-family: var(--hswt-font-family);
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.btn-primary {
  background-color: var(--hswt-primary);
  color: white;
}

.btn-primary:hover {
  background-color: var(--hswt-primary-dark);
}

.btn-secondary {
  background-color: var(--hswt-secondary);
  color: white;
}

.btn-secondary:hover {
  background-color: var(--hswt-secondary-dark);
}

.btn-outline {
  background-color: transparent;
  border: 1px solid var(--hswt-primary);
  color: var(--hswt-primary);
}

.btn-outline:hover {
  background-color: var(--hswt-primary-light);
}

/* Forms */
.form-control {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--hswt-border);
  border-radius: 4px;
  font-family: var(--hswt-font-family);
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.form-control:focus {
  outline: none;
  border-color: var(--hswt-primary);
  box-shadow: 0 0 0 2px rgba(0, 102, 153, 0.2);
}

/* Cards */
.card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  border: 1px solid var(--hswt-border);
}

.card-header {
  border-bottom: 1px solid var(--hswt-border);
  padding-bottom: 1rem;
  margin-bottom: 1rem;
}

/* Alerts */
.alert {
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.alert-success { background-color: var(--hswt-success); color: white; }
.alert-warning { background-color: var(--hswt-warning); color: #333; }
.alert-error { background-color: var(--hswt-error); color: white; }
.alert-info { background-color: var(--hswt-info); color: white; }

/* Navigation */
.navbar {
  background-color: var(--hswt-primary);
  color: white;
  padding: 1rem 2rem;
}

.navbar a {
  color: white;
  margin: 0 1rem;
}

.navbar a:hover {
  color: var(--hswt-primary-light);
}

/* Utility Classes */
.text-primary { color: var(--hswt-primary); }
.text-secondary { color: var(--hswt-secondary); }
.bg-primary { background-color: var(--hswt-primary); color: white; }
.bg-secondary { background-color: var(--hswt-secondary); color: white; }

/* Responsive Design */
@media (max-width: 768px) {
  .container {
    padding: 0 1rem;
  }
  
  h1 { font-size: 2rem; }
  h2 { font-size: 1.75rem; }
  h3 { font-size: 1.5rem; }
}

@media (max-width: 480px) {
  h1 { font-size: 1.75rem; }
  h2 { font-size: 1.5rem; }
  h3 { font-size: 1.25rem; }
  
  .btn {
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
  }
}
"""
    
    def generate_ilias_adaptation_styles(self) -> str:
        """Generate CSS to adapt ILIAS interface elements to HSWT.de style"""
        return """
/* ILIAS Interface Adaptation for HSWT.de */

/* ILIAS Header */
.ilias-header {
  background-color: var(--hswt-primary) !important;
  border-bottom: 3px solid var(--hswt-secondary) !important;
}

.ilias-header .logo {
  max-height: 40px !important;
}

/* ILIAS Navigation */
.ilias-main-menu {
  background-color: var(--hswt-primary) !important;
}

.ilias-main-menu a {
  color: white !important;
  font-family: var(--hswt-font-family) !important;
}

.ilias-main-menu a:hover {
  background-color: var(--hswt-primary-dark) !important;
}

/* ILIAS Content Areas */
.ilias-content {
  font-family: var(--hswt-font-family) !important;
  color: var(--hswt-text) !important;
  background-color: var(--hswt-background) !important;
}

/* ILIAS Tables */
.ilias-table {
  border: 1px solid var(--hswt-border) !important;
}

.ilias-table th {
  background-color: var(--hswt-primary) !important;
  color: white !important;
  font-family: var(--hswt-heading-font) !important;
}

.ilias-table td {
  border-bottom: 1px solid var(--hswt-border) !important;
}

.ilias-table tr:hover td {
  background-color: var(--hswt-primary-light) !important;
}

/* ILIAS Buttons */
.ilias-btn {
  background-color: var(--hswt-primary) !important;
  color: white !important;
  border: none !important;
  font-family: var(--hswt-font-family) !important;
}

.ilias-btn:hover {
  background-color: var(--hswt-primary-dark) !important;
}

/* ILIAS Forms */
.ilias-form input,
.ilias-form select,
.ilias-form textarea {
  border: 1px solid var(--hswt-border) !important;
  font-family: var(--hswt-font-family) !important;
}

.ilias-form input:focus,
.ilias-form select:focus,
.ilias-form textarea:focus {
  border-color: var(--hswt-primary) !important;
  box-shadow: 0 0 0 2px rgba(0, 102, 153, 0.2) !important;
}

/* ILIAS Course List */
.ilias-course-list {
  background-color: white !important;
  border: 1px solid var(--hswt-border) !important;
  border-radius: 8px !important;
}

.ilias-course-item {
  padding: 1rem !important;
  border-bottom: 1px solid var(--hswt-border) !important;
}

.ilias-course-item:hover {
  background-color: var(--hswt-primary-light) !important;
}

/* ILIAS Breadcrumbs */
.ilias-breadcrumb {
  font-family: var(--hswt-font-family) !important;
  color: var(--hswt-text-light) !important;
}

.ilias-breadcrumb a {
  color: var(--hswt-primary) !important;
}

/* ILIAS Tabs */
.ilias-tabs {
  border-bottom: 1px solid var(--hswt-border) !important;
}

.ilias-tab {
  padding: 0.75rem 1.5rem !important;
  font-family: var(--hswt-font-family) !important;
}

.ilias-tab.active {
  background-color: var(--hswt-primary) !important;
  color: white !important;
  border-bottom: 3px solid var(--hswt-secondary) !important;
}

.ilias-tab:hover {
  background-color: var(--hswt-primary-light) !important;
}
"""
    
    def generate_responsive_components(self) -> str:
        """Generate responsive design components"""
        return """
/* Responsive Grid System */
.container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.row {
  display: flex;
  flex-wrap: wrap;
  margin: 0 -0.75rem;
}

.col {
  padding: 0 0.75rem;
  flex: 1 0 0%;
}

@media (min-width: 576px) {
  .col-sm-6 { flex: 0 0 50%; max-width: 50%; }
  .col-sm-4 { flex: 0 0 33.333333%; max-width: 33.333333%; }
  .col-sm-3 { flex: 0 0 25%; max-width: 25%; }
  .col-sm-8 { flex: 0 0 66.666667%; max-width: 66.666667%; }
}

@media (min-width: 768px) {
  .col-md-6 { flex: 0 0 50%; max-width: 50%; }
  .col-md-4 { flex: 0 0 33.333333%; max-width: 33.333333%; }
  .col-md-3 { flex: 0 0 25%; max-width: 25%; }
  .col-md-8 { flex: 0 0 66.666667%; max-width: 66.666667%; }
}

@media (min-width: 992px) {
  .col-lg-6 { flex: 0 0 50%; max-width: 50%; }
  .col-lg-4 { flex: 0 0 33.333333%; max-width: 33.333333%; }
  .col-lg-3 { flex: 0 0 25%; max-width: 25%; }
  .col-lg-8 { flex: 0 0 66.666667%; max-width: 66.666667%; }
}

/* Responsive Navigation */
.navbar-nav {
  display: flex;
  flex-direction: column;
}

@media (min-width: 768px) {
  .navbar-nav {
    flex-direction: row;
  }
}

.navbar-toggle {
  display: block;
}

@media (min-width: 768px) {
  .navbar-toggle {
    display: none;
  }
}

/* Mobile Menu */
.mobile-menu {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background-color: var(--hswt-primary);
  z-index: 1000;
}

.mobile-menu.active {
  display: block;
}

.mobile-menu a {
  display: block;
  padding: 1rem;
  color: white;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

/* Responsive Cards */
.card-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}

@media (min-width: 576px) {
  .card-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 768px) {
  .card-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 992px) {
  .card-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

/* Responsive Tables */
.table-responsive {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

@media (max-width: 767px) {
  .table-responsive {
    display: block;
  }
  
  .table-responsive table {
    width: 100%;
    border: 0;
  }
  
  .table-responsive thead {
    display: none;
  }
  
  .table-responsive tr {
    display: block;
    margin-bottom: 1rem;
    border: 1px solid var(--hswt-border);
    border-radius: 4px;
  }
  
  .table-responsive td {
    display: block;
    text-align: right;
    padding: 0.5rem;
    border-bottom: 1px solid var(--hswt-border);
  }
  
  .table-responsive td::before {
    content: attr(data-label);
    float: left;
    font-weight: bold;
    text-align: left;
  }
  
  .table-responsive td:last-child {
    border-bottom: 0;
  }
}

/* Touch Targets for Mobile */
.btn,
.form-control,
.card {
  min-height: 44px;
  min-width: 44px;
}

/* Focus States for Accessibility */
:focus {
  outline: 2px solid var(--hswt-primary);
  outline-offset: 2px;
}

/* Skip Link for Accessibility */
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: var(--hswt-primary);
  color: white;
  padding: 8px;
  z-index: 100;
  transition: top 0.3s;
}

.skip-link:focus {
  top: 0;
}
"""
    
    def generate_css_files(self) -> Dict[str, str]:
        """Generate all CSS files for HSWT.de styling"""
        files = {}
        
        # Main variables file
        color_vars = self.generate_color_variables()
        typo_vars = self.generate_typography_variables()
        
        files['variables.css'] = f"""
/* HSWT.de Theme Variables */
:root {{
{color_vars}

{typo_vars}
}}

/* Dark mode support */
@media (prefers-color-scheme: dark) {{
  :root {{
    --hswt-background: #1a1a1a;
    --hswt-text: #e0e0e0;
    --hswt-text-light: #b0b0b0;
    --hswt-border: #404040;
  }}
}}
"""
        
        # Main styles file
        base_styles = self.generate_base_styles()
        files['main.css'] = base_styles.replace('{{color_variables}}', color_vars).replace('{{typography_variables}}', typo_vars)
        
        # ILIAS adaptation
        files['ilias.css'] = self.generate_ilias_adaptation_styles()
        
        # Responsive components
        files['responsive.css'] = self.generate_responsive_components()
        
        # Components file
        files['components.css'] = self._generate_component_styles()
        
        # Utility classes
        files['utilities.css'] = self._generate_utility_classes()
        
        return files
    
    def _generate_component_styles(self) -> str:
        """Generate component-specific styles"""
        return """
/* HSWT Component Styles */

/* Buttons with Icons */
.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.btn-icon .icon {
  font-size: 1.2rem;
}

/* Loading Spinners */
.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--hswt-border);
  border-top: 4px solid var(--hswt-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Progress Bars */
.progress {
  height: 20px;
  background-color: var(--hswt-border);
  border-radius: 10px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background-color: var(--hswt-primary);
  transition: width 0.3s ease;
}

.progress-bar.success { background-color: var(--hswt-success); }
.progress-bar.warning { background-color: var(--hswt-warning); }
.progress-bar.error { background-color: var(--hswt-error); }

/* Badges */
.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.badge-primary { background-color: var(--hswt-primary); color: white; }
.badge-secondary { background-color: var(--hswt-secondary); color: white; }
.badge-success { background-color: var(--hswt-success); color: white; }
.badge-warning { background-color: var(--hswt-warning); color: #333; }
.badge-error { background-color: var(--hswt-error); color: white; }

/* Modals */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid var(--hswt-border);
}

.modal-body {
  padding: 1.5rem;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--hswt-border);
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

/* Tooltips */
.tooltip {
  position: relative;
  display: inline-block;
}

.tooltip .tooltiptext {
  visibility: hidden;
  width: 200px;
  background-color: #333;
  color: #fff;
  text-align: center;
  border-radius: 4px;
  padding: 0.5rem;
  position: absolute;
  z-index: 1;
  bottom: 125%;
  left: 50%;
  transform: translateX(-50%);
  opacity: 0;
  transition: opacity 0.3s;
  font-size: 0.75rem;
}

.tooltip:hover .tooltiptext {
  visibility: visible;
  opacity: 1;
}

/* Accordions */
.accordion {
  border: 1px solid var(--hswt-border);
  border-radius: 4px;
  overflow: hidden;
}

.accordion-header {
  padding: 1rem 1.5rem;
  background-color: var(--hswt-primary-light);
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.accordion-header:hover {
  background-color: var(--hswt-primary);
  color: white;
}

.accordion-content {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
}

.accordion-content.active {
  max-height: 1000px;
  padding: 1rem 1.5rem;
}

/* Tabs */
.tabs {
  display: flex;
  border-bottom: 1px solid var(--hswt-border);
  margin-bottom: 1rem;
}

.tab {
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  border: none;
  background: none;
  font-family: var(--hswt-font-family);
  color: var(--hswt-text-light);
  border-bottom: 2px solid transparent;
}

.tab:hover {
  color: var(--hswt-primary);
}

.tab.active {
  color: var(--hswt-primary);
  border-bottom-color: var(--hswt-primary);
}

.tab-content {
  display: none;
}

.tab-content.active {
  display: block;
}
"""
    
    def _generate_utility_classes(self) -> str:
        """Generate utility CSS classes"""
        return """
/* HSWT Utility Classes */

/* Spacing */
.m-0 { margin: 0; }
.m-1 { margin: 0.25rem; }
.m-2 { margin: 0.5rem; }
.m-3 { margin: 0.75rem; }
.m-4 { margin: 1rem; }
.m-5 { margin: 1.5rem; }

.mt-0 { margin-top: 0; }
.mt-1 { margin-top: 0.25rem; }
.mt-2 { margin-top: 0.5rem; }
.mt-3 { margin-top: 0.75rem; }
.mt-4 { margin-top: 1rem; }
.mt-5 { margin-top: 1.5rem; }

.mb-0 { margin-bottom: 0; }
.mb-1 { margin-bottom: 0.25rem; }
.mb-2 { margin-bottom: 0.5rem; }
.mb-3 { margin-bottom: 0.75rem; }
.mb-4 { margin-bottom: 1rem; }
.mb-5 { margin-bottom: 1.5rem; }

.mr-0 { margin-right: 0; }
.mr-1 { margin-right: 0.25rem; }
.mr-2 { margin-right: 0.5rem; }
.mr-3 { margin-right: 0.75rem; }
.mr-4 { margin-right: 1rem; }
.mr-5 { margin-right: 1.5rem; }

.mx-0 { margin-left: 0; margin-right: 0; }
.mx-1 { margin-left: 0.25rem; margin-right: 0.25rem; }
.mx-2 { margin-left: 0.5rem; margin-right: 0.5rem; }

.my-0 { margin-top: 0; margin-bottom: 0; }
.my-1 { margin-top: 0.25rem; margin-bottom: 0.25rem; }
.my-2 { margin-top: 0.5rem; margin-bottom: 0.5rem; }

/* Padding */
.p-0 { padding: 0; }
.p-1 { padding: 0.25rem; }
.p-2 { padding: 0.5rem; }
.p-3 { padding: 0.75rem; }
.p-4 { padding: 1rem; }
.p-5 { padding: 1.5rem; }

/* Text Alignment */
.text-left { text-align: left; }
.text-center { text-align: center; }
.text-right { text-align: right; }

/* Display */
.d-block { display: block; }
.d-inline { display: inline; }
.d-inline-block { display: inline-block; }
.d-flex { display: flex; }
.d-grid { display: grid; }
.d-none { display: none; }

/* Flexbox */
.flex-row { flex-direction: row; }
.flex-column { flex-direction: column; }
.justify-start { justify-content: flex-start; }
.justify-center { justify-content: center; }
.justify-end { justify-content: flex-end; }
.justify-between { justify-content: space-between; }
.align-start { align-items: flex-start; }
.align-center { align-items: center; }
.align-end { align-items: flex-end; }

/* Text */
.text-uppercase { text-transform: uppercase; }
.text-lowercase { text-transform: lowercase; }
.text-capitalize { text-transform: capitalize; }
.text-bold { font-weight: bold; }
.text-normal { font-weight: normal; }
.text-light { font-weight: 300; }

/* Colors */
.text-white { color: white; }
.text-black { color: black; }

/* Background Colors */
.bg-white { background-color: white; }
.bg-light { background-color: #f8f9fa; }
.bg-dark { background-color: #343a40; }

/* Border */
.border { border: 1px solid var(--hswt-border); }
.border-0 { border: 0; }
.border-top { border-top: 1px solid var(--hswt-border); }
.border-bottom { border-bottom: 1px solid var(--hswt-border); }

/* Border Radius */
.rounded { border-radius: 4px; }
.rounded-0 { border-radius: 0; }
.rounded-circle { border-radius: 50%; }

/* Width */
.w-100 { width: 100%; }
.w-75 { width: 75%; }
.w-50 { width: 50%; }
.w-25 { width: 25%; }

/* Float */
.float-left { float: left; }
.float-right { float: right; }
.clearfix::after { content: ""; display: table; clear: both; }

/* Position */
.position-relative { position: relative; }
.position-absolute { position: absolute; }
.position-fixed { position: fixed; }

/* Overflow */
.overflow-hidden { overflow: hidden; }
.overflow-auto { overflow: auto; }

/* Shadows */
.shadow-sm { box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1); }
.shadow { box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); }
.shadow-lg { box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15); }

/* Transitions */
.transition { transition: all 0.3s ease; }
.transition-fast { transition: all 0.15s ease; }
.transition-slow { transition: all 0.5s ease; }
"""
    
    def apply_styling_to_template(self, template_path: str, template_content: str) -> str:
        """Apply HSWT styling to a Django template"""
        try:
            # Add HSWT CSS includes if not present
            if 'hswt' not in template_content.lower():
                # Find the head section or add at the top
                if '<head>' in template_content:
                    head_end = template_content.find('</head>')
                    if head_end != -1:
                        css_includes = '''
    <!-- HSWT.de Styling -->
    <link rel="stylesheet" href="{% static 'css/hswt/variables.css' %}">
    <link rel="stylesheet" href="{% static 'css/hswt/main.css' %}">
    <link rel="stylesheet" href="{% static 'css/hswt/components.css' %}">
    <link rel="stylesheet" href="{% static 'css/hswt/utilities.css' %}">
    <link rel="stylesheet" href="{% static 'css/hswt/responsive.css' %}">
                        '''
                        template_content = (template_content[:head_end] + css_includes + 
                                          template_content[head_end:])
                
                # Add container class to main content
                if '<body>' in template_content:
                    body_start = template_content.find('<body>') + 6
                    if body_start != 5:
                        template_content = (template_content[:body_start] + 
                                          '<div class="container">' + 
                                          template_content[body_start:])
                        if '</body>' in template_content:
                            body_end = template_content.rfind('</body>')
                            template_content = (template_content[:body_end] + 
                                              '</div>' + 
                                              template_content[body_end:])
            
            # Replace generic classes with HSWT classes
            replacements = [
                ('class="btn"', 'class="btn btn-primary"'),
                ('class="button"', 'class="btn btn-primary"'),
                ('class="card"', 'class="card"'),
                ('class="alert"', 'class="alert"'),
                ('class="form-control"', 'class="form-control"'),
            ]
            
            for old, new in replacements:
                template_content = template_content.replace(old, new)
            
            self.stats['templates_styled'] += 1
            return template_content
            
        except Exception as e:
            self.logger.error(f"Error applying styling to template {template_path}: {str(e)}")
            self.stats['errors'] += 1
            return template_content
    
    def generate_template_structure(self) -> Dict[str, str]:
        """Generate Django template structure with HSWT styling"""
        templates = {}
        
        # Base template
        templates['base_hswt.html'] = '''{% load static %}
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}NIR Intelligence Platform{% endblock %}</title>
    
    <!-- HSWT.de Styling -->
    <link rel="stylesheet" href="{% static 'css/hswt/variables.css' %}">
    <link rel="stylesheet" href="{% static 'css/hswt/main.css' %}">
    <link rel="stylesheet" href="{% static 'css/hswt/components.css' %}">
    <link rel="stylesheet" href="{% static 'css/hswt/utilities.css' %}">
    <link rel="stylesheet" href="{% static 'css/hswt/responsive.css' %}">
    <link rel="stylesheet" href="{% static 'css/hswt/ilias.css' %}">
    
    <!-- Additional CSS -->
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Skip Link for Accessibility -->
    <a href="#main-content" class="skip-link">Zum Hauptinhalt springen</a>
    
    <!-- Navigation -->
    <nav class="navbar">
        <div class="container">
            <a href="{% url 'home' %}" class="navbar-brand">
                <img src="{% static 'images/logo.png' %}" alt="NIR Intelligence Logo" class="logo">
                NIR Intelligence
            </a>
            <div class="navbar-nav">
                <a href="{% url 'home' %}" class="nav-link">Home</a>
                <a href="{% url 'spectra' %}" class="nav-link">Spectra</a>
                <a href="{% url 'analysis' %}" class="nav-link">Analysis</a>
                <a href="{% url 'federated' %}" class="nav-link">Federated</a>
                <a href="{% url 'ilias' %}" class="nav-link">ILIAS</a>
            </div>
            <div class="navbar-user">
                {% if user.is_authenticated %}
                    <span class="user-greeting">Hello, {{ user.username }}</span>
                    <a href="{% url 'logout' %}" class="btn btn-outline">Logout</a>
                {% else %}
                    <a href="{% url 'login' %}" class="btn btn-primary">Login</a>
                {% endif %}
            </div>
        </div>
    </nav>
    
    <!-- Messages/Alerts -->
    {% if messages %}
    <div class="container mt-3">
        {% for message in messages %}
        <div class="alert alert-{{ message.tags }}">
            {{ message }}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    <!-- Main Content -->
    <main id="main-content" class="container mt-4">
        {% block content %}{% endblock %}
    </main>
    
    <!-- Footer -->
    <footer class="footer mt-5 py-4 bg-light">
        <div class="container">
            <div class="row">
                <div class="col-md-4">
                    <h5>NIR Intelligence</h5>
                    <p>Open Science Spectroscopy Platform</p>
                </div>
                <div class="col-md-4">
                    <h5>Quick Links</h5>
                    <ul class="list-unstyled">
                        <li><a href="{% url 'docs' %}">Documentation</a></li>
                        <li><a href="{% url 'help' %}">Help</a></li>
                        <li><a href="{% url 'contact' %}">Contact</a></li>
                    </ul>
                </div>
                <div class="col-md-4">
                    <h5>HSWT</h5>
                    <p>Weihenstephan-Triesdorf University</p>
                    <p>Applied Sciences</p>
                </div>
            </div>
            <div class="text-center mt-3 pt-3 border-top">
                <p>&copy; 2026 NIR Intelligence Platform. All rights reserved.</p>
            </div>
        </div>
    </footer>
    
    <!-- JavaScript -->
    <script src="{% static 'js/main.js' %}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>'''
        
        # Home page template
        templates['home.html'] = '''{% extends "base_hswt.html" %}

{% block title %}Home - NIR Intelligence{% endblock %}

{% block content %}
<div class="hero-section bg-primary text-white p-5 rounded mb-4">
    <div class="row align-center">
        <div class="col-md-6">
            <h1>Welcome to NIR Intelligence</h1>
            <p class="lead">Open Science Spectroscopy Platform for analyzing spectral data from any spectrometer</p>
            <div class="mt-4">
                <a href="{% url 'upload' %}" class="btn btn-secondary btn-lg mr-2">Upload Spectra</a>
                <a href="{% url 'analysis' %}" class="btn btn-outline-light btn-lg">View Analysis</a>
            </div>
        </div>
        <div class="col-md-6">
            <img src="{% static 'images/spectrometer-illustration.png' %}" alt="Spectrometer" class="img-fluid">
        </div>
    </div>
</div>

<div class="row mb-4">
    <div class="col-md-4 mb-3">
        <div class="card h-100">
            <div class="card-header bg-primary text-white">
                <h3>Multi-format Support</h3>
            </div>
            <div class="card-body">
                <p>Upload and analyze spectral data in various formats including WAV, MP3, PNG, JPG, and more.</p>
                <a href="{% url 'upload' %}" class="btn btn-primary">Upload Files</a>
            </div>
        </div>
    </div>
    <div class="col-md-4 mb-3">
        <div class="card h-100">
            <div class="card-header bg-secondary text-white">
                <h3>Advanced Analysis</h3>
            </div>
            <div class="card-body">
                <p>Detect spectrometer issues, analyze metadata quality, and get parameter recommendations.</p>
                <a href="{% url 'analysis' %}" class="btn btn-secondary">Start Analysis</a>
            </div>
        </div>
    </div>
    <div class="col-md-4 mb-3">
        <div class="card h-100">
            <div class="card-header bg-info text-white">
                <h3>Federated Learning</h3>
            </div>
            <div class="card-body">
                <p>Contribute to and benefit from the federated learning system with other researchers.</p>
                <a href="{% url 'federated' %}" class="btn btn-info">Join Federation</a>
            </div>
        </div>
    </div>
</div>

<div class="card">
    <div class="card-header">
        <h2>Recent Activity</h2>
    </div>
    <div class="card-body">
        <div class="table-responsive">
            <table class="table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>User</th>
                        <th>Action</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for activity in recent_activities %}
                    <tr>
                        <td>{{ activity.date|date:"Y-m-d H:i" }}</td>
                        <td>{{ activity.user.username }}</td>
                        <td>{{ activity.action }}</td>
                        <td><span class="badge badge-{{ activity.status }}">{{ activity.get_status_display }}</span></td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="4" class="text-center">No recent activity</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}'''
        
        return templates
    
    def create_output_directory(self) -> bool:
        """Create the output directory structure"""
        try:
            base_dir = Path(self.output_dir)
            base_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            (base_dir / "css").mkdir(parents=True, exist_ok=True)
            (base_dir / "js").mkdir(parents=True, exist_ok=True)
            (base_dir / "images").mkdir(parents=True, exist_ok=True)
            
            return True
        except Exception as e:
            self.logger.error(f"Error creating output directory: {str(e)}")
            return False
    
    def save_css_files(self, css_files: Dict[str, str]) -> List[str]:
        """Save CSS files to the output directory"""
        saved_files = []
        try:
            base_dir = Path(self.output_dir) / "css" / "hswt"
            base_dir.mkdir(parents=True, exist_ok=True)
            
            for filename, content in css_files.items():
                file_path = base_dir / filename
                with open(file_path, 'w') as f:
                    f.write(content)
                saved_files.append(str(file_path))
                self.logger.info(f"Saved CSS file: {file_path}")
            
            self.stats['css_files_generated'] = len(saved_files)
            return saved_files
            
        except Exception as e:
            self.logger.error(f"Error saving CSS files: {str(e)}")
            self.stats['errors'] += 1
            return saved_files
    
    def save_templates(self, templates: Dict[str, str], template_dir: str = None) -> List[str]:
        """Save Django templates to the template directory"""
        saved_files = []
        try:
            base_dir = Path(template_dir or self.template_dir)
            base_dir.mkdir(parents=True, exist_ok=True)
            
            for filename, content in templates.items():
                file_path = base_dir / filename
                with open(file_path, 'w') as f:
                    f.write(content)
                saved_files.append(str(file_path))
                self.logger.info(f"Saved template: {file_path}")
            
            return saved_files
            
        except Exception as e:
            self.logger.error(f"Error saving templates: {str(e)}")
            self.stats['errors'] += 1
            return saved_files
    
    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute the agent's primary function"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting HSWTStylingAgent execution")
            
            action = context.get('action', 'generate_all')
            
            if action == 'generate_all':
                # Create output directory
                if not self.create_output_directory():
                    return self._create_error_output("Failed to create output directory")
                
                # Generate CSS files
                css_files = self.generate_css_files()
                saved_css = self.save_css_files(css_files)
                
                # Generate templates
                templates = self.generate_template_structure()
                saved_templates = self.save_templates(templates)
                
                # Generate statistics
                output = {
                    "status": "completed",
                    "message": "HSWT styling generation completed successfully",
                    "statistics": self.stats,
                    "generated_files": {
                        "css_files": saved_css,
                        "templates": saved_templates
                    },
                    "color_scheme": {
                        "primary": self.color_scheme.primary,
                        "secondary": self.color_scheme.secondary,
                        "accent": self.color_scheme.accent
                    }
                }
                
            elif action == 'generate_css':
                css_files = self.generate_css_files()
                output = {
                    "status": "completed",
                    "css_files": list(css_files.keys()),
                    "file_count": len(css_files)
                }
                
            elif action == 'generate_templates':
                templates = self.generate_template_structure()
                output = {
                    "status": "completed", 
                    "templates": list(templates.keys()),
                    "template_count": len(templates)
                }
                
            elif action == 'apply_to_template':
                template_path = context.get('template_path')
                template_content = context.get('template_content', '')
                
                if not template_path or not template_content:
                    return self._create_error_output("template_path and template_content are required")
                
                styled_content = self.apply_styling_to_template(template_path, template_content)
                output = {
                    "status": "completed",
                    "original_length": len(template_content),
                    "styled_length": len(styled_content),
                    "template_path": template_path
                }
                
            elif action == 'set_color_scheme':
                new_colors = context.get('colors', {})
                for color_name, color_value in new_colors.items():
                    if hasattr(self.color_scheme, color_name):
                        setattr(self.color_scheme, color_name, color_value)
                
                output = {
                    "status": "completed",
                    "updated_colors": new_colors,
                    "current_scheme": {
                        "primary": self.color_scheme.primary,
                        "secondary": self.color_scheme.secondary,
                        "accent": self.color_scheme.accent
                    }
                }
                
            else:
                output = {"status": "error", "message": f"Unknown action: {action}"}
            
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(output)
            
        except Exception as e:
            return self._handle_error(e)
    
    def validate(self) -> List[AgentError]:
        """Validate agent configuration and state"""
        errors = super().validate()
        
        # Check if output directory is writable
        try:
            test_path = Path(self.output_dir)
            if test_path.exists():
                test_file = test_path / ".write_test"
                with open(test_file, 'w') as f:
                    f.write("test")
                test_file.unlink()
            else:
                # Try to create the directory
                test_path.mkdir(parents=True, exist_ok=True)
                test_path.rmdir()
        except Exception as e:
            errors.append(AgentError(
                agent_name=self.name,
                error_type="permission_error",
                message=f"Output directory is not writable: {self.output_dir}",
                severity=ErrorSeverity.MEDIUM,
                context={"output_dir": self.output_dir},
                solution=f"Ensure directory {self.output_dir} exists and is writable"
            ))
        
        return errors


if __name__ == "__main__":
    # Allow direct execution for testing
    agent = HSWTStylingAgent()
    output = agent.initialize()
    print(f"HSWTStylingAgent initialized: {output.status.name}")
