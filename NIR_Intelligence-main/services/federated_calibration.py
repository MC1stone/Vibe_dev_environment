# NIR Intelligence Platform - Federated calibration models (FL2)
# Extends the FL1 flwr runtime with real chemometric calibration models:
# instead of only the S9 ridge core, clients train a local PLS calibration
# (scikit-learn, already a platform dependency) on their own spectra and
# transmit ONLY the model coefficients (federated model averaging of the
# regression hyperplane). Sharding uses the OP15 provenance dimensions
# (instrument_type / sample_type) - the same non-IID dimensions as the
# spectral database. Global model aggregation is example-weighted FedAvg,
# mirroring the S9 core semantics. Raw spectra never leave the client.

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("Service.FederatedCalibration")

try:
    from sklearn.cross_decomposition import PLSRegression
    from sklearn.exceptions import NotFittedError

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .federated_learning_service import ModelUpdate


@dataclass
class CalibrationShard:
    """One client's local calibration data (stays local).

    Provenance group (instrument_type / sample_type of the OP15
    SpectrumRecord) doubles as the non-IID shard dimension.
    """

    x: np.ndarray  # spectra: (n_samples, n_channels)
    y: np.ndarray  # reference values (e.g. brix): (n_samples,)
    instrument_type: str = "unknown"
    sample_type: str = "unknown"

    def size(self) -> int:
        return int(self.x.shape[0])

    @property
    def group(self) -> str:
        return f"{self.instrument_type}:{self.sample_type}"


@dataclass
class FederatedCalibrationResult:
    round_id: int
    global_coefficients: Optional[np.ndarray] = None  # (n_channels,)
    global_intercept: float = 0.0
    participating_clients: List[str] = field(default_factory=list)
    total_examples: int = 0
    rmse: Optional[float] = None
    strategy: str = "fedavg-pls"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_id": self.round_id,
            "participating_clients": self.participating_clients,
            "total_examples": self.total_examples,
            "rmse": self.rmse,
            "strategy": self.strategy,
            "n_channels": int(self.global_coefficients.shape[0])
            if self.global_coefficients is not None else None,
            "privacy_note": "only parameter updates shared - raw data stays local",
        }


class PLSCalibrationClient:
    """Local PLS calibration on one client's shard.

    The transmitted payload is ONLY (coefficients, intercept, n_examples) -
    never the spectra. Fitting is the standard PLS regression from the
    platform's calibration stack (task_definition.yaml: pls).
    """

    def __init__(self, client_id: str, shard: CalibrationShard,
                 n_components: int = 2):
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn is not installed - PLS calibration unavailable")
        self.client_id = client_id
        self.shard = shard
        self.n_components = max(1, min(int(n_components), shard.x.shape[1]))

    def fit_local(self) -> Tuple[np.ndarray, float, int, Dict[str, float]]:
        """Fit the local PLS calibration and return the parameter update."""
        x = self.shard.x.astype(np.float64)
        y = self.shard.y.astype(np.float64).ravel()
        if x.shape[0] < 2:
            raise ValueError(f"client {self.client_id} has too few samples for PLS")
        pls = PLSRegression(n_components=self.n_components)
        pls.fit(x, y)
        coefficients = np.asarray(pls.coef_, dtype=np.float64).ravel()
        intercept = _pls_intercept(pls, coefficients, x, y)
        pred = x @ coefficients + intercept
        rmse = float(np.sqrt(np.mean((pred - y) ** 2)))
        return coefficients, intercept, self.shard.size(), {
            "local_rmse": rmse, "group": self.shard.group,
        }


def _pls_intercept(pls: "PLSRegression", coef: np.ndarray,
                   x: np.ndarray, y: np.ndarray) -> float:
    """PLS regression hyperplane intercept: y = x @ coef + intercept."""
    residuals = y.astype(np.float64) - x.astype(np.float64) @ coef
    return float(np.mean(residuals))


class FederatedPLSAggregator:
    """Example-weighted FedAvg of PLS regression hyperplanes.

    Mirrors the S9 FedAvgAggregator semantics: clients are weighted by
    their local example counts; the aggregated hyperplane is the weighted
    average of the client hyperplanes.
    """

    def __init__(self, strategy: str = "fedavg-pls"):
        if strategy not in ("fedavg-pls",):
            raise ValueError(f"unknown federated calibration strategy: {strategy}")
        self.strategy = strategy

    def aggregate(self, updates: List[Dict[str, Any]]) -> Optional[Tuple[np.ndarray, float]]:
        if not updates:
            return None
        shapes = {tuple(u["coefficients"].shape) for u in updates}
        if len(shapes) != 1:
            raise ValueError(f"client coefficient shapes differ: {shapes}")
        total = sum(u["num_examples"] for u in updates)
        if total == 0:
            raise ValueError("no examples across updates")
        coef = np.zeros_like(updates[0]["coefficients"], dtype=np.float64)
        intercept = 0.0
        for u in updates:
            w = u["num_examples"] / total
            coef += w * u["coefficients"]
            intercept += w * u["intercept"]
        return coef, intercept


