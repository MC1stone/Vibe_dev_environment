# NIR_Mistral Django Management Command
# Command for rendering Quarto reports

from django.core.management.base import BaseCommand
from django.conf import settings
from core.utils.quarto_renderer import quarto_renderer
import json
import os


class Command(BaseCommand):
    help = 'Render Quarto reports for spectral analysis'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--template',
            type=str,
            default='spectral_analysis',
            help='Quarto template name (without .qmd extension)'
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Output filename (without extension)'
        )
        parser.add_argument(
            '--format',
            type=str,
            default='html',
            choices=['html', 'pdf', 'docx'],
            help='Output format'
        )
        parser.add_argument(
            '--data',
            type=str,
            default=None,
            help='JSON data to pass to the template'
        )
        parser.add_argument(
            '--data-file',
            type=str,
            default=None,
            help='JSON file containing data for the template'
        )
        parser.add_argument(
            '--list-templates',
            action='store_true',
            help='List available Quarto templates'
        )
        parser.add_argument(
            '--check',
            action='store_true',
            help='Check Quarto installation'
        )

    def handle(self, *args, **options):
        if options['list_templates']:
            self.list_templates()
            return
        
        if options['check']:
            self.check_quarto()
            return
        
        # Load data
        data = {}
        if options['data']:
            try:
                data = json.loads(options['data'])
            except json.JSONDecodeError as e:
                self.stderr.write(f"Error parsing JSON data: {e}")
                return
        
        if options['data_file']:
            try:
                with open(options['data_file'], 'r') as f:
                    data = json.load(f)
            except FileNotFoundError:
                self.stderr.write(f"Data file not found: {options['data_file']}")
                return
            except json.JSONDecodeError as e:
                self.stderr.write(f"Error parsing JSON file: {e}")
                return
        
        # Render the report
        success, output_path, error = quarto_renderer.render_report(
            template_name=options['template'],
            output_filename=options['output'],
            data=data,
            format=options['format']
        )
        
        if success:
            self.stdout.write(f"Successfully rendered report: {output_path}")
            
            # Create URL for web access
            if output_path:
                url = quarto_renderer.create_report_url(output_path)
                if url:
                    self.stdout.write(f"Access the report at: {url}")
        else:
            self.stderr.write(f"Error rendering report: {error}")

    def list_templates(self):
        templates = quarto_renderer.get_available_templates()
        if templates:
            self.stdout.write("Available Quarto templates:")
            for template in templates:
                self.stdout.write(f"  - {template}")
        else:
            self.stdout.write("No Quarto templates found")

    def check_quarto(self):
        installed, version = quarto_renderer.check_quarto_installation()
        if installed:
            self.stdout.write(f"Quarto is installed: {version}")
            self.stdout.write(f"Quarto path: {quarto_renderer.quarto_path}")
            self.stdout.write(f"Reports directory: {quarto_renderer.reports_dir}")
            self.stdout.write(f"Output directory: {quarto_renderer.output_dir}")
            self.stdout.write(f"Quarto enabled: {quarto_renderer.enabled}")
        else:
            self.stderr.write(f"Quarto is not properly installed: {version}")