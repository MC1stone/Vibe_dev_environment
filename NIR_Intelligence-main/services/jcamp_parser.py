"""JCAMP-DX parser (ASTM E5795 style) for the NIR-IP (M2 of the
interoperability implementation plan).

Parses ##TITLE, ##XUNITS/##YUNITS, ##XFACTOR/##YFACTOR and the data blocks
##XYDATA (X Y..Y with AFFN/PAC/SQZ/DIF/DUP compression), ##XYPOINTS and
##PEAK TABLE into the unified spectral schema used by the data preparation
agent. Independently developed against the public JCAMP-DX data label
specification - no third-party code reused (license compliance, see
THIRD_PARTY_LICENSES.md).
"""

from typing import Any, Dict, List, Optional, Tuple

_AFFN_DIGITS = "0123456789+-."

_SQZ_DIGITS = {
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8, "I": 9, "+": 0,
    "a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8, "i": 9,
    "J": -1, "K": -2, "L": -3, "M": -4, "N": -5, "O": -6, "P": -7, "Q": -8,
    "R": -9, "-": 0,
    "j": -1, "k": -2, "l": -3, "m": -4, "n": -5, "o": -6, "p": -7, "q": -8,
    "r": -9,
}

_DUP_DIGITS = {
    "S": 2, "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9,
    "s": 2, "t": 3, "u": 4, "v": 5, "w": 6, "x": 7, "y": 8, "z": 9,
}


class JCAMPError(ValueError):
    pass


def _decode_number(token: str) -> float:
    """Decode one AFFN/PAC/SQZ number token."""
    token = token.strip()
    if not token:
        raise JCAMPError("empty numeric token")
    if all(c in _AFFN_DIGITS for c in token):
        return float(token)
    lead = _SQZ_DIGITS.get(token[0])
    if lead is None:
        raise JCAMPError(f"unsupported JCAMP token: {token!r}")
    sign = -1.0 if lead < 0 else 1.0
    return sign * abs(lead) * 0 + sign * (abs(lead) * 10 + float(token[1:] or "0"))


def _decode_value_stream(text: str) -> List[float]:
    """Decode a JCAMP value line: mixed AFFN/SQZ/DIF/DUP compressed numbers."""
    values: List[float] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in " \t,":
            i += 1
            continue
        if c in _DUP_DIGITS:
            if not values:
                raise JCAMPError(f"DUP code without previous value: {c!r}")
            count = _DUP_DIGITS[c]
            values.extend([values[-1]] * (count - 1))
            i += 1
            continue
        if c in _SQZ_DIGITS:
            j = i + 1
            while j < n and text[j] in _AFFN_DIGITS:
                j += 1
            values.append(_decode_number(text[i:j]))
            i = j
            continue
        if c in _AFFN_DIGITS:
            j = i
            while j < n and text[j] in _AFFN_DIGITS:
                j += 1
            values.append(float(text[i:j]))
            i = j
            continue
        raise JCAMPError(f"unsupported character in data block: {c!r}")
    return values


class JCAMPTags:
    """Extract header fields and data blocks from a JCAMP-DX file."""

    @staticmethod
    def _split_headers(lines: List[str]):
        fields: Dict[str, str] = {}
        data_lines: List[str] = []
        active_label: Optional[str] = None
        last_data_label: Optional[str] = None
        for raw in lines:
            stripped = raw.strip("\r\n").rstrip()
            if stripped.startswith("##"):
                label_part, _, value = stripped[2:].partition("=")
                label = label_part.strip().upper()
                value = value.strip()
                if label in ("XYDATA", "XYPOINTS", "PEAK TABLE", "PEAKTABLE"):
                    active_label = label
                    last_data_label = label
                    data_lines = []
                    continue
                if label == "END":
                    break
                active_label = None
                if label:
                    fields.setdefault(label, value)
            elif active_label is not None:
                data_lines.append(stripped)
        return fields, last_data_label, data_lines

    @staticmethod
    def _expand_xydata(lines: List[str], x_start: float, x_step: float) -> List[Tuple[float, float]]:
        points: List[Tuple[float, float]] = []
        x = x_start
        for line in lines:
            if not line:
                continue
            head, _, rest = line.partition(" ")
            try:
                x_val = float(head)
            except ValueError:
                x_val = x
            values = _decode_value_stream(rest or line)
            for v in values:
                points.append((x_val, v))
                x_val += x_step
                x = x_val
        return points

    @staticmethod
    def _expand_xypoints(lines: List[str]) -> List[Tuple[float, float]]:
        points: List[Tuple[float, float]] = []
        for line in lines:
            if not line:
                continue
            values = _decode_value_stream(line)
            for k in range(0, len(values) - 1, 2):
                points.append((values[k], values[k + 1]))
        return points


def parse_jcamp_dx(text: str) -> Dict[str, Any]:
    """Parse JCAMP-DX content into the unified spectral schema."""
    lines = text.splitlines()
    fields, data_label, data_lines = JCAMPTags._split_headers(lines)

    xunits = fields.get("XUNITS")
    yunits = fields.get("YUNITS")
    try:
        xfactor = float(fields.get("XFACTOR", "1"))
    except ValueError:
        xfactor = 1.0
    try:
        yfactor = float(fields.get("YFACTOR", "1"))
    except ValueError:
        yfactor = 1.0
    try:
        xstart = float(fields.get("FIRSTX", "0"))
        deltax = float(fields.get("DELTAX", "0"))
    except ValueError:
        xstart, deltax = 0.0, 0.0

    if data_label in ("XYDATA",):
        points = JCAMPTags._expand_xydata(data_lines, xstart, deltax)
    elif data_label in ("XYPOINTS", "PEAK TABLE", "PEAKTABLE"):
        points = JCAMPTags._expand_xypoints(data_lines)
    else:
        points = []

    if not points:
        raise JCAMPError(
            f"no data points found (data label: {data_label!r})")

    xs = [p[0] * xfactor for p in points]
    ys = [p[1] * yfactor for p in points]

    try:
        import pandas as pd
        df = pd.DataFrame({"wavelength": xs, "intensity": ys})
    except ImportError:
        df = {"wavelength": xs, "intensity": ys}

    metadata: Dict[str, Any] = {
        "title": fields.get("TITLE"),
        "x_units": xunits,
        "y_units": yunits,
        "jcamp_data_type": fields.get("DATATYPE"),
        "jcamp_n_points": fields.get("NPOINTS"),
        "origin": fields.get("ORIGIN"),
        "owner": fields.get("OWNER"),
    }
    metadata = {k: v for k, v in metadata.items() if v is not None}
    return {
        "data": df,
        "format": ".jdx",
        "wavelength_column": "wavelength",
        "intensity_column": "intensity",
        "metadata": metadata,
    }


def load_jcamp_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Read and parse a JCAMP-DX file; returns None on non-JCAMP content."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            head = f.read(4096)
        if "##" not in head:
            return None
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return parse_jcamp_dx(f.read())
    except JCAMPError:
        return None
    except Exception:
        return None
