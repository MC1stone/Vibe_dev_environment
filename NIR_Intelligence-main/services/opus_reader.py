"""Bruker OPUS import for the NIR-IP (M2 of the interoperability plan).

OPUS `.d` files/directories are the de-facto standard in NIR labs. The binary
format is proprietary; reading is delegated to the optional, MIT-licensed
`opusfc` package (verified in THIRD_PARTY_LICENSES.md) - no GPL reader
(brukeropusreader is GPLv3) is used. When `opusfc` is not installed the loader
reports a clear reason and the caller falls back to the content-driven chain.
"""

from typing import Any, Dict, Optional


def opusfc_available() -> bool:
    try:
        import opusfc  # noqa: F401
        return True
    except ImportError:
        return False


def _opusfc_is_d(path: str) -> bool:
    """True for OPUS `.d` entries (file or unpacked directory)."""
    import os
    if os.path.isdir(path):
        return True
    return os.path.splitext(path)[1].lower() == ".d"


def load_opus_spectrum(path: str) -> Optional[Dict[str, Any]]:
    """Load one OPUS spectrum via opusfc into the unified spectral schema."""
    if not opusfc_available():
        return None
    try:
        import numpy as np
        import opusfc
        file_path = path
        if _opusfc_is_d(path):
            import os
            if os.path.isdir(path):
                from os import listdir
                candidates = [
                    os.path.join(path, name)
                    for name in sorted(listdir(path))
                    if os.path.isfile(os.path.join(path, name))
                    and os.path.splitext(name)[1].lower() not in (".log",)
                ]
                if not candidates:
                    return None
                file_path = candidates[0]
        content = opusfc.OpusFile(file_path)
        try:
            data = content.get_data("ScSm")
        finally:
            content.close()
        if data is None or len(data) == 0 or data.shape[0] < 2:
            return None
        x = np.asarray(data[0], dtype="float64")
        y = np.asarray(data[1], dtype="float64")
        import pandas as pd
        df = pd.DataFrame({"wavelength": x, "intensity": y})
        metadata: Dict[str, Any] = {
            "x_units": "cm^-1" if "cm" in str(getattr(content, "xunit", "")).lower()
            else "unknown",
            "opus_data_type": "ScSm (single channel sample)",
            "source_path": path,
        }
        return {
            "data": df,
            "format": ".d",
            "wavelength_column": "wavelength",
            "intensity_column": "intensity",
            "metadata": metadata,
        }
    except Exception:
        return None
