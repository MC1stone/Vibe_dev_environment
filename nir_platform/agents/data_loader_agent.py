"""
Data Loader Agent for NIR Intelligence Platform

This agent owns the ingestion and structural parsing of newly uploaded spectral
files. It is invoked every time new data arrives and is responsible for:

- Detecting the real column-header row, skipping free-text preambles that some
  spectrometer exports prepend (e.g. a German description paragraph before the
  `Counter;...;A_410;...` header of a SparkFun NIR Triad export).
- Reading the file across several encodings (utf-8, latin-1, cp1252) so exports
  with umlauts in metadata columns still parse.
- Parsing wide-format multi-sample NIR exports (per-sample intensity matrix +
  reference columns such as Brix/Temp) as well as classic two-column
  (wavelength, intensity) spectra.
- Detecting the spectrometer type from the parsed wavelengths.
- Producing a structured LoadResult (wavelengths, representative intensities,
  full per-sample intensity matrix, metadata incl. Brix, spectrometer info,
  and any issues detected during loading).

The downstream analysis agents (spectral analysis, metadata quality,
calibration, QA, reporting) consume the LoadResult, so the loading/parsing
logic lives in exactly one place and runs automatically on every new upload.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Column-name pattern for wide-NIR spectral channels: A_410, B_435, R_610, ...
_WIDE_COL_RE = re.compile(r'([A-Z])_?(\d+(?:\.\d+)?)$')
# Same pattern but used to scan raw file lines for the spectral header row,
# where the token is followed by a delimiter (semicolon/tab/comma).
_WIDE_HEADER_TOKEN_RE = re.compile(r'([A-Z])_?(\d+(?:\.\d+)?)\s*[;,\t]')


@dataclass
class LoadIssue:
    """A non-fatal issue detected while loading a file."""
    code: str
    severity: str  # "warning" | "error"
    message: str

    def to_dict(self) -> Dict:
        return {"code": self.code, "severity": self.severity, "message": self.message}


@dataclass
class LoadResult:
    """Structured result of loading a spectral file."""
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    spectrometer_type: Optional[str] = None
    spectrometer_info: Dict[str, Any] = field(default_factory=dict)
    wavelengths: List[float] = field(default_factory=list)
    intensities: List[float] = field(default_factory=list)
    # Per-sample intensity matrix (rows = samples, cols = wavelengths) for
    # wide-format exports; empty for single-spectrum files.
    intensity_matrix: List[List[float]] = field(default_factory=list)
    spectral_columns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    num_samples: int = 0
    format: str = "unknown"
    issues: List[LoadIssue] = field(default_factory=list)
    success: bool = False

    def to_dict(self) -> Dict:
        return {
            "file_path": self.file_path,
            "file_type": self.file_type,
            "spectrometer_type": self.spectrometer_type,
            "spectrometer_info": self.spectrometer_info,
            "wavelengths": self.wavelengths,
            "intensities": self.intensities,
            "intensity_matrix": self.intensity_matrix,
            "spectral_columns": self.spectral_columns,
            "metadata": self.metadata,
            "num_samples": self.num_samples,
            "format": self.format,
            "issues": [i.to_dict() for i in self.issues],
            "success": self.success,
        }


class DataLoaderAgent:
    """Agent that loads and structurally parses newly uploaded spectral files.

    Run on every new upload; the returned LoadResult feeds the downstream
    analysis pipeline.
    """

    def __init__(self, agent_id: str = "data_loader_agent"):
        self.agent_id = agent_id
        self.spectrometer_database = self._load_spectrometer_database()
        logger.info(f"Data Loader Agent {self.agent_id} initialized")

    def _load_spectrometer_database(self) -> Dict[str, Dict[str, Any]]:
        return {
            "sparkfun_nir_triad": {
                "wavelength_range": [410, 940],
                "resolution": 30.0,
                "num_channels": 18,
                "wavelengths": [410, 435, 460, 485, 510, 535, 560, 585, 610,
                                 645, 680, 705, 730, 760, 810, 860, 900, 940],
            },
            "ocean_optics": {
                "wavelength_range": [200, 1100],
                "resolution": 0.5,
                "wavelengths": None,
            },
            "asd_fieldspec": {
                "wavelength_range": [350, 2500],
                "resolution": 1.0,
                "wavelengths": None,
            },
            "diy_raspberry": {
                "wavelength_range": [650, 1100],
                "resolution": 10.0,
                "wavelengths": None,
            },
            "diy_arduino": {
                "wavelength_range": [700, 1000],
                "resolution": 15.0,
                "wavelengths": None,
            },
        }

    async def load(self, file_path: str) -> LoadResult:
        """Load and structurally parse a spectral file.

        Args:
            file_path: Path to the uploaded file on disk.

        Returns:
            LoadResult with parsed wavelengths/intensities, per-sample matrix
            and metadata (incl. Brix for wide-format exports), plus any issues.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        logger.info(f"Data Loader Agent loading {file_path}")
        result = LoadResult(file_path=file_path, file_type=suffix)

        try:
            if suffix == ".csv":
                self._load_delimited(file_path, result)
            elif suffix == ".txt":
                self._load_delimited(file_path, result)
            elif suffix in (".xlsx", ".xls"):
                self._load_excel(file_path, result)
            elif suffix == ".json":
                self._load_json(file_path, result)
            else:
                self._load_delimited(file_path, result)
        except Exception as e:
            logger.error(f"Error loading spectral data: {e}")
            result.issues.append(LoadIssue("load_failed", "error", str(e)))
            result.success = False
            return result

        if not result.wavelengths:
            result.issues.append(LoadIssue(
                "no_spectral_data", "error",
                "Could not identify any spectral columns in the file."))
            result.success = False
            return result

        result.spectrometer_info = self._detect_spectrometer_type(
            np.array(result.wavelengths, dtype=float))
        result.spectrometer_type = result.spectrometer_info.get("type")
        result.success = True
        logger.info(
            f"Loaded {file_path}: wl_len={len(result.wavelengths)} "
            f"ns={result.num_samples} spec_type={result.spectrometer_type!r} "
            f"format={result.format!r}")
        return result

    @staticmethod
    def _find_wide_header_row(file_path: str) -> int:
        """Return the 0-based index of the wide-NIR spectral header row.

        Wide-NIR exports (e.g. SparkFun Triad) are often prefixed with a
        free-text description / blank lines before the actual column header
        (`Counter;Messobjekt;...;A_410;B_435;...`). When pandas reads such a
        file with the default header it treats the prose line as the column
        names, so the A_410-style spectral columns are never found and the
        loader silently falls through to two-column mode. Scan the file for
        the first line containing several spectral-style tokens and use it as
        the header. Returns -1 when no such line is found.
        """
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f):
                if len(_WIDE_HEADER_TOKEN_RE.findall(line)) >= 2:
                    return idx
        return -1

    @staticmethod
    def _read_delimited(file_path: str, sep: Optional[str] = None) -> "pd.DataFrame":
        """Read a delimited file, trying several encodings.

        When a wide-NIR spectral header row is found later than line 0, it is
        used as the pandas header (skiprows) so the A_410-style columns parse
        correctly instead of being swallowed by a prose preamble.
        """
        skip = DataLoaderAgent._find_wide_header_row(file_path)
        last_exc: Optional[UnicodeDecodeError] = None
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                return pd.read_csv(
                    file_path, sep=sep, encoding=enc,
                    on_bad_lines="skip", dtype=str,
                    skiprows=(skip if skip > 0 else None),
                )
            except UnicodeDecodeError as e:
                last_exc = e
                continue
            except Exception:
                break
        if last_exc is not None:
            raise last_exc
        return pd.DataFrame()

    def _load_delimited(self, file_path: str, result: LoadResult) -> None:
        """Load CSV/TXT, preferring the wide-NIR parse then two-column."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        header_row_idx = self._find_wide_header_row(file_path)
        if 0 <= header_row_idx < len(lines):
            first_data_line = lines[header_row_idx].strip()
        else:
            first_data_line = ""
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    first_data_line = stripped
                    break
        delimiter = None
        for cand in (";", "\t", ","):
            if first_data_line and cand in first_data_line:
                delimiter = cand
                break

        try:
            df = self._read_delimited(file_path, sep=delimiter)
        except Exception as e:
            result.issues.append(LoadIssue("read_failed", "warning", str(e)))
            df = pd.DataFrame()

        if not df.empty and self._parse_wide_nir(df, result):
            return

        self._parse_two_column(lines, result)

    def _parse_wide_nir(self, df: "pd.DataFrame", result: LoadResult) -> bool:
        """Parse a wide-format multi-sample NIR dataframe.

        Spectral columns are named like A_410, B_435, ... L_940 (wavelength nm
        encoded in the column name). The representative spectrum is the
        column-wise mean; the full per-sample intensity matrix and metadata
        columns (Brix, Temp, ...) are preserved for downstream calibration.
        Returns False (and leaves result untouched) if not a wide-NIR export.
        """
        wl_cols: Dict[str, float] = {}
        for col in df.columns:
            m = _WIDE_COL_RE.search(str(col).strip())
            if m:
                wl_cols[col] = float(m.group(2))
        if not wl_cols:
            return False

        col_order = list(wl_cols.keys())
        wavelengths = [wl_cols[c] for c in col_order]
        intensity_df = df[col_order].apply(pd.to_numeric, errors="coerce")
        matrix = intensity_df.to_numpy(dtype=float)
        # Drop rows that are entirely NaN.
        valid_mask = ~np.isnan(matrix).all(axis=1)
        matrix = matrix[valid_mask]
        intensities = np.nanmean(matrix, axis=0) if matrix.size else np.array([])

        meta: Dict[str, Any] = {}
        for col in df.columns:
            if col not in wl_cols:
                meta[col] = df[col].dropna().tolist()

        result.wavelengths = [float(w) for w in wavelengths]
        result.intensities = [
            float(v) if not (isinstance(v, float) and np.isnan(v)) else 0.0
            for v in intensities.tolist()
        ]
        result.intensity_matrix = [
            [float(v) if not (isinstance(v, float) and np.isnan(v)) else 0.0
             for v in row]
            for row in matrix.tolist()
        ]
        result.spectral_columns = col_order
        result.metadata = meta
        result.num_samples = int(matrix.shape[0]) if matrix.size else 0
        result.format = "wide_nir_multisample"
        return True

    def _parse_two_column(self, lines: List[str], result: LoadResult) -> None:
        """Fallback parse for classic two-column (wavelength, intensity) data."""
        wavelengths: List[float] = []
        intensities: List[float] = []
        metadata: Dict[str, Any] = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                parts = line[1:].split(":")
                if len(parts) >= 2:
                    metadata[parts[0].strip()] = parts[1].strip()
                continue
            parts: Optional[List[str]] = None
            for delim in (";", "\t", ",", None):
                cand = line.split(delim) if delim else line.split()
                cand = [p.strip() for p in cand if p.strip()]
                if len(cand) >= 2:
                    parts = cand
                    break
            if not parts:
                continue
            try:
                wavelengths.append(float(parts[0]))
                intensities.append(float(parts[1]))
            except (ValueError, IndexError):
                continue
        result.wavelengths = wavelengths
        result.intensities = intensities
        result.metadata = metadata
        result.num_samples = len(wavelengths)
        result.format = "two_column"

    def _load_excel(self, file_path: str, result: LoadResult) -> None:
        df = pd.read_excel(file_path, dtype=str)
        if not self._parse_wide_nir(df, result):
            # Fall back to first two columns as two-column data.
            if len(df.columns) >= 2:
                wl = pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna()
                it = pd.to_numeric(df.iloc[:, 1], errors="coerce").dropna()
                n = min(len(wl), len(it))
                result.wavelengths = wl.iloc[:n].astype(float).tolist()
                result.intensities = it.iloc[:n].astype(float).tolist()
                result.num_samples = n
                result.format = "excel_two_column"

    def _load_json(self, file_path: str, result: LoadResult) -> None:
        import json
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        if isinstance(data, dict):
            result.wavelengths = [float(w) for w in data.get("wavelengths", [])]
            result.intensities = [float(v) for v in data.get("intensities", [])]
            result.metadata = data.get("metadata", {}) or {}
            result.num_samples = len(result.wavelengths)
            result.format = "json"
        elif isinstance(data, list):
            arr = np.array(data, dtype=float)
            if arr.ndim == 2 and arr.shape[1] >= 2:
                result.wavelengths = arr[:, 0].tolist()
                result.intensities = arr[:, 1].tolist()
                result.num_samples = len(result.wavelengths)
                result.format = "json_array"

    def _detect_spectrometer_type(self, wavelengths: np.ndarray) -> Dict[str, Any]:
        """Detect the spectrometer type from the wavelength grid."""
        if len(wavelengths) < 2:
            return {"type": "unknown", "confidence": 0.0}
        wl_min = float(np.min(wavelengths))
        wl_max = float(np.max(wavelengths))
        resolution = float(np.mean(np.diff(np.sort(wavelengths))))
        num_points = int(len(wavelengths))
        wl_set = sorted(set(np.round(wavelengths).astype(float).tolist()))

        best_match = "unknown"
        best_score = 0
        for name, info in self.spectrometer_database.items():
            score = 0
            spec_wls = info.get("wavelengths")
            if spec_wls is not None:
                if sorted(set(float(w) for w in spec_wls)) == wl_set:
                    score += 10
                lo, hi = info["wavelength_range"]
                if lo <= wl_min <= hi and lo <= wl_max <= hi:
                    score += 2
            else:
                lo, hi = info["wavelength_range"]
                if lo <= wl_min <= hi and lo <= wl_max <= hi:
                    score += 2
                if abs(resolution - info["resolution"]) < info["resolution"] * 0.5:
                    score += 1
            expected = info.get("num_channels")
            if expected is not None:
                if num_points == expected:
                    score += 2
                elif abs(num_points - expected) <= 1:
                    score += 1
            if score > best_score:
                best_score = score
                best_match = name

        if best_score < 2:
            if wl_min > 600 and wl_max < 1200:
                best_match = "diy_raspberry" if resolution < 12 else "diy_arduino"

        return {
            "type": best_match,
            "wavelength_range": [wl_min, wl_max],
            "resolution": resolution,
            "num_points": num_points,
            "confidence": min(best_score / 4.0, 1.0) if best_match != "unknown" else 0.0,
        }


if __name__ == "__main__":
    import asyncio

    async def _test():
        agent = DataLoaderAgent()
        r = await agent.load("../NIR_Intelligence-main/data/raw/T4-T5_ALLE_mit_Brix_2.txt")
        print("success:", r.success)
        print("wl_len:", len(r.wavelengths), "ns:", r.num_samples)
        print("spec_type:", r.spectrometer_type)
        print("has Brix:", "Brix" in r.metadata)
        print("matrix shape:", len(r.intensity_matrix), "x",
              len(r.intensity_matrix[0]) if r.intensity_matrix else 0)

    asyncio.run(_test())
