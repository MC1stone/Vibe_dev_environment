# NIR Intelligence Platform - Statistical Analysis Agent
# Handles traditional statistical analysis of NIR spectroscopy data (MO 5).
# Real implementation: PCA, PLS, PCR, ANOVA and cluster analysis computed
# with scikit-learn / scipy on the supplied spectra. Methods that cannot run
# (missing target values) are reported as skipped instead of simulated.

from typing import Any, Dict, List, Optional

import numpy as np

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


def _extract_matrix(spectra: Any) -> Optional[np.ndarray]:
    """Extract an (n_samples, n_points) matrix (see sensor_quality_agent)."""
    if spectra is None:
        return None
    if isinstance(spectra, np.ndarray):
        return np.asarray(spectra, dtype=float) if spectra.size else None
    if isinstance(spectra, dict):
        if spectra.get("data") is None and spectra.get("intensities") is None:
            return None
        spectra = [spectra]
    if not isinstance(spectra, (list, tuple)) or len(spectra) == 0:
        return None
    rows = []
    for item in spectra:
        if isinstance(item, dict):
            data = item.get("data")
            if data is None:
                intensities = item.get("intensities")
                if intensities is None:
                    return None
                rows.append(np.asarray(intensities, dtype=float))
            else:
                import pandas as pd

                if isinstance(data, pd.DataFrame):
                    column = item.get("intensity_column", "intensity")
                    if column not in data.columns:
                        column = data.columns[-1]
                    rows.append(data[column].to_numpy(dtype=float))
                else:
                    rows.append(np.asarray(data, dtype=float))
        else:
            rows.append(np.asarray(item, dtype=float))
    if any(row.size == 0 for row in rows):
        return None
    if len({row.size for row in rows}) != 1:
        return None
    return np.vstack(rows)


def _replicate_structure_assessment(y: np.ndarray) -> Optional[Dict[str, Any]]:
    """Detect replicate structure in calibration targets (learned from the
    T4/T5 tomato comparison, issue #65 follow-up): few unique reference
    values spread over many rows mean multiple spectra share one target
    (replicas of the same object). Random KFold can then split replicas of
    the same object across train and test folds, which inflates R^2. The
    recommended fix is a group-wise CV keyed by the measured object - it
    is only recommended here, never applied automatically."""
    if y is None or y.size < 8:
        return None
    unique, counts = np.unique(y, return_counts=True)
    if unique.size < 3:
        return None
    replicas_per_target = counts.mean()
    if unique.size >= y.size * 0.9 or replicas_per_target < 2.0:
        return None
    return {
        "unique_reference_values": int(unique.size),
        "mean_replicas_per_reference": round(float(replicas_per_target), 2),
        "max_replicas_per_reference": int(counts.max()),
        "risk": (
            "replica_overlap_in_cv"
            if unique.size < y.size * 0.25 else "moderate_replica_overlap"
        ),
        "recommendation": (
            "Kalibrationszeilen sind Replikate je Messobjekt (eindeutige "
            "Referenzwerte: {n_unique} auf {n_rows} Zeilen). Kreuzvalidierung "
            "kann Replikate desselben Objekts auf Train- und Testfold "
            "verteilen und R\u00b2 optimistisch machen. Empfohlene Option: "
            "Group-wise CV (Replikate je Objekt strikt in denselben Fold), "
            "um generalisierbare G\u00fcte zu messen."
        ).format(n_unique=int(unique.size), n_rows=int(y.size)),
    }


