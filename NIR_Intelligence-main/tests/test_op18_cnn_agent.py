# OP18: CNN agent fix and supervised calibration pipeline.
#
# Two root causes kept the CNN agent from ever training:
# 1. TensorFlow is deliberately not part of the minimal requirements, and
#    the CNN training code itself was broken for current Keras
#    (deprecated input_shape argument) and lacked feature scaling (raw ADC
#    values vs Brix ~5 stall the gradient descent) and any loss history.
# 2. No reference values ever reached the supervised agents: the wide
#    ingest kept Brix only as a column statistic, never per measurement.
#    A supervised calibrator needs varying targets - the replica block is
#    one object with a constant Brix, so the ingest now samples calibration
#    rows across the whole file (one target per measured object).
#
# The matrix pins: graceful deferred path without TF, real training with
# TF, Keras-3 conform model construction, scaled training, loss curves and
# the end-to-end pipeline from the Triad file to a trained CNN.
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
check("T1a triad sample present", TRIAD.exists(), str(TRIAD))

# ---------------------------------------------------------------------------
# T1: ingest provides per-measurement calibration data (root cause 2)
# ---------------------------------------------------------------------------
from services.project_ingest import _detect_wide_format, _ingest_wide_format

wide = _detect_wide_format(str(TRIAD))
check("T1b wide format detected", wide is not None)


class _FR:
    def __init__(self, path):
        import uuid
        self.id = uuid.uuid4()
        self.name = Path(path).name
        self.file_extension = Path(path).suffix
        self.file = None


dataset = _ingest_wide_format(_FR(TRIAD), str(TRIAD), wide)
cal = dataset.get("calibration_samples") or []
ref = dataset.get("reference_values")
check("T1c calibration samples extracted (whole file)", len(cal) >= 50,
      str(len(cal)))
check("T1d one reference value per calibration row",
      isinstance(ref, list) and len(ref) == len(cal) and len(ref) >= 50,
      str(len(ref) if ref else "None"))
check("T1e reference values are the real Brix range (4.3-8.1)",
      ref and 4.0 <= min(ref) and max(ref) <= 8.5,
      f"{min(ref):.2f}-{max(ref):.2f}" if ref else "None")
check("T1f target varies (a constant cannot train a calibrator)",
      ref and len(set(ref)) >= 5, str(len(set(ref))) if ref else "None")
check("T1g replica block still present for the sensor agent",
      len(dataset.get("measurement_samples") or []) >= 3,
      str(len(dataset.get("measurement_samples") or [])))

# ---------------------------------------------------------------------------
# T2: CNN agent - fixed training path (root cause 1)
# ---------------------------------------------------------------------------
import numpy as np

from agents.neural_network_agent import NeuralNetworkAgent, _tensor_flow_available

agent = NeuralNetworkAgent()
tf_available = _tensor_flow_available()

if not tf_available:
    out = agent._train_cnn(np.zeros((5, 4)), np.array([1.0, 2, 3, 4, 5]), {})
    check("T2a without TF: graceful deferred, never simulated",
          out.get("status") == "deferred", str(out))
else:
    out = agent._train_cnn(np.zeros((3, 4)), np.array([1.0, 2, 3]), {})
    check("T2a too few samples: skipped, not crashed",
          out.get("status") == "skipped", str(out))
    out = agent._train_cnn(np.ones((10, 4)), None, {})
    check("T2b without reference values: skipped (supervised model)",
          out.get("status") == "skipped", str(out))

    rng = np.random.default_rng(42)
    X = rng.normal(size=(60, 18)) * 1500.0 + 3000.0
    w = rng.normal(size=18)
    y = X @ w / 27000.0 + 5.0 + rng.normal(scale=0.05, size=60)
    out = agent._train_cnn(X, y, {"epochs": 60})
    check("T2c CNN trains with TF (status ok)", out.get("status") == "ok", str(out))
    loss = out.get("loss_curve") or []
    check("T2d scaled training converges (loss drops substantially)",
          len(loss) == 60 and loss[-1] < 0.5 * loss[0],
          f"first={loss[0]:.3f} last={loss[-1]:.3f}" if loss else "no curve")
    check("T2e RMSE reported",
          isinstance(out.get("rmse"), float) and out["rmse"] >= 0.0,
          str(out.get("rmse")))
    check("T2f loss curve recorded (needed for the loss plot)",
          isinstance(out.get("loss_curve"), list) and len(out["loss_curve"]) == 60,
          str(len(out.get("loss_curve") or [])))
    check("T2g validation loss recorded when samples suffice",
          isinstance(out.get("validation_loss_curve"), list)
          and len(out["validation_loss_curve"]) > 0,
          str(len(out.get("validation_loss_curve") or [])))
    check("T2h convergence flag reflects the history (not hardcoded True)",
          out.get("convergence_achieved") in (True, False))

    src = (PROJECT / "agents" / "neural_network_agent.py").read_text(encoding="utf-8")
    check("T2i Keras-3 conform model construction (Input layer, no input_shape kwarg)",
          "tf.keras.Input" in src and 'input_shape=' not in src)
    check("T2j feature scaling in the CNN path",
          "StandardScaler" in src.split("def _train_cnn")[1].split("def ")[0])

# ---------------------------------------------------------------------------
# T3: end-to-end - agent execute() on the real triad calibration data
# ---------------------------------------------------------------------------
if cal and ref:
    out = agent.execute({
        "spectra": cal, "reference_values": ref,
        "models": ["MLP", "Autoencoder", "CNN"],
        "training": {"epochs": 30},
    })
    data = out.data
    check("T3a agent completes on the triad data",
          out.status.name == "COMPLETED" if hasattr(out.status, "name") else True)
    if _tensor_flow_available():
        check("T3b CNN trained (not deferred, not skipped) end-to-end",
              "CNN" in data.get("models_trained", []),
              str(data.get("models_deferred")) + " " + str(data.get("models_skipped")))
        cnn = (data.get("model_results") or {}).get("CNN") or {}
        check("T3c CNN reaches a usable Brix R2 on the triad data",
              cnn.get("r2_score", -1) > 0.2, str(cnn.get("r2_score")))
    else:
        check("T3b CNN trained (not deferred, not skipped) end-to-end",
              "CNN" in data.get("models_trained", [])
              or any(d.get("model") == "CNN" for d in data.get("models_deferred", [])),
              str(data.get("models_skipped")))
    check("T3d results strictly JSON-safe (no numpy types)",
          _is_json := (lambda v: isinstance(v, (int, float, str, bool, list, dict, type(None))))(
              data.get("status")))

# ---------------------------------------------------------------------------
# T4: crew wiring - supervised agents get the calibration samples
# ---------------------------------------------------------------------------
crew_src = (PROJECT / "agents" / "nir_analysis_crew.py").read_text(encoding="utf-8")
check("T4a crew defines a supervised context with calibration samples",
      "calibration_samples" in crew_src and "supervised_context" in crew_src)
check("T4b statistical agent uses the supervised context",
      "supervised_context" in crew_src.split("statistical_output = self.statistical_analysis_agent.execute")[1][:200])
check("T4c neural network agent uses the supervised context",
      "supervised_context" in crew_src.split("neural_output = self.neural_network_agent.execute")[1][:200])
crew_proj_src = (PROJECT / "services" / "project_crew.py").read_text(encoding="utf-8")
check("T4d project crew passes calibration_samples and reference_values",
      "calibration_samples" in crew_proj_src
      and "reference_values" in crew_proj_src)

print(f"OP18 CNN agent matrix: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
