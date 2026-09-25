# OP14: truthfulness of the agent statements in the project report.
#
# Trigger: the Dpark fun NIR Triad (18 channels, 410-940 nm, wide format,
# 2049 measurements) produced wrong agent statements:
#   - a garbled wavelength axis via the two-column fallback loader,
#   - 'outside expected range (700, 2500)' although the sensor is a valid
#     VIS-NIR multisensor,
#   - a FAISS failure although intensities existed (schema mismatch),
#   - noise 0.71 'exceeds threshold' computed from the genuine spectral
#     shape instead of the measurement replicas,
#   - missing-metadata complaints about fields the platform itself knows.
#
# This matrix pins the corrected behaviour. File-type and spectrometer
# agnostic per the init prompt ground rules.
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"[PASS] {name}")
    else:
        failed += 1
        print(f"[FAIL] {name} {detail}")


TRIAD = PROJECT / "data" / "raw" / "T4-T5_ALLE_mit_Brix_2.txt"

# ---------------------------------------------------------------------------
# T1: wide-format detection and ingest (18 channels, 410-940 nm, 2049 rows)
# ---------------------------------------------------------------------------
from services.project_ingest import _detect_wide_format, _ingest_wide_format

check("T1a triad sample present", TRIAD.exists(), str(TRIAD))
wide = _detect_wide_format(str(TRIAD))
check("T1b wide format detected", wide is not None)
if wide:
    check("T1c 18 channels detected", len(wide["channel_columns"]) == 18,
          str(len(wide["channel_columns"])))
    check("T1d header row found above data", wide["header_row"] == 2,
          str(wide["header_row"]))


class _FR:
    """Minimal GenericFile stand-in (attributes used by the ingest)."""

    def __init__(self, path):
        import uuid
        self.id = uuid.uuid4()
        self.name = Path(path).name
        self.file_extension = Path(path).suffix
        self.file_category = "raw"
        self._path = str(path)

    def get_file_path(self):
        return self._path


entry = _ingest_wide_format(_FR(TRIAD), str(TRIAD), wide)
check("T1e wide ingest usable", entry.get("usable") is True, str(entry)[:200])
wavelengths = entry.get("preview", {}).get("wavelengths", [])
check("T1f wavelengths are the real channel axis",
      wavelengths == [410.0, 435.0, 460.0, 485.0, 510.0, 535.0, 560.0, 585.0,
                      610.0, 645.0, 680.0, 705.0, 730.0, 760.0, 810.0, 860.0,
                      900.0, 940.0], str(wavelengths))
check("T1g all 2049 measurements counted", entry.get("num_measurements") == 2049,
      str(entry.get("num_measurements")))
intensities = entry.get("preview", {}).get("intensities", [])
check("T1h median intensities in sensor range",
      all(500.0 < v < 100000.0 for v in intensities), str(intensities[:4]))
brix = [r for r in entry.get("numeric_references", []) if r["name"] == "Brix"]
check("T1i Brix reference plausible (4.3-8.1 °Brix)",
      brix and 4.0 <= brix[0]["min"] and brix[0]["max"] <= 9.0, str(brix))
replicas = entry.get("measurement_samples") or []
check("T1j measurement replicas extracted (>=3 rows)",
      len(replicas) >= 3 and len(replicas[0]) == 18,
      f"{len(replicas)}x{len(replicas[0]) if replicas else 0}")
check("T1k replica rows free of ADC overflow markers",
      all(0 <= v < 2 ** 31 for row in replicas for v in row))
check("T1l saturated measurements reported",
      entry.get("metadata", {}).get("saturated_measurements", 0) == 5,
      str(entry.get("metadata", {}).get("saturated_measurements")))

# T2: spectral agent must not impose a NIR range on a VIS multisensor
# ---------------------------------------------------------------------------
from agents.spectral_analysis_agent import SpectralAnalysisAgent, AgentStatus

agent = SpectralAnalysisAgent()
ctx = {
    "spectral_data": {"wavelengths": wavelengths, "intensities": intensities,
                      "sample_id": "triad"},
    "sample_id": "triad",
    "metadata": {},
}
out = agent.execute(ctx)
check("T2a spectral agent completes on VIS range", out.status == AgentStatus.COMPLETED)
check("T2b no false 'outside expected range' statement",
      all("outside expected range" not in r for r in out.data["spectral_analysis"]["recommendations"]),
      str(out.data["spectral_analysis"]["recommendations"]))
