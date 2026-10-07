"""M3 verification: reference-spectrum import with license gate.

Covers mandatory source/license/version metadata, rejected licenses, x-axis
unit normalization to nm (M1 integration), idempotent-ish import summaries and
provenance display for similarity hits."""

import os
import sys
import types
from types import SimpleNamespace  # noqa: F401

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from services.reference_import import (
    LicenseViolationError,
    import_reference_dataset,
    normalize_reference_axis,
    reference_hit_display,
    validate_reference_metadata,
)


def test_missing_metadata_rejected():
    try:
        validate_reference_metadata({"source": "USDA"})
        raised = False
    except LicenseViolationError as e:
        raised = True
        assert "license" in str(e) and "version" in str(e)
    assert raised


def test_rejected_license_names():
    for bad in ("unknown", "proprietary", "All Rights Reserved"):
        try:
            validate_reference_metadata(
                {"source": "x", "license": bad, "version": "1"})
            raised = False
        except LicenseViolationError:
            raised = True
        assert raised, bad


def test_valid_metadata_accepted():
    validate_reference_metadata(
        {"source": "Open Specy", "license": "CC-BY-4.0", "version": "v1.2"})


def test_axis_normalization_cm_to_nm():
    r = normalize_reference_axis([10000.0, 5000.0, 4000.0], "1/CM")
    assert r["x_unit"] == "nm"
    assert abs(r["wavelengths_nm"][0] - 1000.0) < 1e-6
    assert abs(r["wavelengths_nm"][2] - 2500.0) < 1e-6


def test_axis_normalization_unknown_unit_rejected():
    try:
        normalize_reference_axis([1.0, 2.0], "")
        raised = False
    except LicenseViolationError:
        raised = True
    assert raised


def _entry(**overrides):
    entry = {
        "file_name": "ref_polystyrene.csv",
        "wavelengths": [1000.0, 1100.0, 1200.0],
        "intensities": [0.1, 0.2, 0.3],
        "x_unit": "nm",
        "metadata": {"source": "Open Specy", "license": "CC-BY-4.0",
                     "version": "v1.2", "sample_type": "polystyrene"},
    }
    entry.update(overrides)
    return entry


def test_import_with_license_gate(monkey=None):
    import types
    created = []

    fake_model = types.SimpleNamespace()
    fake_model.objects = types.SimpleNamespace(
        create=lambda **kwargs: created.append(kwargs))
    fake_model.grid_key = staticmethod(
        lambda ws: ",".join(f"{w:g}" for w in ws))
    fake_core = types.ModuleType("core")
    fake_core_models = types.ModuleType("core.models")
    fake_core_models.SpectrumRecord = fake_model

    import services.reference_import as ri
    import sys
    saved = {k: sys.modules.get(k) for k in ("core", "core.models")}
    sys.modules["core"] = fake_core
    sys.modules["core.models"] = fake_core_models
    try:
        good = _entry()
        no_license = _entry(file_name="bad.csv",
                            metadata={"source": "x", "version": "1"})
        proprietary = _entry(
            file_name="prop.csv",
            metadata={"source": "x", "license": "proprietary",
                     "version": "1"})
        cm_axis = _entry(file_name="cm.csv", x_unit="1/CM",
                         wavelengths=[10000.0, 5000.0, 4000.0])
        summary = ri.import_reference_dataset(
            [good, no_license, proprietary, cm_axis], user=None)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v

    assert summary["imported"] == 2, summary
    assert summary["rejected"] == 2, summary
    assert summary["errors"] == 0
    assert len(created) == 2
    fnames = {c["file_name"] for c in created}
    assert fnames == {"ref_polystyrene.csv", "cm.csv"}
    cm_record = next(c for c in created if c["file_name"] == "cm.csv")
    assert abs(cm_record["wavelengths"][0] - 1000.0) < 1e-6
    assert cm_record["metadata"]["x_unit"] == "nm"
    assert cm_record["metadata"]["reference_import"] is True
    good_record = next(
        c for c in created if c["file_name"] == "ref_polystyrene.csv")
    assert good_record["metadata"]["license"] == "CC-BY-4.0"


def test_reference_hit_display_shows_provenance():
    record = types.SimpleNamespace(
        id="abc-123",
        file_name="ref.csv",
        sample_type="polystyrene",
        metadata={"source": "Open Specy", "license": "CC-BY-4.0",
                  "version": "v1.2", "reference_import": True},
    )
    display = reference_hit_display(record)
    assert display["source"] == "Open Specy"
    assert display["license"] == "CC-BY-4.0"
    assert display["version"] == "v1.2"
    assert display["is_reference_import"] is True


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {t.__name__}: {e}")
    if failed:
        raise SystemExit(f"{failed} test(s) failed")
    print(f"All {len(tests)} tests passed.")


if __name__ == "__main__":
    main()
