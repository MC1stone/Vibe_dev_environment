#!/usr/bin/env python3
"""
NIR_Mistral Framework - Test Environment Setup Script

This script automates the setup of the NIR_TEST environment and integrates it
with the Django frontend for a complete demonstration system.
"""

import os
import sys
import subprocess
import shutil
import yaml
import json
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add NIR_TEST to the path
nir_test_path = project_root / "NIR_TEST"
if str(nir_test_path) not in sys.path:
    sys.path.insert(0, str(nir_test_path))

def print_header():
    """Print the setup header"""
    print("""
    ============================================================
    NIR_MISTRAL FRAMEWORK - TEST ENVIRONMENT SETUP
    ============================================================
    
    This script will:
    1. Setup the NIR_TEST environment with test data
    2. Configure the Django project for test environment integration
    3. Create test users and permissions
    4. Register test agents with the framework
    5. Verify the complete setup
    
    ============================================================
    """)

def check_prerequisites():
    """Check that all prerequisites are installed"""
    print("Checking prerequisites...")
    
    required_commands = [
        ('python', 'python3 --version'),
        ('pip', 'pip3 --version'),
        ('django-admin', 'django-admin --version'),
    ]
    
    missing = []
    for name, command in required_commands:
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                missing.append(name)
            else:
                print(f"  ✓ {name}: {result.stdout.strip()}")
        except Exception as e:
            missing.append(name)
            print(f"  ✗ {name}: Not found")
    
    if missing:
        print(f"\n✗ Missing prerequisites: {', '.join(missing)}")
        print("Please install the missing prerequisites and try again.")
        return False
    
    print("✓ All prerequisites are installed")
    return True