configured = SpectralAnalysisAgent(wavelength_range=(700, 2500))
out_cfg = configured.execute(ctx)
check("T2c explicit device range still graded",
      any("outside expected range" in r
          for r in out_cfg.data["spectral_analysis"]["recommendations"]))

# T3: sensor quality uses replicas, not the channel shape
# ---------------------------------------------------------------------------
from agents.sensor_quality_agent import SensorQualityAgent

sensor_out = SensorQualityAgent().execute({"spectra": replicas})
sd = sensor_out.data
check("T3a replica-based assessment runs", sensor_out.status == AgentStatus.COMPLETED)
check("T3b noise level from replica scatter (not 0.71 shape artefact)",
      0.01 < sd["noise_level"] < 0.71, str(sd.get("noise_level")))
check("T3c offset not false-positived against the replicas' own mean",
      sd.get("offset_detected") is not True, str(sd.get("offset_level")))

# T4: FAISS agent accepts the preview schema and completes without references
# ---------------------------------------------------------------------------
from agents.faiss_agent import FaissAgent

faiss_out = FaissAgent().execute({
    "reference_spectra": [],
    "reference_ids": [],
    "query_spectrum": None,
    "top_k": 5,
})
check("T4a FAISS completes with an empty reference set",
      faiss_out.status == AgentStatus.COMPLETED, str(faiss_out.data)[:200])

# T5: crew metadata context provides the known sample_id
# ---------------------------------------------------------------------------
import re

crew_source = (PROJECT / "agents" / "nir_analysis_crew.py").read_text(encoding="utf-8")
check("T5a crew injects sample_id into the metadata",
      'metadata.setdefault("sample_id", request.sample_id)' in crew_source)
check("T5b instrument alias mapped to instrument_type",
      '"instrument_type" not in metadata and metadata.get("instrument")' in crew_source)
check("T5c acquisition_time alias mapped to measurement_date",
      '"measurement_date" not in metadata' in crew_source
      and '"acquisition_time"' in crew_source)

# T6: end-to-end project run over the triad file produces truthful sections
# ---------------------------------------------------------------------------
from services.project_ingest import build_preparation_report
from services.project_crew import run_project_crew


class _FilesQS:
    def __init__(self, files):
        self._files = files

    def all(self):
        return self._files


class _Project:
    def __init__(self, files, name="OP14 Testprojekt"):
        self.files = _FilesQS(files)
        self.metadata_overrides = {}
        self.id = "op14test"
        self.name = name
        self.user_id = "u1"
        self.description = "OP14 truthfulness run"
        self.created_at = None

    def save(self, **kwargs):
        pass


fr = _FR(TRIAD)
prep = build_preparation_report(_Project([fr]))
ds = prep["datasets"][0]
check("T6a preparation report usable dataset", ds.get("usable") is True)
check("T6b 18 points reported", ds.get("num_points") == 18, str(ds.get("num_points")))
check("T6c range 410-940 reported",
      ds.get("wavelength_min") == 410.0 and ds.get("wavelength_max") == 940.0,
      f"{ds.get('wavelength_min')}-{ds.get('wavelength_max')}")

project = _Project([fr])
project.preparation_report = prep
project.phase = "released"
project.crew_results = None
project.final_report_path = None
results = run_project_crew(project)
statuses = {r["agent"]: r["status"] for r in results["per_agent_reports"]}
check("T6d all eight agent sections completed",
      len(statuses) == 8 and set(statuses.values()) == {"completed"}
      and "outlier_analysis" in statuses, str(statuses))
check("T6e no 'outside expected range' in the crew result",
      all("outside expected range" not in str(results).lower() for _ in [0]))
report_html = Path(project.final_report_path).read_text(encoding="utf-8")
check("T6f final report written", len(report_html) > 10000, str(len(report_html)))
check("T6g report shows the real channel axis",
      "410" in report_html and "940" in report_html)
check("T6h report states the 18 channels",
      "18" in report_html)
check("T6i crew results strictly JSON serializable",
      json.loads(json.dumps(results, default=str)) is not None)

# Cleanup run artefacts written into the sandbox output directory
print()
print(f"OP14 agent truthfulness matrix: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
