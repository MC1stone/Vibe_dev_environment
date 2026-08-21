#!/usr/bin/env python3
"""
NIR_TEST Environment Main Script

This script provides a comprehensive interface to the NIR_TEST environment
and demonstrates the functionality of the NIR_Mistral DeveloperAgent Framework.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Add the NIR_TEST directory to the path FIRST
nir_test_path = os.path.dirname(os.path.abspath(__file__))
if nir_test_path not in sys.path:
    sys.path.insert(0, nir_test_path)

# Add the NIR_TEST agents directory to the path explicitly
agents_path = os.path.join(nir_test_path, "agents")
if agents_path not in sys.path:
    sys.path.insert(0, agents_path)

# Add the main framework to the path AFTER NIR_TEST
framework_path = "/home/martin/Development/vsCode_Environment/NIR_Mistral"
if framework_path not in sys.path:
    sys.path.append(framework_path)

def print_header():
    """Print the NIR_TEST environment header"""
    print("""
    ============================================================
    NIR_MISTRAL DEVELOPERAGENT FRAMEWORK - TEST ENVIRONMENT
    ============================================================
    
    Welcome to the NIR_TEST environment!
    This environment demonstrates the functionality of the NIR_Mistral
    DeveloperAgent Framework using realistic NIR spectroscopy test data.
    
    Available Commands:
    - setup: Setup the test environment
    - run: Run the complete demonstration
    - test: Run specific tests
    - analyze: Analyze test data
    - validate: Validate data quality
    - report: Generate test reports
    - info: Show environment information
    - clean: Clean up test files
    
    ============================================================
    """)

def print_environment_info():
    """Print information about the test environment"""
    print("NIR_TEST Environment Information")
    print("=" * 50)
    
    # Check directory structure
    base_path = "/home/martin/Development/vsCode_Environment/NIR_Mistral/NIR_TEST"
    
    directories = [
        "data/raw",
        "data/processed", 
        "data/results",
        "config",
        "scripts",
        "output",
        "logs",
        "agents",
        "models"
    ]
    
    print("Directory Structure:")
    for directory in directories:
        full_path = os.path.join(base_path, directory)
        exists = "✓" if os.path.exists(full_path) else "✗"
        print(f"  {exists} {directory}")
    
    # Check test data files
    raw_data_path = os.path.join(base_path, "data", "raw")
    if os.path.exists(raw_data_path):
        files = [f for f in os.listdir(raw_data_path) if f.endswith('.txt')]
        print(f"\nTest Data Files ({len(files)}):")
        for file in files:
            file_path = os.path.join(raw_data_path, file)
            size = os.path.getsize(file_path)
            print(f"  - {file} ({size} bytes)")
    
    # Check configuration
    config_path = os.path.join(base_path, "config", "test_config.yaml")
    if os.path.exists(config_path):
        print(f"\nConfiguration: ✓ test_config.yaml found")
    else:
        print(f"\nConfiguration: ✗ test_config.yaml not found")
    
    # Check agents
    agents_path = os.path.join(base_path, "agents")
    if os.path.exists(agents_path):
        agents = [f for f in os.listdir(agents_path) if f.endswith('.py')]
        print(f"Agents: {len(agents)} available")
        for agent in agents:
            print(f"  - {agent}")

def setup_environment():
    """Setup the test environment"""
    print("Setting up NIR_TEST environment...")
    
    base_path = "/home/martin/Development/vsCode_Environment/NIR_Mistral/NIR_TEST"
    
    # Create directory structure
    directories = [
        "data/raw",
        "data/processed",
        "data/results", 
        "config",
        "scripts",
        "output",
        "logs",
        "agents",
        "models"
    ]
    
    for directory in directories:
        full_path = os.path.join(base_path, directory)
        os.makedirs(full_path, exist_ok=True)
        print(f"  ✓ Created: {directory}")
    
    # Check if test data exists
    raw_data_path = os.path.join(base_path, "data", "raw")
    test_files = [
        "nir_spectrum_001.txt",
        "nir_spectrum_002.txt", 
        "metadata.txt"
    ]
    
    print("\nChecking test data files:")
    for file in test_files:
        file_path = os.path.join(raw_data_path, file)
        if os.path.exists(file_path):
            print(f"  ✓ {file} exists")
        else:
            print(f"  ✗ {file} missing")
    
    # Check configuration
    config_path = os.path.join(base_path, "config", "test_config.yaml")
    if os.path.exists(config_path):
        print(f"  ✓ Configuration file exists")
    else:
        print(f"  ✗ Configuration file missing")
    
    print("\nEnvironment setup completed!")

def run_demonstration():
    """Run the complete demonstration"""
    print("Running NIR_TEST Environment Demonstration...")
    print("=" * 60)
    
    try:
        # Import and run the test agent from NIR_TEST directory
        import agents.nir_test_agent
        NIRTestAgent = agents.nir_test_agent.NIRTestAgent
        
        # Create the agent
        agent = NIRTestAgent()
        
        # Run the demonstration
        success = agent.run_demonstration()
        
        if success:
            print("\n✓ Demonstration completed successfully!")
            return True
        else:
            print("\n✗ Demonstration failed!")
            return False
            
    except ImportError as e:
        print(f"✗ Error importing test agent: {e}")
        return False
    except Exception as e:
        print(f"✗ Error during demonstration: {e}")
        return False

def run_specific_test(test_name: str):
    """Run a specific test"""
    print(f"Running specific test: {test_name}")
    
    try:
        import agents.nir_test_agent
        NIRTestAgent = agents.nir_test_agent.NIRTestAgent
        
        agent = NIRTestAgent()
        
        if test_name == "load_data":
            success = agent.load_test_data()
            if success:
                print(f"✓ Successfully loaded {len(agent.spectra)} spectra")
                for sample_id, spectrum in agent.spectra.items():
                    print(f"  - {spectrum.sample_name}: {len(spectrum.wavelengths)} data points")
            else:
                print("✗ Failed to load test data")
                
        elif test_name == "analyze":
            results = agent.analyze_spectra()
            print(f"✓ Analyzed {len(results)} spectra")
            for sample_id, result in results.items():
                print(f"  - {result['sample_name']}: Mean={result['mean_absorbance']:.3f}, Peaks={len(result['peaks'])}")
                
        elif test_name == "validate":
            quality_report = agent.validate_data_quality()
            print(f"✓ Validated {len(quality_report)} spectra")
            for sample_id, quality in quality_report.items():
                status = "PASS" if quality['overall_quality'] else "FAIL"
                print(f"  - {quality['sample_name']}: {status}")
                
        elif test_name == "report":
            report = agent.generate_report()
            print("✓ Report generated successfully")
            print("Report content preview:")
            lines = report.split('\n')
            for line in lines[:20]:  # Show first 20 lines
                print(f"  {line}")
            if len(lines) > 20:
                print(f"  ... ({len(lines) - 20} more lines)")
                
        else:
            print(f"✗ Unknown test: {test_name}")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ Error running test {test_name}: {e}")
        return False

def install_dependencies():
    """Install required dependencies"""
    print("Installing NIR_TEST environment dependencies...")
    
    requirements_file = os.path.join(nir_test_path, "requirements.txt")
    
    if not os.path.exists(requirements_file):
        print("✗ requirements.txt not found")
        return False
    
    try:
        # Use pip to install requirements
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", requirements_file
        ], capture_output=True, text=True, cwd=nir_test_path)
        
        if result.returncode == 0:
            print("✓ Dependencies installed successfully")
            return True
        else:
            print("✗ Failed to install dependencies")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"✗ Error installing dependencies: {e}")
        return False

def clean_environment():
    """Clean up test files"""
    print("Cleaning NIR_TEST environment...")
    
    base_path = "/home/martin/Development/vsCode_Environment/NIR_Mistral/NIR_TEST"
    
    # Remove generated files
    generated_dirs = ["output", "logs", "data/processed", "data/results"]
    
    for directory in generated_dirs:
        full_path = os.path.join(base_path, directory)
        if os.path.exists(full_path):
            try:
                # Remove all files in the directory but keep the directory
                for file in os.listdir(full_path):
                    file_path = os.path.join(full_path, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"  ✓ Removed: {directory}/{file}")
            except Exception as e:
                print(f"  ✗ Error cleaning {directory}: {e}")
    
    print("Environment cleaned!")

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(
        description="NIR_TEST Environment - NIR_Mistral DeveloperAgent Framework Test Environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_test_environment.py info          Show environment information
  python run_test_environment.py setup         Setup the test environment
  python run_test_environment.py run           Run complete demonstration
  python run_test_environment.py test load_data  Run specific test
  python run_test_environment.py install       Install dependencies
  python run_test_environment.py clean         Clean up test files
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show environment information')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Setup the test environment')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run complete demonstration')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run specific tests')
    test_parser.add_argument('test_name', nargs='?', default='load_data', 
                           help='Test to run (load_data, analyze, validate, report)')
    
    # Install command
    install_parser = subparsers.add_parser('install', help='Install dependencies')
    
    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Clean up test files')
    
    args = parser.parse_args()
    
    if not args.command:
        print_header()
        parser.print_help()
        return
    
    # Execute the appropriate command
    if args.command == 'info':
        print_environment_info()
    elif args.command == 'setup':
        setup_environment()
    elif args.command == 'run':
        success = run_demonstration()
        sys.exit(0 if success else 1)
    elif args.command == 'test':
        success = run_specific_test(args.test_name)
        sys.exit(0 if success else 1)
    elif args.command == 'install':
        success = install_dependencies()
        sys.exit(0 if success else 1)
    elif args.command == 'clean':
        clean_environment()
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()