class StatisticalAnalysisAgent(BaseAgent):
    """Agent for performing statistical analysis on NIR data.

    context keys:
    - spectra: samples to analyze (vectors or unified schema dicts)
    - reference_values / y: target values for PLS/PCR (required for those)
    - methods: list of methods to run (default PCA, PLS, PCR, ANOVA, ClusterAnalysis)
    """

    def __init__(self, **kwargs):
        super().__init__(name="StatisticalAnalysisAgent", version="2.0.0", **kwargs)
        self.dependencies = ["numpy", "pandas", "scikit-learn", "scipy"]
        self.methods = kwargs.get("methods", ["PCA", "PLS", "PCR", "ANOVA", "ClusterAnalysis"])
        self.default_components = int(kwargs.get("default_components", 10))
        self.validation_method = kwargs.get("validation_method", "cross_validation")
        self.cv_folds = int(kwargs.get("cv_folds", 5))
        self.random_state = int(kwargs.get("random_state", 42))

    def _run_pca(self, matrix: np.ndarray) -> Dict[str, Any]:
        from sklearn.decomposition import PCA

        n_components = int(min(self.default_components, min(matrix.shape)))
        pca = PCA(n_components=n_components)
        transformed = pca.fit(matrix)
        variance = pca.explained_variance_ratio_
        return {
            "n_components": n_components,
            "variance_explained": [float(v) for v in variance],
            "cumulative_variance_explained": float(np.cumsum(variance)[-1]),
            "samples_transformed": int(transformed.transform(matrix).shape[0]),
        }

    def _run_pls(self, matrix: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        from sklearn.cross_decomposition import PLSRegression
        from sklearn.model_selection import KFold, cross_val_score
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        n_components = int(min(self.default_components, matrix.shape[0] - 1, matrix.shape[1]))
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("pls", PLSRegression(n_components=max(1, n_components))),
        ])
        folds = min(self.cv_folds, len(y))
        splitter = KFold(n_splits=folds, shuffle=True, random_state=self.random_state)
        scores = cross_val_score(pipeline, matrix, y, cv=splitter, scoring="r2")
        return {
            "n_components": max(1, n_components),
            "feature_scaling": "standardized",
            "r2_scores": [float(s) for s in scores],
            "mean_r2": float(np.mean(scores)),
            "validation": self.validation_method,
            "cv_folds": folds,
        }

    def _run_pcr(self, matrix: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        from sklearn.decomposition import PCA
        from sklearn.linear_model import LinearRegression
        from sklearn.model_selection import KFold, cross_val_score
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        n_components = int(min(self.default_components, matrix.shape[0] - 1, matrix.shape[1]))
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("pca", PCA(n_components=max(1, n_components))),
            ("regression", LinearRegression()),
        ])
        folds = min(self.cv_folds, len(y))
        splitter = KFold(n_splits=folds, shuffle=True, random_state=self.random_state)
        scores = cross_val_score(pipeline, matrix, y, cv=splitter, scoring="r2")
        return {
            "n_components": max(1, n_components),
            "r2_scores": [float(s) for s in scores],
            "mean_r2": float(np.mean(scores)),
            "validation": self.validation_method,
            "cv_folds": folds,
        }

    def _run_anova(self, matrix: np.ndarray, y: Optional[np.ndarray]) -> Dict[str, Any]:
        from scipy import stats

        if y is None or len(np.unique(y)) < 2:
            return {"status": "skipped", "reason": "ANOVA needs grouping reference values"}
        groups = [matrix[y == group] for group in np.unique(y)]
        f_stats, p_values = [], []
        for column in range(matrix.shape[1]):
            f, p = stats.f_oneway(*[group[:, column] for group in groups])
            f_stats.append(float(f))
            p_values.append(float(p))
        significant = int(np.sum(np.array(p_values) < 0.05))
        return {
            "groups_compared": int(len(groups)),
            "features_tested": int(matrix.shape[1]),
            "significant_features": significant,
            "min_p_value": float(np.min(p_values)),
            "max_f_statistic": float(np.max(f_stats)),
        }

    def _run_cluster(self, matrix: np.ndarray) -> Dict[str, Any]:
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score

        max_clusters = int(min(10, matrix.shape[0] - 1))
        if max_clusters < 2:
            return {"status": "skipped", "reason": "not enough samples for clustering"}
        k = 3 if max_clusters >= 3 else max_clusters
        k = min(k, max_clusters)
        labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(matrix)
        silhouette = silhouette_score(matrix, labels) if len(set(labels)) > 1 else -1.0
        return {
            "k": k,
            "labels": [int(label) for label in labels],
            "cluster_sizes": {str(i): int(c) for i, c in zip(*np.unique(labels, return_counts=True))},
            "silhouette_score": float(silhouette),
        }

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute statistical analysis workflow."""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting statistical analysis execution")

            context = context or {}
            matrix = _extract_matrix(context.get("spectra", context.get("spectral_data")))
            if matrix is None:
                return self._create_success_output({
                    "methods_applied": [],
                    "status": "no_data",
                    "message": "No spectra supplied for statistical analysis",
                })

            y = context.get("reference_values", context.get("y"))
            if y is not None:
                y = np.asarray(y, dtype=float).ravel()
                if y.size != matrix.shape[0]:
                    y = None

            methods = list(context.get("methods", self.methods))
            results: Dict[str, Any] = {
                "methods_applied": [],
                "methods_skipped": [],
                "num_samples": int(matrix.shape[0]),
                "data_points": int(matrix.shape[1]),
                "method_results": {},
            }

            replicate_assessment = _replicate_structure_assessment(y)
            if replicate_assessment is not None:
                results["replicate_structure"] = replicate_assessment

            if matrix.shape[0] == 1:
                # Single spectrum: PCA/PLS/clustering need multiple samples.
                # Report descriptive statistics plus robust outlier detection
                # (modified z-score on the median/MAD) so a single DIY
                # spectrum still gets a real, meaningful statistics section.
                spectrum = matrix[0]
                median = float(np.median(spectrum))
                mad = float(np.median(np.abs(spectrum - median)))
                modified_z = (
                    0.6745 * (spectrum - median) / mad if mad > 0
                    else np.zeros_like(spectrum)
                )
                # A spectrum has a wide genuine dynamic range (peaks), so a
                # global z-score misses single-band spikes. Compare each band
                # against the median of its LOCAL NEIGHBOURS ONLY (the tested
                # band is excluded from its own reference window): a spike
                # deviates strongly from its neighbours even when the global
                # MAD is large.
                if spectrum.size >= 5:
                    spectrum_f = spectrum.astype(float)
                    neighbours = []
                    for i in range(spectrum_f.size):
                        lo = max(0, i - 3)
                        hi = min(spectrum_f.size, i + 4)
                        window_values = np.concatenate([
                            spectrum_f[lo:i], spectrum_f[i + 1:hi]
                        ])
                        neighbours.append(float(np.median(window_values)))
                    rolling = np.array(neighbours)
                    residual = spectrum_f - rolling
                    residual_mad = float(np.median(np.abs(residual)))
                    if residual_mad > 0:
                        local_z = 0.6745 * residual / residual_mad
                        outlier_mask = np.abs(local_z) > 3.5
                    else:
                        # Degenerate MAD (e.g. mostly-flat spectrum): fall back
                        # to any residual larger than 5% of the signal scale.
                        threshold = 0.05 * float(np.abs(spectrum_f).max() or 1.0)
                        outlier_mask = np.abs(residual) > threshold
                    outlier_indices = [int(i) for i in np.flatnonzero(outlier_mask)]
                    outlier_basis = "local modified z-score (leave-one-out median)"
                    outlier_scores = [float(residual[i]) for i in outlier_indices]
                else:
                    outlier_indices = []
                    outlier_basis = "too few points for outlier detection"
                    outlier_scores = []
                global_z_outliers = (
                    [int(i) for i in np.flatnonzero(np.abs(modified_z) > 3.5)]
                    if mad > 0 else []
                )
                results["methods_applied"].append("DescriptiveStatistics")
                results["method_results"]["DescriptiveStatistics"] = {
                    "num_points": int(spectrum.size),
                    "mean": float(np.mean(spectrum)),
                    "std": float(np.std(spectrum)),
                    "median": median,
                    "mad": mad,
                    "min": float(np.min(spectrum)),
                    "max": float(np.max(spectrum)),
                    "q1": float(np.percentile(spectrum, 25)),
                    "q3": float(np.percentile(spectrum, 75)),
                    "dynamic_range": float(np.max(spectrum) - np.min(spectrum)),
                    "outliers": {
                        "method": outlier_basis,
                        "indices": outlier_indices,
                        "values": [float(spectrum[i]) for i in outlier_indices],
                        "modified_z_scores": outlier_scores,
                        "global_z_outlier_indices": global_z_outliers,
                    },
                    "status": "ok",
                }
                results["status"] = "ok"
                self.status = AgentStatus.COMPLETED
                return self._create_success_output(results)

            for method in methods:
                method_name = str(method).strip()
                try:
                    if method_name == "PCA":
                        outcome = self._run_pca(matrix)
                    elif method_name == "PLS":
                        if y is None:
                            results["methods_skipped"].append(
                                {"method": "PLS", "reason": "reference values required"})
                            continue
                        outcome = self._run_pls(matrix, y)
                    elif method_name == "PCR":
                        if y is None:
                            results["methods_skipped"].append(
                                {"method": "PCR", "reason": "reference values required"})
                            continue
                        outcome = self._run_pcr(matrix, y)
                    elif method_name == "ANOVA":
                        outcome = self._run_anova(matrix, y)
                        if outcome.get("status") == "skipped":
                            results["methods_skipped"].append(
                                {"method": "ANOVA", "reason": outcome["reason"]})
                            continue
                    elif method_name in ("ClusterAnalysis", "Clustering"):
                        outcome = self._run_cluster(matrix)
                        if outcome.get("status") == "skipped":
                            results["methods_skipped"].append(
                                {"method": method_name, "reason": outcome["reason"]})
                            continue
                    else:
                        results["methods_skipped"].append(
                            {"method": method_name, "reason": "unknown method"})
                        continue
                    results["method_results"][method_name] = outcome
                    results["methods_applied"].append(method_name)
                except Exception as exc:
                    results["methods_skipped"].append(
                        {"method": method_name, "reason": str(exc)})

            results["status"] = "ok"
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(results)
        except Exception as e:
            return self._handle_error(e)
