# NIR Intelligence Platform - Federated privacy: DP + secure aggregation (FL3)
# Makes the privacy levels of the FlowerAgent configuration real instead of
# simulated: clients clip their parameter update to an L2 bound and add
# calibrated Gaussian noise (DP-SGD style, epsilon/delta accounting per
# round), the service tracks the privacy budget. Secure aggregation is
# evaluated against the flwr runtime: if the installed flwr ships a usable
# SecAgg workflow it is reported as available, otherwise the status is an
# honest 'unavailable' - nothing is simulated (OP14/OP18 truthfulness rule).

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("Service.FederatedPrivacy")


@dataclass
class DPConfig:
    """Differential privacy configuration (mirrors FederatedLearningConfig)."""

    epsilon: float = 1.0
    delta: float = 1e-5
    clip_norm: float = 1.0
    noise_multiplier: Optional[float] = None  # default: sigma = epsilon-based

    def __post_init__(self):
        if self.epsilon <= 0:
            raise ValueError("epsilon must be > 0")
        if not 0 < self.delta < 1:
            raise ValueError("delta must be in (0, 1)")
        if self.clip_norm <= 0:
            raise ValueError("clip_norm must be > 0")

    @property
    def sigma(self) -> float:
        """Gaussian noise std derived from (epsilon, delta).

        Standard Gaussian mechanism bound: sigma >= sqrt(2 * ln(1.25/delta)) / epsilon.
        """
        if self.noise_multiplier is not None:
            return float(self.noise_multiplier)
        return math.sqrt(2.0 * math.log(1.25 / self.delta)) / self.epsilon


def clip_update(params: np.ndarray, clip_norm: float) -> np.ndarray:
    """L2-clip a parameter update to the given bound (sensitivity bound)."""
    norm = float(np.linalg.norm(params))
    if norm <= clip_norm or norm == 0.0:
        return params
    return params * (clip_norm / norm)


class DPNoiser:
    """Adds calibrated Gaussian noise to a clipped parameter update."""

    def __init__(self, config: DPConfig, seed: Optional[int] = None):
        self.config = config
        self.rng = np.random.default_rng(seed)

    def privatize(self, params: np.ndarray, num_examples: int) -> np.ndarray:
        clipped = clip_update(params, self.config.clip_norm)
        sigma = self.config.sigma
        noise = self.rng.normal(0.0, sigma, size=clipped.shape)
        return clipped + noise


@dataclass
class PrivacyBudgetRecord:
    round_id: int
    epsilon: float
    delta: float
    sigma: float
    clip_norm: float


class PrivacyAccountant:
    """Tracks the cumulative privacy budget over federated rounds.

    Uses the simple (composition) bound: total epsilon = k * epsilon_round
    for k rounds of the Gaussian mechanism (honest upper bound; advanced
    composition would tighten it but needs no extra dependencies here).
    """

    def __init__(self, config: DPConfig):
        self.config = config
        self.rounds: List[PrivacyBudgetRecord] = []

    def record_round(self, round_id: int) -> PrivacyBudgetRecord:
        rec = PrivacyBudgetRecord(
            round_id=round_id,
            epsilon=self.config.epsilon,
            delta=self.config.delta,
            sigma=self.config.sigma,
            clip_norm=self.config.clip_norm,
        )
        self.rounds.append(rec)
        return rec

    @property
    def total_epsilon(self) -> float:
        return sum(r.epsilon for r in self.rounds)

    @property
    def total_delta(self) -> float:
        return 1.0 - math.prod(1.0 - r.delta for r in self.rounds) if self.rounds else 0.0

    def budget_exhausted(self, max_epsilon: Optional[float] = None) -> bool:
        if max_epsilon is None:
            return False
        return self.total_epsilon >= max_epsilon

    def status(self) -> Dict[str, Any]:
        return {
            "mechanism": "gaussian",
            "rounds_recorded": len(self.rounds),
            "total_epsilon": self.total_epsilon,
            "total_delta": self.total_delta,
            "sigma": self.config.sigma,
            "clip_norm": self.config.clip_norm,
        }


def secure_aggregation_available() -> Dict[str, Any]:
    """Honest availability report for secure aggregation via flwr.

    Checks the installed flwr for a usable SecAgg workflow; reports
    'unavailable' (with reason) instead of simulating it if not present.
    """
    try:
        import flwr  # noqa: F401
    except ImportError:
        return {"available": False, "status": "unavailable",
                "reason": "flwr not installed"}
    try:
        from flwr.server.workflow import SecAggPlusWorkflow  # noqa: F401
        return {"available": True, "status": "available",
                "workflow": "SecAggPlusWorkflow",
                "note": "server-side blind aggregation over flwr SecAggPlus"}
    except ImportError:
        pass
    try:
        from flwr.server.superlink.fleet.secagg import secagg_workflow  # noqa: F401
        return {"available": True, "status": "available",
                "workflow": "flwr.secagg"}
    except ImportError:
        pass
    return {"available": False, "status": "unavailable",
            "reason": "installed flwr ships no usable SecAgg workflow"}


class DPFederatedClientMixin:
    """Mixin adding DP to any client exposing fit_local-style updates.

    Applied by the FL2 calibration clients and the S9 ridge core alike:
    the parameter update is clipped and noised BEFORE it leaves the client.
    """

    def privatize_update(self, params: np.ndarray, num_examples: int,
                         noiser: Optional[DPNoiser] = None) -> np.ndarray:
        if noiser is None:
            return params
        return noiser.privatize(params, num_examples)


def dp_utility_cost(clean_params: np.ndarray, dp_params: np.ndarray) -> float:
    """Honest utility measure: L2 distance between clean and privatized
    parameter updates (reported, not hidden)."""
    return float(np.linalg.norm(np.asarray(dp_params) - np.asarray(clean_params)))
