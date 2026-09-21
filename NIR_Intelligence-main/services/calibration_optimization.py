# NIR Intelligence Platform - Calibration optimization protocol (roadmap S7, MO 8/9/15)
# Wraps Optuna-based hyperparameter studies for calibrations. Optuna is an
# optional dependency: when not installed, the protocol records the planned
# optimization and reports it as deferred instead of failing.

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Service.CalibrationOptimization")

try:
    import optuna

    OPTUNA_AVAILABLE = True
except ImportError:
    optuna = None
    OPTUNA_AVAILABLE = False

DEFAULT_METHODS = ["PLS", "PCR", "SVM", "RandomForest", "XGBoost", "CNN"]


@dataclass
class TrialRecord:
    """One recorded optimization trial"""

    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    score: Optional[float] = None
    state: str = "complete"


@dataclass
class OptimizationProtocol:
    """Protocol of one calibration optimization run (Abschlussbericht section)"""

    objective: str
    methods: List[str] = field(default_factory=list)
    n_trials: int = 0
    trials: List[TrialRecord] = field(default_factory=list)
    best_method: Optional[str] = None
    best_params: Dict[str, Any] = field(default_factory=dict)
    best_score: Optional[float] = None
    optuna_used: bool = False
    status: str = "pending"

    def summary(self) -> Dict[str, Any]:
        return {
            "objective": self.objective,
            "methods": self.methods,
            "n_trials": self.n_trials,
            "best_method": self.best_method,
            "best_params": self.best_params,
            "best_score": self.best_score,
            "optuna_used": self.optuna_used,
            "status": self.status,
        }


class CalibrationOptimizationService:
    """Optuna-based optimization protocol for calibrations (S7).

    The objective function is provided by the caller (Calibration Agent):
    it receives a params dict and returns a float score to maximize.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.n_trials = int(self.config.get("n_trials", 20))

    def optimize(self, objective: Callable[[Dict[str, Any]], float],
                 search_space: Dict[str, List[Any]],
                 methods: Optional[List[str]] = None,
                 objective_name: str = "r2") -> OptimizationProtocol:
        """Run the optimization and return the protocol.

        objective: callable(params) -> float (higher is better)
        search_space: param name -> list of candidate values
        """
        methods = methods or DEFAULT_METHODS
        protocol = OptimizationProtocol(objective=objective_name, methods=methods)

        if not OPTUNA_AVAILABLE:
            protocol.status = "deferred"
            protocol.optuna_used = False
            logger.info("Optuna not installed - optimization deferred (protocol only)")
            return protocol

        optuna.logging.set_verbosity(optuna.logging.WARNING)

        def wrapped_objective(trial):
            params = {}
            for name, candidates in search_space.items():
                if all(isinstance(v, bool) for v in candidates):
                    params[name] = trial.suggest_categorical(name, candidates)
                elif all(isinstance(v, int) and not isinstance(v, bool) for v in candidates):
                    params[name] = trial.suggest_int(name, min(candidates), max(candidates))
                elif all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in candidates):
                    params[name] = trial.suggest_float(name, min(candidates), max(candidates))
                else:
                    params[name] = trial.suggest_categorical(name, candidates)
            score = objective(params)
            trial_record = TrialRecord(method=params.get("method", "unknown"),
                                       params=dict(params), score=float(score))
            protocol.trials.append(trial_record)
            protocol.n_trials += 1
            if protocol.best_score is None or score > protocol.best_score:
                protocol.best_score = float(score)
                protocol.best_params = dict(params)
                protocol.best_method = params.get("method", "unknown")
            return score

        study = optuna.create_study(direction="maximize",
                                    sampler=optuna.samplers.RandomSampler(seed=42))
        if "method" not in search_space:
            search_space = {**search_space, "method": methods}
        study.optimize(wrapped_objective, n_trials=self.n_trials)

        protocol.optuna_used = True
        protocol.status = "complete"
        return protocol

    def status(self) -> Dict[str, Any]:
        return {
            "service": "calibration_optimization",
            "optuna_available": OPTUNA_AVAILABLE,
            "n_trials": self.n_trials,
        }


def create_calibration_optimization(config: Optional[Dict[str, Any]] = None) -> CalibrationOptimizationService:
    """Factory used by the CalibrationAgent to get the optimization service"""
    return CalibrationOptimizationService(config=config)
