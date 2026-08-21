# NIR_Mistral Quarto Report Renderer
# Utility for rendering Quarto reports with spectral analysis data

import os
import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)


class QuartoRenderer:
    """
    Utility class for rendering Quarto reports with spectral analysis data.
    """
    
    def __init__(self):
        self.quarto_path = settings.QUARTO_PATH
        self.reports_dir = Path(settings.QUARTO_REPORTS_DIR)
        self.output_dir = Path(settings.QUARTO_OUTPUT_DIR)
        self.enabled = settings.QUARTO_ENABLED
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def check_quarto_installation(self):
        """Check if Quarto is properly installed and accessible."""
        try:
            result = subprocess.run(
                [self.quarto_path, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Quarto installation verified: {result.stdout.strip()}")
                return True, result.stdout.strip()
            else:
                logger.error(f"Quarto version check failed: {result.stderr}")
                return False, result.stderr
        except FileNotFoundError:
            logger.error(f"Quarto not found at {self.quarto_path}")
            return False, f"Quarto not found at {self.quarto_path}"
        except subprocess.TimeoutExpired:
            logger.error("Quarto version check timed out")
            return False, "Quarto version check timed out"
        except Exception as e:
            logger.error(f"Error checking Quarto installation: {str(e)}")
            return False, str(e)

    def render_report(self, template_name, output_filename=None, data=None, format='html'):
        """
        Render a Quarto report with the given data.
        
        Args:
            template_name (str): Name of the Quarto template file (without extension)
            output_filename (str, optional): Output filename (without extension). Defaults to template_name.
            data (dict, optional): Data to pass to the Quarto template. Defaults to None.
            format (str): Output format ('html', 'pdf', 'docx'). Defaults to 'html'.
            
        Returns:
            tuple: (success: bool, output_path: str or None, error: str or None)
        """
        if not self.enabled:
            logger.warning("Quarto rendering is disabled in settings")
            return False, None, "Quarto rendering is disabled"
        
        # Check Quarto installation
        installed, version = self.check_quarto_installation()
        if not installed:
            return False, None, f"Quarto not properly installed: {version}"
        
        try:
            # Set default output filename
            if output_filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"{template_name}_{timestamp}"
            
            # Find the template file
            template_path = self.reports_dir / f"{template_name}.qmd"
            if not template_path.exists():
                # Try with .qmd extension
                template_path = self.reports_dir / template_name
                if not template_path.exists():
                    return False, None, f"Template file not found: {template_name}"
            
            # Set output path
            if format == 'html':
                output_path = self.output_dir / f"{output_filename}.html"
            elif format == 'pdf':
                output_path = self.output_dir / f"{output_filename}.pdf"
            elif format == 'docx':
                output_path = self.output_dir / f"{output_filename}.docx"
            else:
                output_path = self.output_dir / f"{output_filename}.html"
            
            # Try to render with Quarto first
            success, error = self._render_with_quarto(template_path, output_filename, data, format, output_path)
            
            if success:
                logger.info(f"Successfully rendered report: {output_path}")
                return True, str(output_path), None
            else:
                logger.warning(f"Quarto rendering failed, trying fallback: {error}")
                # Try fallback method (simple template replacement)
                success, fallback_path = self._render_with_fallback(template_path, output_path, data)
                if success:
                    logger.info(f"Successfully rendered report with fallback: {fallback_path}")
                    return True, str(fallback_path), None
                else:
                    logger.error(f"Both Quarto and fallback rendering failed")
                    return False, None, f"Quarto rendering failed: {error}"
                
        except subprocess.TimeoutExpired:
            logger.error("Quarto rendering timed out")
            return False, None, "Quarto rendering timed out"
        except Exception as e:
            logger.error(f"Error rendering Quarto report: {str(e)}")
            return False, None, str(e)

    def _render_with_quarto(self, template_path, output_filename, data, format, output_path):
        """Try to render with Quarto CLI."""
        try:
            template_dir = template_path.parent
            
            # For Quarto, we need to work in the template directory
            # and use relative paths
            output_filename_with_ext = f"{output_filename}.{format}"
            
            # Prepare command - Quarto doesn't like --output with paths, 
            # so we'll let it use the default output location and then move the file
            cmd = [
                self.quarto_path,
                'render',
                template_path.name,  # Just the filename
                '--to', format
            ]
            
            # Add data if provided (as YAML parameters)
            if data:
                # Create a temporary YAML file with the data in the template directory
                params_file = template_dir / f"{output_filename}_params.yml"
                self._write_yaml_params(params_file, data)
                cmd.extend(['--execute-params', f"{output_filename}_params.yml"])
            
            logger.info(f"Rendering with Quarto: {template_path.name}")
            
            # Execute the command from the template directory
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.AGENTS_CONFIG.get('reporting', {}).get('timeout', 300),
                cwd=str(template_dir)
            )
            
            if result.returncode == 0:
                # Quarto creates the output file in the current directory
                # We need to move it to our desired location
                default_output = template_dir / output_filename_with_ext
                if default_output.exists():
                    # Ensure output directory exists
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    # Move the file
                    default_output.rename(output_path)
                    # Clean up params file if it exists
                    params_file = template_dir / f"{output_filename}_params.yml"
                    if params_file.exists():
                        params_file.unlink()
                    return True, None
                else:
                    logger.error(f"Quarto output file not found at {default_output}")
                    return False, f"Output file not created by Quarto"
            else:
                logger.error(f"Quarto rendering failed: {result.stderr}")
                return False, f"Quarto rendering failed: {result.stderr}"
                
        except Exception as e:
            logger.error(f"Error in Quarto rendering: {str(e)}")
            return False, str(e)

    def _render_with_fallback(self, template_path, output_path, data):
        """Fallback rendering using simple template replacement."""
        try:
            # Read the template
            template_content = template_path.read_text()
            
            # Simple template replacement
            if data:
                rendered_content = self._simple_template_replace(template_content, data)
            else:
                rendered_content = template_content
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the rendered content
            output_path.write_text(rendered_content)
            
            return True, output_path
            
        except Exception as e:
            logger.error(f"Error in fallback rendering: {str(e)}")
            return False, None

    def _simple_template_replace(self, content, data):
        """Simple template replacement using {{ key }} syntax."""
        import re
        
        # Replace {{ key }} with data values
        for key, value in data.items():
            # Handle nested data
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    placeholder = f"{{{{ {key}.{subkey} }}}}"
                    content = content.replace(placeholder, str(subvalue))
            elif isinstance(value, list):
                # Join list items with commas
                placeholder = f"{{{{ {key} }}}}"
                content = content.replace(placeholder, ", ".join(str(item) for item in value))
            else:
                placeholder = f"{{{{ {key} }}}}"
                content = content.replace(placeholder, str(value))
        
        # Also handle simple {{ key }} without spaces
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            if isinstance(value, list):
                content = content.replace(placeholder, ", ".join(str(item) for item in value))
            else:
                content = content.replace(placeholder, str(value))
        
        return content

    def _write_yaml_params(self, params_file, data):
        """Write data to a YAML parameters file."""
        try:
            yaml_content = "# Quarto Parameters\n"
            yaml_content += self._dict_to_yaml(data, indent=0)
            params_file.write_text(yaml_content)
            logger.debug(f"Wrote parameters to {params_file}")
        except Exception as e:
            logger.error(f"Error writing YAML parameters: {str(e)}")
            raise

    def _dict_to_yaml(self, data, indent=0):
        """Convert a dictionary to YAML string."""
        yaml_lines = []
        prefix = "  " * indent
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    yaml_lines.append(f"{prefix}{key}:")
                    yaml_lines.append(self._dict_to_yaml(value, indent + 1))
                elif isinstance(value, list):
                    yaml_lines.append(f"{prefix}{key}:")
                    for item in value:
                        if isinstance(item, dict):
                            yaml_lines.append(f"{prefix}  - {self._dict_to_yaml(item, indent + 2).strip()}")
                        else:
                            yaml_lines.append(f"{prefix}  - {item}")
                else:
                    yaml_lines.append(f"{prefix}{key}: {value}")
        else:
            yaml_lines.append(f"{prefix}{data}")
        
        return "\n".join(yaml_lines)

    def render_spectral_analysis_report(self, analysis_data, output_filename=None):
        """
        Render a spectral analysis report with the given analysis data.
        
        Args:
            analysis_data (dict): Spectral analysis data to include in the report
            output_filename (str, optional): Output filename. Defaults to None.
            
        Returns:
            tuple: (success: bool, output_path: str or None, error: str or None)
        """
        # Prepare data for the Quarto template
        quarto_data = {
            'sample_id': analysis_data.get('sample_id', 'Unknown'),
            'quality_score': analysis_data.get('quality_score', 0),
            'quality_grade': analysis_data.get('quality_grade', 'unknown'),
            'issues_detected': analysis_data.get('issues_detected', []),
            'wavelength_range': analysis_data.get('wavelength_range', [0, 0]),
            'data_points': analysis_data.get('data_points', 0),
            'noise_level': analysis_data.get('noise_level', 0),
            'signal_to_noise_ratio': analysis_data.get('signal_to_noise_ratio', 0),
            'shift_detected': analysis_data.get('shift_detected'),
            'preprocessing_steps': analysis_data.get('preprocessing_steps', []),
            'parameter_recommendations': analysis_data.get('parameter_recommendations', []),
            'wavelengths': analysis_data.get('wavelengths', []),
            'intensities': analysis_data.get('intensities', []),
            'analysis_timestamp': datetime.now().isoformat(),
        }
        
        return self.render_report(
            template_name='spectral_analysis',
            output_filename=output_filename,
            data=quarto_data,
            format='html'
        )

    def render_metadata_report(self, metadata_data, output_filename=None):
        """
        Render a metadata quality report.
        
        Args:
            metadata_data (dict): Metadata analysis data
            output_filename (str, optional): Output filename. Defaults to None.
            
        Returns:
            tuple: (success: bool, output_path: str or None, error: str or None)
        """
        quarto_data = {
            'sample_id': metadata_data.get('sample_id', 'Unknown'),
            'metadata_quality_score': metadata_data.get('quality_score', 0),
            'metadata_grade': metadata_data.get('quality_grade', 'unknown'),
            'missing_fields': metadata_data.get('missing_fields', []),
            'quality_issues': metadata_data.get('quality_issues', []),
            'recommendations': metadata_data.get('recommendations', []),
            'standards_compliance': metadata_data.get('standards_compliance', {}),
            'analysis_timestamp': datetime.now().isoformat(),
        }
        
        return self.render_report(
            template_name='metadata_quality',
            output_filename=output_filename,
            data=quarto_data,
            format='html'
        )

    def get_available_templates(self):
        """Get list of available Quarto templates."""
        templates = []
        if self.reports_dir.exists():
            for file in self.reports_dir.glob('*.qmd'):
                templates.append(file.stem)
        return templates

    def create_report_url(self, output_path):
        """Create a URL for accessing the rendered report."""
        if output_path:
            relative_path = os.path.relpath(output_path, settings.STATIC_ROOT)
            return f"/static/reports/{os.path.basename(output_path)}"
        return None


# Singleton instance
quarto_renderer = QuartoRenderer()