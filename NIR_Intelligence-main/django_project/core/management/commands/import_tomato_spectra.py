"""
Django management command to import tomato spectra from T4-T5_ALLE_mit_Brix_2.txt file
"""

import os
import sys
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import User, NIRSpectrum
from django.utils import timezone
import json
import uuid

# Add the data directory to the path so we can import the parser
sys.path.append('/home/martin/Development/vsCode_Environment/NIR_Mistral/data/raw')
from parse_spectra_file import SpectraFileParser


class Command(BaseCommand):
    help = 'Import tomato spectra from T4-T5_ALLE_mit_Brix_2.txt file'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='/home/martin/Development/vsCode_Environment/NIR_Mistral/data/raw/T4-T5_ALLE_mit_Brix_2.txt',
            help='Path to the spectra file to import'
        )
        parser.add_argument(
            '--user',
            type=str,
            default='admin',
            help='Username to assign the spectra to (default: admin)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without actually importing data'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of spectra to import (for testing)'
        )
    
    def handle(self, *args, **options):
        file_path = options['file']
        username = options['user']
        dry_run = options['dry_run']
        limit = options['limit']
        
        self.stdout.write(self.style.SUCCESS(f'Starting import from: {file_path}'))
        
        # Check if file exists
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return
        
        # Get or create user
        try:
            user = User.objects.get(username=username)
            self.stdout.write(self.style.SUCCESS(f'Using user: {username}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User not found: {username}'))
            return
        
        # Parse the file
        self.stdout.write(self.style.SUCCESS('Parsing spectra file...'))
        parser = SpectraFileParser(file_path)
        parser.parse()
        
        summary = parser.get_summary()
        self.stdout.write(self.style.SUCCESS(f'Found {summary["total_spectra"]} spectra'))
        self.stdout.write(self.style.SUCCESS(f'Wavelength range: {summary["experiment_metadata"]["wavelength_range_nm"]} nm'))
        
        # Prepare spectra for import
        spectra_to_import = parser.spectral_data
        if limit:
            spectra_to_import = spectra_to_import[:limit]
            self.stdout.write(self.style.SUCCESS(f'Limiting to {limit} spectra for testing'))
        
        # Group spectra by tomato for batch import
        spectra_by_tomato = {}
        for spectrum in spectra_to_import:
            tomato_id = spectrum.tomate
            if tomato_id not in spectra_by_tomato:
                spectra_by_tomato[tomato_id] = []
            spectra_by_tomato[tomato_id].append(spectrum)
        
        self.stdout.write(self.style.SUCCESS(f'Found {len(spectra_by_tomato)} unique tomatoes'))
        
        # Import each tomato's spectra as a single NIRSpectrum
        imported_count = 0
        skipped_count = 0
        
        for tomato_id, tomato_spectra in spectra_by_tomato.items():
            # Create a name for this spectrum
            name = f"Tomato {tomato_id} - NIR Spectra"
            description = f"NIR spectra for tomato {tomato_id} from T4-T5 experiment"
            
            # Extract metadata from first spectrum
            first_spectrum = tomato_spectra[0]
            
            # Create collection conditions
            collection_conditions = {
                'experiment': 'Tomaten Reifegradbestimmung',
                'device': 'Dpark fun NIR Triad',
                'environment': 'Darkened and air-conditioned at 22°C',
                'students': ['Leonhard', 'Samuel', 'Frederik', 'Luzia'],
                'calibration_method': 'Refractometer',
                'measurement_target': 'Tomato ripeness',
                'brix_values': [s.brix for s in tomato_spectra],
                'temperatures': {
                    'temp0': [s.temp0 for s in tomato_spectra],
                    'temp1': [s.temp1 for s in tomato_spectra],
                    'temp2': [s.temp2 for s in tomato_spectra]
                },
                'original_file': 'T4-T5_ALLE_mit_Brix_2.txt',
                'tomato_id': tomato_id,
                'rispe': first_spectrum.rispe,
                'reihe': first_spectrum.reihe,
                'tag': first_spectrum.tag
            }
            
            # Create spectral data JSON
            spectral_data = {
                'wavelengths': list(parser.wavelength_columns),
                'intensities': [],
                'metadata': []
            }
            
            # Average intensities across all measurements for this tomato
            num_spectra = len(tomato_spectra)
            num_wavelengths = len(parser.wavelength_columns)
            
            # Initialize sums for averaging
            intensity_sums = {wl: 0.0 for wl in parser.wavelength_columns}
            
            for spectrum in tomato_spectra:
                for wl, intensity in spectrum.wavelengths.items():
                    intensity_sums[wl] += intensity
                
                # Store individual spectrum metadata
                spectral_data['metadata'].append({
                    'counter': spectrum.counter,
                    'messobjekt': spectrum.messobjekt,
                    'kurz': spectrum.kurz,
                    'brix': spectrum.brix,
                    'temperatures': {
                        'temp0': spectrum.temp0,
                        'temp1': spectrum.temp1,
                        'temp2': spectrum.temp2
                    }
                })
            
            # Calculate averages
            averaged_intensities = []
            for wl in parser.wavelength_columns:
                avg_intensity = intensity_sums[wl] / num_spectra
                averaged_intensities.append(avg_intensity)
            
            spectral_data['intensities'] = averaged_intensities
            
            # Create the NIRSpectrum object
            spectrum_obj = NIRSpectrum(
                id=uuid.uuid4(),
                user=user,
                name=name,
                description=description,
                sample_id=tomato_id,
                sample_type='Tomato',
                sample_source=f'T4-T5 Experiment - {tomato_id}',
                spectral_type='absorbance',  # Assuming these are absorbance values
                data_format='txt',
                wavelength_range_start=410.0,
                wavelength_range_end=940.0,
                resolution=25.0,  # Approximate resolution between wavelengths
                data_points=num_wavelengths,
                instrument='Dpark fun NIR Triad',
                collection_date=timezone.now(),
                collection_conditions=collection_conditions,
                mean_absorbance=sum(averaged_intensities) / len(averaged_intensities),
                max_absorbance=max(averaged_intensities),
                min_absorbance=min(averaged_intensities),
                peaks_detected=0,  # Will be calculated later
                signal_to_noise_ratio=0.0,  # Will be calculated later
                baseline_corrected=False,
                quality_score=0.8,  # Default quality score
                status='uploaded'
            )
            
            if not dry_run:
                # Save the spectrum
                spectrum_obj.save()
                
                # Save spectral data as JSON in processed_file or as metadata
                # For now, we'll store it in the collection_conditions
                spectrum_obj.collection_conditions['spectral_data'] = spectral_data
                spectrum_obj.save()
                
                imported_count += 1
                self.stdout.write(self.style.SUCCESS(f'Imported spectrum for {tomato_id}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'[DRY RUN] Would import spectrum for {tomato_id}'))
                imported_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'\nImport complete!'))
        self.stdout.write(self.style.SUCCESS(f'Total spectra processed: {imported_count}'))
        self.stdout.write(self.style.SUCCESS(f'Spectra skipped: {skipped_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run completed - no data was actually imported'))
        else:
            self.stdout.write(self.style.SUCCESS('Data has been imported successfully'))
        
        # Also save the raw parsed data as JSON for reference
        if not dry_run:
            json_path = os.path.join(
                settings.MEDIA_ROOT, 
                'spectra', 
                'imported', 
                't4_t5_tomato_spectra_metadata.json'
            )
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            export_data = {
                'import_date': timezone.now().isoformat(),
                'user': username,
                'source_file': file_path,
                'total_spectra': len(spectra_to_import),
                'tomatoes_imported': list(spectra_by_tomato.keys()),
                'experiment_metadata': summary['experiment_metadata']
            }
            
            with open(json_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            self.stdout.write(self.style.SUCCESS(f'Metadata saved to: {json_path}'))