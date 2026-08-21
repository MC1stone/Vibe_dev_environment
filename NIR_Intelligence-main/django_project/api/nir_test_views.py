"""
NIR_TEST Environment API Views

This module provides API endpoints for integrating the NIR_TEST environment
with the Django frontend.
"""

import os
import sys
import subprocess
import json
import logging
from pathlib import Path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add NIR_TEST to the path
nir_test_path = project_root / "NIR_TEST"
if str(nir_test_path) not in sys.path:
    sys.path.insert(0, str(nir_test_path))

# Setup logging
logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def nir_test_info(request):
    """
    Get information about the NIR_TEST environment
    
    Returns:
        JSON response with environment information including:
        - Directory structure status
        - Test data files
        - Configuration status
        - Available agents
    """
    try:
        # Set PYTHONPATH
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{nir_test_path}:{project_root}:{env.get('PYTHONPATH', '')}"
        
        # Run the info command
        result = subprocess.run(
            [sys.executable, "run_test_environment.py", "info"],
            cwd=nir_test_path,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        
        if result.returncode == 0:
            # Parse the output
            info = _parse_environment_info(result.stdout)
            return Response({
                "status": "success",
                "data": info,
                "message": "Environment information retrieved successfully"
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "error",
                "message": f"Failed to get environment info: {result.stderr}",
                "error": result.stderr
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        logger.error(f"Error getting environment info: {e}")
        return Response({
            "status": "error",
            "message": f"Error getting environment info: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nir_test_demo(request):
    """
    Run the complete NIR_TEST demonstration
    
    Returns:
        JSON response with demonstration results
    """
    try:
        # Set PYTHONPATH
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{nir_test_path}:{project_root}:{env.get('PYTHONPATH', '')}"
        
        # Run the demonstration
        result = subprocess.run(
            [sys.executable, "run_test_environment.py", "run"],
            cwd=nir_test_path,
            capture_output=True,
            text=True,
            timeout=120,
            env=env
        )
        
        if result.returncode == 0:
            # Parse the results
            demo_results = _parse_demonstration_results(result.stdout)
            return Response({
                "status": "success",
                "data": demo_results,
                "message": "Demonstration completed successfully"
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "error",
                "message": f"Demonstration failed: {result.stderr}",
                "error": result.stderr
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except subprocess.TimeoutExpired:
        return Response({
            "status": "error",
            "message": "Demonstration timed out after 120 seconds"
        }, status=status.HTTP_408_REQUEST_TIMEOUT)
    except Exception as e:
        logger.error(f"Error running demonstration: {e}")
        return Response({
            "status": "error",
            "message": f"Error running demonstration: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nir_test_run(request, test_name):
    """
    Run a specific NIR_TEST test
    
    Args:
        test_name: Name of the test to run (load_data, analyze, validate, report)
    
    Returns:
        JSON response with test results
    """
    valid_tests = ["load_data", "analyze", "validate", "report"]
    
    if test_name not in valid_tests:
        return Response({
            "status": "error",
            "message": f"Invalid test name. Valid tests are: {', '.join(valid_tests)}"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Set PYTHONPATH
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{nir_test_path}:{project_root}:{env.get('PYTHONPATH', '')}"
        
        # Run the specific test
        result = subprocess.run(
            [sys.executable, "run_test_environment.py", "test", test_name],
            cwd=nir_test_path,
            capture_output=True,
            text=True,
            timeout=60,
            env=env
        )
        
        if result.returncode == 0:
            test_results = _parse_test_results(result.stdout, test_name)
            return Response({
                "status": "success",
                "data": test_results,
                "message": f"Test '{test_name}' completed successfully"
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "error",
                "message": f"Test '{test_name}' failed: {result.stderr}",
                "error": result.stderr
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except subprocess.TimeoutExpired:
        return Response({
            "status": "error",
            "message": f"Test '{test_name}' timed out after 60 seconds"
        }, status=status.HTTP_408_REQUEST_TIMEOUT)
    except Exception as e:
        logger.error(f"Error running test {test_name}: {e}")
        return Response({
            "status": "error",
            "message": f"Error running test {test_name}: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def nir_test_files(request):
    """
    Get list of test data files in NIR_TEST environment
    
    Returns:
        JSON response with list of test data files
    """
    try:
        raw_data_path = nir_test_path / "data" / "raw"
        
        if not raw_data_path.exists():
            return Response({
                "status": "error",
                "message": "Test data directory not found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        test_files = []
        for file_path in raw_data_path.glob("*.txt"):
            test_files.append({
                "name": file_path.name,
                "path": str(file_path.relative_to(nir_test_path)),
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime
            })
        
        return Response({
            "status": "success",
            "data": test_files,
            "message": f"Found {len(test_files)} test data files"
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error getting test files: {e}")
        return Response({
            "status": "error",
            "message": f"Error getting test files: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def nir_test_report(request):
    """
    Get the latest test report from NIR_TEST environment
    
    Returns:
        JSON response with test report content
    """
    try:
        report_path = nir_test_path / "output" / "test_report.txt"
        
        if not report_path.exists():
            return Response({
                "status": "error",
                "message": "No test report found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        with open(report_path, 'r') as f:
            report_content = f.read()
        
        return Response({
            "status": "success",
            "data": {"report": report_content},
            "message": "Test report retrieved successfully"
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error getting test report: {e}")
        return Response({
            "status": "error",
            "message": f"Error getting test report: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nir_test_setup(request):
    """
    Setup the NIR_TEST environment
    
    Returns:
        JSON response with setup results
    """
    try:
        # Set PYTHONPATH
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{nir_test_path}:{project_root}:{env.get('PYTHONPATH', '')}"
        
        # Run setup
        result = subprocess.run(
            [sys.executable, "run_test_environment.py", "setup"],
            cwd=nir_test_path,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        
        if result.returncode == 0:
            return Response({
                "status": "success",
                "message": "Environment setup completed successfully",
                "output": result.stdout
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "error",
                "message": f"Environment setup failed: {result.stderr}",
                "error": result.stderr
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        logger.error(f"Error setting up environment: {e}")
        return Response({
            "status": "error",
            "message": f"Error setting up environment: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nir_test_clean(request):
    """
    Clean the NIR_TEST environment
    
    Returns:
        JSON response with cleanup results
    """
    try:
        # Set PYTHONPATH
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{nir_test_path}:{project_root}:{env.get('PYTHONPATH', '')}"
        
        # Run cleanup
        result = subprocess.run(
            [sys.executable, "run_test_environment.py", "clean"],
            cwd=nir_test_path,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        
        if result.returncode == 0:
            return Response({
                "status": "success",
                "message": "Environment cleaned successfully",
                "output": result.stdout
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "error",
                "message": f"Environment cleanup failed: {result.stderr}",
                "error": result.stderr
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        logger.error(f"Error cleaning environment: {e}")
        return Response({
            "status": "error",
            "message": f"Error cleaning environment: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Helper functions
def _parse_environment_info(output: str) -> dict:
    """Parse environment info output into structured data"""
    info = {
        "directory_structure": {},
        "test_data_files": [],
        "configuration": "not_found",
        "agents": []
    }
    
    lines = output.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if "Directory Structure:" in line:
            current_section = "directory_structure"
            continue
        elif "Test Data Files" in line:
            current_section = "test_data_files"
            continue
        elif "Configuration:" in line:
            current_section = "configuration"
            continue
        elif "Agents:" in line:
            current_section = "agents"
            continue
        
        if current_section == "directory_structure":
            if "✓" in line:
                dir_name = line.split("✓")[1].strip()
                info["directory_structure"][dir_name] = True
            elif "✗" in line:
                dir_name = line.split("✗")[1].strip()
                info["directory_structure"][dir_name] = False
        
        elif current_section == "test_data_files":
            if "- " in line and ".txt" in line:
                parts = line.split("(")
                if len(parts) >= 1:
                    file_info = parts[0].replace("- ", "").strip()
                    file_name = file_info.split(" ")[0]
                    info["test_data_files"].append({
                        "name": file_name,
                        "full_line": line
                    })
        
        elif current_section == "configuration":
            if "✓" in line:
                info["configuration"] = "found"
            elif "✗" in line:
                info["configuration"] = "not_found"
        
        elif current_section == "agents":
            if "- " in line and ".py" in line:
                agent_name = line.split("- ")[1].strip()
                info["agents"].append(agent_name)
    
    return info

def _parse_demonstration_results(output: str) -> dict:
    """Parse demonstration results into structured data"""
    results = {
        "spectra_loaded": [],
        "analysis_results": {},
        "quality_control": {},
        "summary": {}
    }
    
    lines = output.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        
        if "Loaded Spectra:" in line:
            current_section = "spectra_loaded"
            continue
        elif "Analysis Results:" in line:
            current_section = "analysis_results"
            continue
        elif "Quality Control:" in line:
            current_section = "quality_control"
            continue
        elif "Demonstration completed successfully!" in line:
            current_section = "summary"
            continue
        
        if current_section == "spectra_loaded":
            if "- " in line and "(" in line:
                parts = line.split("(")
                if len(parts) >= 2:
                    name_part = parts[0].replace("- ", "").strip()
                    id_part = parts[1].replace(")", "").strip()
                    data_points = ""
                    if ":" in parts[1]:
                        id_part = parts[1].split(":")[0].replace(")", "").strip()
                        data_points = parts[1].split(":")[1].replace(")", "").strip()
                    
                    results["spectra_loaded"].append({
                        "name": name_part,
                        "id": id_part,
                        "data_points": data_points
                    })
        
        elif current_section == "analysis_results":
            if "- " in line and line.endswith(":"):
                sample_name = line.replace("- ", "").replace(":", "").strip()
                results["analysis_results"][sample_name] = {}
            elif "Wavelength Range:" in line:
                range_info = line.replace("Wavelength Range:", "").strip()
                current_sample = list(results["analysis_results"].keys())[-1] if results["analysis_results"] else "unknown"
                results["analysis_results"][current_sample]["wavelength_range"] = range_info
            elif "Mean Absorbance:" in line:
                mean_abs = line.replace("Mean Absorbance:", "").strip()
                current_sample = list(results["analysis_results"].keys())[-1] if results["analysis_results"] else "unknown"
                results["analysis_results"][current_sample]["mean_absorbance"] = mean_abs
            elif "Peaks Found:" in line:
                peaks = line.replace("Peaks Found:", "").strip()
                current_sample = list(results["analysis_results"].keys())[-1] if results["analysis_results"] else "unknown"
                results["analysis_results"][current_sample]["peaks_found"] = peaks
        
        elif current_section == "quality_control":
            if "- " in line and ":" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    sample_name = parts[0].replace("- ", "").strip()
                    status = parts[1].strip()
                    results["quality_control"][sample_name] = status
    
    return results

def _parse_test_results(output: str, test_name: str) -> dict:
    """Parse test results based on test type"""
    results = {}
    
    if test_name == "load_data":
        # Parse loaded spectra information
        spectra = []
        lines = output.split('\n')
        for line in lines:
            if "Successfully loaded" in line:
                count_part = line.split("Successfully loaded")[1].split("spectra")[0].strip()
                results["count"] = count_part
            elif "- " in line and "data points" in line:
                parts = line.split("- ")[1].split(":")
                if len(parts) >= 2:
                    spectrum_info = parts[0].strip()
                    data_points = parts[1].replace("data points", "").strip()
                    spectra.append({
                        "name": spectrum_info,
                        "data_points": data_points
                    })
        results["spectra"] = spectra
    
    elif test_name == "analyze":
        # Parse analysis results
        analysis = {}
        lines = output.split('\n')
        for line in lines:
            if "Analyzed" in line and "spectra" in line:
                count = line.split("Analyzed")[1].split("spectra")[0].strip()
                results["count"] = count
            elif "- " in line and ":" in line and "Mean=" in line:
                parts = line.split("- ")[1].split(":")
                if len(parts) >= 2:
                    sample_name = parts[0].strip()
                    analysis_info = parts[1].strip()
                    analysis[sample_name] = analysis_info
        results["analysis"] = analysis
    
    elif test_name == "validate":
        # Parse validation results
        validation = {}
        lines = output.split('\n')
        for line in lines:
            if "Validated" in line and "spectra" in line:
                count = line.split("Validated")[1].split("spectra")[0].strip()
                results["count"] = count
            elif "- " in line and ":" in line:
                parts = line.split("- ")[1].split(":")
                if len(parts) >= 2:
                    sample_name = parts[0].strip()
                    status = parts[1].strip()
                    validation[sample_name] = status
        results["validation"] = validation
    
    elif test_name == "report":
        # Parse report generation
        lines = output.split('\n')
        for line in lines:
            if "Report generated successfully" in line:
                results["status"] = "success"
            elif "Report content preview:" in line:
                # Extract preview lines
                preview_lines = []
                for preview_line in lines[lines.index(line)+1:lines.index(line)+21]:
                    if preview_line.strip():
                        preview_lines.append(preview_line.strip())
                results["preview"] = preview_lines
    
    return results