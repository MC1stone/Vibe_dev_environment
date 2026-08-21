from analysis.models import SpectralData
from agents.reporting_agent import ReportingAgent
from agents.spectral_analysis_agent import SpectralAnalysisAgent
from agents.metadata_quality_agent import MetadataQualityAgent
from agents.calibration_agent import CalibrationAgent
import asyncio

# Check if any files exist
count = SpectralData.objects.count()
print(f"Found {count} SpectralData records")

if count == 0:
    print("ERROR: No files uploaded to database!")
    print("Please upload a file first at http://localhost:8000/upload/")
else:
    # Get the latest file
    latest = SpectralData.objects.latest('upload_date')
    print(f"Using file: {latest.original_filename}")

    # Load and analyze the data
    spectral_agent = SpectralAnalysisAgent()
    metadata_agent = MetadataQualityAgent()
    calibration_agent = CalibrationAgent()
    report_agent = ReportingAgent()

    # Load spectral data
    try:
        data = spectral_agent.load_spectral_data(latest.file_path)
        print(f"Loaded spectral data with {len(data.wavelengths)} wavelengths")

        # Analyze
        analysis_result = spectral_agent.analyze(data)
        metadata_quality = metadata_agent.validate_metadata(latest.metadata or {})
        calibration_result = calibration_agent.generate_calibration(data)

        # Generate report (async)
        report = asyncio.run(
            report_agent.generate_spectral_analysis_report(
                analysis_result,
                metadata_quality,
                calibration_result,
                output_dir="/app/reports/"
            )
        )

        print(f"✅ Report generated: {report.title}")
        print(f"   Sections: {[s.title for s in report.sections]}")
        print(f"   Python source files: {len(report.python_source)}")
        print(f"   Data files: {report.data_files}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