class FederatedCalibrationService:
    """Orchestrates federated calibration rounds over PLS clients (FL2).

    Simulation/standalone orchestration of the same contract the FL1
    flwr ClientApp uses; the production transport (flower-superlink/
    supernode) carries the identical payloads.
    """

    def __init__(self, n_components: int = 2):
        self.n_components = n_components
        self.aggregator = FederatedPLSAggregator()
        self.round_id = 0
        self.global_coefficients: Optional[np.ndarray] = None
        self.global_intercept: float = 0.0
        self.history: List[FederatedCalibrationResult] = []

    def run_round(self, shards: List[CalibrationShard],
                  reference_x: Optional[np.ndarray] = None,
                  ) -> FederatedCalibrationResult:
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn is not installed - deferred")
        updates = []
        for shard in shards:
            client = PLSCalibrationClient(client_id=shard.group, shard=shard,
                                          n_components=self.n_components)
            coef, intercept, n, metrics = client.fit_local()
            payload_row = np.concatenate([coef.ravel(), [intercept]])
            if reference_x is not None:
                for row in reference_x[: min(5, reference_x.shape[0])]:
                    if np.array_equal(payload_row, row):
                        raise RuntimeError(
                            "privacy audit failed: payload matches a raw data row")
            updates.append({"client_id": shard.group, "coefficients": coef,
                            "intercept": intercept, "num_examples": n,
                            "metrics": metrics})
        aggregated = self.aggregator.aggregate(updates)
        if aggregated is None:
            raise ValueError("no client updates to aggregate")
        coef, intercept = aggregated
        self.round_id += 1
        self.global_coefficients = coef
        self.global_intercept = intercept
        result = FederatedCalibrationResult(
            round_id=self.round_id,
            global_coefficients=coef,
            global_intercept=intercept,
            participating_clients=[u["client_id"] for u in updates],
            total_examples=sum(u["num_examples"] for u in updates),
        )
        self.history.append(result)
        return result

    def global_rmse(self, x: np.ndarray, y: np.ndarray) -> Optional[float]:
        if self.global_coefficients is None:
            return None
        pred = x.astype(np.float64) @ self.global_coefficients + self.global_intercept
        return float(np.sqrt(np.mean((pred - y.astype(np.float64).ravel()) ** 2)))

    def status(self) -> Dict[str, Any]:
        return {
            "service": "federated_calibration",
            "model": "pls",
            "n_components": self.n_components,
            "sklearn_available": SKLEARN_AVAILABLE,
            "rounds_completed": len(self.history),
            "global_model_initialized": self.global_coefficients is not None,
        }


def shard_spectra_database(records: List[Dict[str, Any]],
                           dimension: str = "instrument_type",
                           ) -> List[CalibrationShard]:
    """Shard OP15 SpectrumRecord-like dicts into non-IID calibration shards.

    Each record needs wavelengths/intensities (or x), a reference value (y)
    and the provenance dimension used for grouping. Records without a
    reference value are skipped (they cannot train a calibrator - honest
    skip, no invention).
    """
    shards: Dict[str, CalibrationShard] = {}
    skipped = 0
    for rec in records:
        y = rec.get("reference_value")
        x = rec.get("x")
        if x is None:
            intens = rec.get("intensities")
            if intens is None:
                skipped += 1
                continue
            x = np.asarray(intens, dtype=np.float64)
        if y is None:
            skipped += 1
            continue
        group_key = str(rec.get(dimension, "unknown") or "unknown")
        if group_key not in shards:
            shards[group_key] = CalibrationShard(
                x=np.asarray(x, dtype=np.float64).reshape(1, -1) if np.asarray(x).ndim == 1 else np.asarray(x, dtype=np.float64),
                y=np.asarray([y], dtype=np.float64),
                instrument_type=str(rec.get("instrument_type", "unknown") or "unknown"),
                sample_type=str(rec.get("sample_type", "unknown") or "unknown"),
            )
        else:
            shard = shards[group_key]
            xi = np.asarray(x, dtype=np.float64)
            if xi.ndim == 1:
                xi = xi.reshape(1, -1)
            shard.x = np.vstack([shard.x, xi])
            shard.y = np.concatenate([shard.y, [float(y)]])
    if skipped:
        logger.info("shard_spectra_database: %s records skipped (no reference value/spectrum)", skipped)
    return list(shards.values())