def setup_nir_test_environment():
    """Setup the NIR_TEST environment with test data"""
    print("\nSetting up NIR_TEST environment...")
    
    # Check if NIR_TEST directory exists
    if not nir_test_path.exists():
        print("✗ NIR_TEST directory not found")
        return False
    
    # Create directory structure
    directories = [
        "data/raw", "data/processed", "data/results",
        "config", "scripts", "output", "logs", "agents", "models"
    ]
    
    for directory in directories:
        full_path = nir_test_path / directory
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created directory: {directory}")
    
    # Create test data files if they don't exist
    test_data_path = nir_test_path / "data" / "raw"
    test_files = {
        "nir_spectrum_001.txt": """# NIR Spectrum Data - Wheat Flour
# Wavelength (nm), Absorbance
700,0.250
702,0.255
704,0.260
706,0.265
708,0.270
710,0.275
712,0.280
714,0.285
716,0.290
718,0.295
720,0.300
840,0.950
842,0.955
844,0.960
846,0.965
848,0.970
850,0.975
1040,1.050
1042,1.055
1044,1.060
1046,1.065
1048,1.070
1050,1.075
1200,1.250
1202,1.255
1204,1.260
1206,1.265
1208,1.270
1210,1.275
1420,1.250
1422,1.255
1424,1.260
1426,1.265
1428,1.270
1430,1.275
1900,2.160
1902,2.155
1904,2.150
1906,2.145
1908,2.140
1910,2.135
2500,1.800""",
        
        "nir_spectrum_002.txt": """# NIR Spectrum Data - Corn Meal
# Wavelength (nm), Reflectance
700,0.350
702,0.355
704,0.360
706,0.365
708,0.370
710,0.375
712,0.380
714,0.385
716,0.390
718,0.395
720,0.400
840,1.050
842,1.055
844,1.060
846,1.065
848,1.070
850,1.075
1040,1.150
1042,1.155
1044,1.160
1046,1.165
1048,1.170
1050,1.175
1440,2.050
1442,2.045
1444,2.040
1446,2.035
1448,2.030
1450,2.025
1900,1.650
1902,1.645
1904,1.640
1906,1.635
1908,1.630
1910,1.625
2500,1.400""",
        
        "metadata.txt": """# Metadata for NIR Test Spectra
# Format: SampleID,SampleName,Type,Description
001,Wheat Flour,absorbance,High-quality wheat flour sample
002,Corn Meal,reflectance,Yellow corn meal sample"""
    }
    
    for filename, content in test_files.items():
        file_path = test_data_path / filename
        if not file_path.exists():
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"  ✓ Created test file: {filename}")
        else:
            print(f"  ✓ Test file exists: {filename}")
    
    # Create configuration file
    config_path = nir_test_path / "config" / "test_config.yaml"
    if not config_path.exists():
        config_data = {
            'environment': {
                'name': 'NIR_TEST',
                'description': 'NIR_Mistral DeveloperAgent Framework Test Environment',
                'version': '1.0.0'
            },
            'paths': {
                'root': str(nir_test_path),
                'raw_data': '${root}/data/raw',
                'processed_data': '${root}/data/processed',
                'results': '${root}/data/results',
                'output': '${root}/output',
                'logs': '${root}/logs',
                'agents': '${root}/agents',
                'models': '${root}/models',
                'config': '${root}/config'
            },
            'test_data': {
                'samples': [
                    {
                        'id': '001',
                        'name': 'Wheat Flour',
                        'file': 'nir_spectrum_001.txt',
                        'type': 'absorbance',
                        'expected_properties': {
                            'wavelength_range': [700, 2500],
                            'resolution': 2,
                            'signal_range': [0.2, 2.5]
                        }
                    },
                    {
                        'id': '002',
                        'name': 'Corn Meal',
                        'file': 'nir_spectrum_002.txt',
                        'type': 'reflectance',
                        'expected_properties': {
                            'wavelength_range': [700, 2500],
                            'resolution': 2,
                            'signal_range': [0.3, 2.5]
                        }
                    }
                ]
            },
            'nir_settings': {
                'wavelength_range': [700, 2500],
                'resolution': 2,
                'min_signal': 0.0,
                'max_signal': 3.0
            },
            'data_processing': {
                'delimiter': ',',
                'skip_rows': 2,
                'wavelength_column': 0,
                'value_column': 1
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'log_file': '${logs}/nir_test_agent.log'
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        print(f"  ✓ Created configuration file: test_config.yaml")
    else:
        print(f"  ✓ Configuration file exists: test_config.yaml")
    
    return True

def configure_django_project():
    """Configure the Django project for test environment integration"""
    print("\nConfiguring Django project...")
    
    django_project_path = project_root / "django_project"
    
    # Check if Django project exists
    if not (django_project_path / "manage.py").exists():
        print("✗ Django project not found")
        return False
    
    # Create settings for test environment integration
    settings_path = django_project_path / "nir_web" / "settings.py"
    
    # Add NIR_TEST configuration to Django settings
    nir_test_config = f"""
# NIR_TEST Environment Configuration
NIR_TEST_PATH = '{nir_test_path}'
NIR_TEST_DATA_PATH = os.path.join(NIR_TEST_PATH, 'data')
NIR_TEST_OUTPUT_PATH = os.path.join(NIR_TEST_PATH, 'output')
NIR_TEST_AGENTS_PATH = os.path.join(NIR_TEST_PATH, 'agents')

# Add NIR_TEST paths to Python path
sys.path.insert(0, NIR_TEST_PATH)
sys.path.insert(0, NIR_TEST_AGENTS_PATH)

# Test environment flag
NIR_TEST_ENVIRONMENT = True
"""
    
    # Read current settings
    with open(settings_path, 'r') as f:
        settings_content = f.read()
    
    # Add NIR_TEST configuration if not already present
    if 'NIR_TEST_PATH' not in settings_content:
        # Find the end of the file and add before the last line if it's not empty
        if settings_content.strip():
            settings_content = settings_content.rstrip() + '\n\n' + nir_test_config
        else:
            settings_content = nir_test_config
        
        with open(settings_path, 'w') as f:
            f.write(settings_content)
        
        print("  ✓ Added NIR_TEST configuration to Django settings")
    else:
        print("  ✓ NIR_TEST configuration already exists in Django settings")
    
    return True

def create_test_users():
    """Create test users for the Django project"""
    print("\nCreating test users...")
    
    django_project_path = project_root / "django_project"
    
    # Change to Django project directory
    original_cwd = os.getcwd()
    os.chdir(django_project_path)
    
    try:
        # Import Django and set up
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
        django.setup()
        
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Permission
        from core.models import UserProfile
        
        User = get_user_model()
        
        # Test users to create
        test_users = [
            {
                'username': 'admin',
                'email': 'admin@nir-mistral.local',
                'password': 'admin123',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_superuser': True,
                'is_staff': True,
                'is_active': True
            },
            {
                'username': 'testuser',
                'email': 'testuser@nir-mistral.local',
                'password': 'testuser123',
                'first_name': 'Test',
                'last_name': 'User',
                'is_superuser': False,
                'is_staff': False,
                'is_active': True
            },
            {
                'username': 'researcher',
                'email': 'researcher@nir-mistral.local',
                'password': 'researcher123',
                'first_name': 'Research',
                'last_name': 'Scientist',
                'is_superuser': False,
                'is_staff': True,
                'is_active': True
            }
        ]
        
        for user_data in test_users:
            username = user_data['username']
            
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                print(f"  ✓ User already exists: {username}")
                continue
            
            # Create user
            user = User.objects.create_user(
                username=username,
                email=user_data['email'],
                password=user_data['password'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                is_superuser=user_data['is_superuser'],
                is_staff=user_data['is_staff'],
                is_active=user_data['is_active']
            )
            
            # Create user profile
            UserProfile.objects.create(
                user=user,
                organization='NIR Research Institute',
                department='Spectroscopy',
                bio=f'Test user for NIR_Mistral framework',
                theme_preference='light',
                language_preference='en'
            )
            
            print(f"  ✓ Created user: {username}")
        
        print("✓ Test users created successfully")
        
    except Exception as e:
        print(f"✗ Error creating test users: {e}")
        return False
    finally:
        os.chdir(original_cwd)
    
    return True

def register_test_agents():
    """Register test agents with the Django framework"""
    print("\nRegistering test agents...")
    
    django_project_path = project_root / "django_project"
    
    # Change to Django project directory
    original_cwd = os.getcwd()
    os.chdir(django_project_path)
    
    try:
        # Import Django and set up
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
        django.setup()
        
        from core.models import Agent
        
        # Test agents to register
        test_agents = [
            {
                'name': 'NIR_Test_Agent',
                'version': '1.0.0',
                'description': 'Test agent for NIR spectroscopy analysis in the NIR_TEST environment',
                'author': 'NIR_Mistral Team',
                'analysis_types': ['peak_detection', 'quality_control', 'statistical_analysis'],
                'is_active': True,
                'is_system_agent': True,
                'module_path': 'agents.nir_test_agent.NIRTestAgent',
                'config_path': str(nir_test_path / 'config' / 'test_config.yaml')
            },
            {
                'name': 'Peak_Detector',
                'version': '1.0.0',
                'description': 'Agent for detecting peaks in NIR spectra',
                'author': 'NIR_Mistral Team',
                'analysis_types': ['peak_detection'],
                'is_active': True,
                'is_system_agent': True,
                'module_path': 'agents.peak_detector.PeakDetectorAgent',
                'config_path': str(nir_test_path / 'config' / 'peak_config.yaml')
            },
            {
                'name': 'Quality_Validator',
                'version': '1.0.0',
                'description': 'Agent for validating NIR data quality',
                'author': 'NIR_Mistral Team',
                'analysis_types': ['quality_control'],
                'is_active': True,
                'is_system_agent': True,
                'module_path': 'agents.quality_validator.QualityValidatorAgent',
                'config_path': str(nir_test_path / 'config' / 'quality_config.yaml')
            },
            {
                'name': 'Statistical_Analyzer',
                'version': '1.0.0',
                'description': 'Agent for statistical analysis of NIR spectra',
                'author': 'NIR_Mistral Team',
                'analysis_types': ['statistical_analysis'],
                'is_active': True,
                'is_system_agent': True,
                'module_path': 'agents.statistical_analyzer.StatisticalAnalyzerAgent',
                'config_path': str(nir_test_path / 'config' / 'statistical_config.yaml')
            }
        ]
        
        for agent_data in test_agents:
            name = agent_data['name']
            
            # Check if agent already exists
            if Agent.objects.filter(name=name).exists():
                print(f"  ✓ Agent already registered: {name}")
                continue
            
            # Create agent
            Agent.objects.create(**agent_data)
            print(f"  ✓ Registered agent: {name}")
        
        print("✓ Test agents registered successfully")
        
    except Exception as e:
        print(f"✗ Error registering test agents: {e}")
        return False
    finally:
        os.chdir(original_cwd)
    
    return True

def load_test_data():
    """Load test data into the Django database"""
    print("\nLoading test data...")
    
    django_project_path = project_root / "django_project"
    
    # Change to Django project directory
    original_cwd = os.getcwd()
    os.chdir(django_project_path)
    
    try:
        # Import Django and set up
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
        django.setup()
        
        from core.models import NIRSpectrum
        import numpy as np
        
        # Test spectra to load
        test_spectra = [
            {
                'sample_id': '001',
                'sample_name': 'Wheat Flour',
                'spectral_type': 'absorbance',
                'description': 'High-quality wheat flour sample for testing',
                'metadata': {
                    'instrument': 'NIR-1000',
                    'temperature': 25.0,
                    'humidity': 50.0,
                    'measurement_date': '2026-08-03'
                },
                'wavelengths': list(range(700, 2501, 2)),
                'values': [0.250 + 0.005 * i + (0.950 if 840 <= 700 + 2*i <= 850 else 0) + 
                          (1.050 if 1040 <= 700 + 2*i <= 1050 else 0) + 
                          (1.250 if 1200 <= 700 + 2*i <= 1210 else 0) + 
                          (1.250 if 1420 <= 700 + 2*i <= 1430 else 0) + 
                          (2.160 if 1900 <= 700 + 2*i <= 1910 else 0) 
                          for i in range(len(range(700, 2501, 2)))]
            },
            {
                'sample_id': '002',
                'sample_name': 'Corn Meal',
                'spectral_type': 'reflectance',
                'description': 'Yellow corn meal sample for testing',
                'metadata': {
                    'instrument': 'NIR-1000',
                    'temperature': 25.0,
                    'humidity': 50.0,
                    'measurement_date': '2026-08-03'
                },
                'wavelengths': list(range(700, 2501, 2)),
                'values': [0.350 + 0.005 * i + (1.050 if 840 <= 700 + 2*i <= 850 else 0) + 
                          (1.150 if 1040 <= 700 + 2*i <= 1050 else 0) + 
                          (2.050 if 1440 <= 700 + 2*i <= 1450 else 0) + 
                          (1.650 if 1900 <= 700 + 2*i <= 1910 else 0) 
                          for i in range(len(range(700, 2501, 2)))]
            }
        ]
        
        for spectrum_data in test_spectra:
            sample_id = spectrum_data['sample_id']
            
            # Check if spectrum already exists
            if NIRSpectrum.objects.filter(sample_id=sample_id).exists():
                print(f"  ✓ Spectrum already loaded: {sample_id}")
                continue
            
            # Create spectrum
            spectrum = NIRSpectrum.objects.create(
                sample_id=sample_id,
                sample_name=spectrum_data['sample_name'],
                spectral_type=spectrum_data['spectral_type'],
                description=spectrum_data['description'],
                metadata=spectrum_data['metadata'],
                wavelength_range=f"{min(spectrum_data['wavelengths'])}-{max(spectrum_data['wavelengths'])} nm",
                data_points=len(spectrum_data['wavelengths']),
                wavelengths=spectrum_data['wavelengths'],
                values=spectrum_data['values']
            )
            
            # Calculate and save basic statistics
            spectrum.mean_absorbance = float(np.mean(spectrum_data['values']))
            spectrum.max_absorbance = float(np.max(spectrum_data['values']))
            spectrum.min_absorbance = float(np.min(spectrum_data['values']))
            spectrum.save()
            
            print(f"  ✓ Loaded spectrum: {sample_id}")
        
        print("✓ Test data loaded successfully")
        
    except Exception as e:
        print(f"✗ Error loading test data: {e}")
        return False
    finally:
        os.chdir(original_cwd)
    
    return True

def verify_setup():
    """Verify the complete setup"""
    print("\nVerifying setup...")
    
    django_project_path = project_root / "django_project"
    
    # Change to Django project directory
    original_cwd = os.getcwd()
    os.chdir(django_project_path)
    
    try:
        # Import Django and set up
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
        django.setup()
        
        from django.contrib.auth import get_user_model
        from core.models import NIRSpectrum, Agent, AnalysisJob
        
        User = get_user_model()
        
        # Check users
        user_count = User.objects.count()
        print(f"  ✓ Users: {user_count}")
        
        # Check agents
        agent_count = Agent.objects.count()
        print(f"  ✓ Agents: {agent_count}")
        
        # Check spectra
        spectrum_count = NIRSpectrum.objects.count()
        print(f"  ✓ Spectra: {spectrum_count}")
        
        # Check jobs
        job_count = AnalysisJob.objects.count()
        print(f"  ✓ Analysis Jobs: {job_count}")
        
        # Check NIR_TEST files
        test_files = [
            nir_test_path / "data" / "raw" / "nir_spectrum_001.txt",
            nir_test_path / "data" / "raw" / "nir_spectrum_002.txt",
            nir_test_path / "config" / "test_config.yaml"
        ]
        
        for file_path in test_files:
            if file_path.exists():
                print(f"  ✓ Test file exists: {file_path.name}")
            else:
                print(f"  ✗ Test file missing: {file_path.name}")
        
        print("\n✓ Setup verification completed")
        
    except Exception as e:
        print(f"✗ Error during verification: {e}")
        return False
    finally:
        os.chdir(original_cwd)
    
    return True

def run_demonstration():
    """Run a demonstration of the test environment"""
    print("\nRunning demonstration...")
    
    django_project_path = project_root / "django_project"
    
    # Change to Django project directory
    original_cwd = os.getcwd()
    os.chdir(django_project_path)
    
    try:
        # Import Django and set up
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
        django.setup()
        
        # Import and run the test agent
        from agents.nir_test_agent import NIRTestAgent
        
        agent = NIRTestAgent()
        
        print("  Running NIR Test Agent demonstration...")
        
        # Run the demonstration
        success = agent.run_demonstration()
        
        if success:
            print("  ✓ Demonstration completed successfully")
        else:
            print("  ✗ Demonstration failed")
            return False
        
    except ImportError as e:
        print(f"  ✗ Error importing test agent: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error during demonstration: {e}")
        return False
    finally:
        os.chdir(original_cwd)
    
    return True

def main():
    """Main setup function"""
    print_header()
    
    if not check_prerequisites():
        sys.exit(1)
    
    # Run setup steps
    steps = [
        ("NIR_TEST Environment", setup_nir_test_environment),
        ("Django Configuration", configure_django_project),
        ("Test Users", create_test_users),
        ("Test Agents", register_test_agents),
        ("Test Data", load_test_data),
        ("Verification", verify_setup)
    ]
    
    for step_name, step_function in steps:
        print(f"\n{'='*50}")
        print(f"Step: {step_name}")
        print('='*50)
        
        if not step_function():
            print(f"✗ {step_name} failed")
            if input("Continue anyway? (y/n): ").lower() != 'y':
                sys.exit(1)
    
    # Run demonstration
    if input("\nRun demonstration? (y/n): ").lower() == 'y':
        if not run_demonstration():
            print("✗ Demonstration failed")
    
    print("\n" + "="*60)
    print("NIR_MISTRAL FRAMEWORK - TEST ENVIRONMENT SETUP COMPLETED")
    print("="*60)
    print("\nNext steps:")
    print("1. Start the Django development server:")
    print("   cd django_project")
    print("   python manage.py runserver")
    print("2. Access the web interface at: http://localhost:8000")
    print("3. Log in with test users:")
    print("   - admin/admin123 (superuser)")
    print("   - testuser/testuser123 (regular user)")
    print("   - researcher/researcher123 (staff user)")
    print("\nThe NIR_TEST environment is now fully integrated with the Django frontend!")

if __name__ == "__main__":
    main()