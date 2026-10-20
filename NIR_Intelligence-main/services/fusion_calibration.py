"""OP63 Stufe 3: Vergleichende Kalibration des Fusion-Analyse-Zweigs.

Fachliche Frage (PO, 2026-10-16): Bringt die Zusammenfuehrung zweier
Projekte (z. B. unterschiedliche Operatoren/Tomaten, gleicher Sensor)
einen Kalibrationsgewinn - oder schadet die Heterogenitaet? Dazu werden
drei Kalibrationen gerechnet und gegenuebergestellt:

  1. Projekt A einzeln
  2. Projekt B einzeln
  3. kombiniert (Fusionsprojekt)

Vergleichskennzahlen: R2 (CV), RMSECV, RPD je Kalibration. Dazu ein
statistischer Test der Residuen pro Herkunftsgruppe (Levene-Test auf
Varianzgleichheit + t-Test auf Residuen-Mittelwert-Differenz), der
beantwortet, ob die Operator-/Proben-Differenz die Kalibration
signifikant beeinflusst.

Wiederverwendung: CalibrationAgent (PLS, sklearn, bereits im Stack) -
keine neue Abhaengigkeit, keine Kopie der Kalibrationslogik.
"""
import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Methoden fuer den Vergleich: bewusst nur PLS - das ist das Standard-
# NIR-Kalibrationsmodell (Mission Statement: PLS/PCR); weitere Methoden
# waeren zulaessig, aber der Vergleich soll klein und interpretierbar
# bleiben (Anti-Code-Creep).
COMPARISON_METHOD = "PLS"


def _collect_samples(project) -> Dict[str, Any]:
    """Kalibrationsfaehige Daten eines Projekts aus dem Vorbereitungs-
    bericht ziehen (calibration_samples/reference_values werden beim
    Ingest je Datensatz erkannt). Liefert {'samples': [...], 'targets':
    [...], 'target_name': str|None, 'file_names': [...] }."""
    samples: List[List[float]] = []
    targets: List[float] = []
    file_names: List[str] = []
    target_name = None
    prep = project.preparation_report or {}
    for dataset in prep.get('datasets', []):
        if not dataset.get('usable'):
            continue
        ds_samples = dataset.get('calibration_samples') or []
        ds_targets = dataset.get('reference_values') or []
        if not ds_samples or not ds_targets:
            continue
        if len(ds_samples) != len(ds_targets):
            continue
        samples.extend(ds_samples)
        targets.extend(float(t) for t in ds_targets)
        file_names.extend(
            [dataset.get('file_name', '')] * len(ds_samples))
        target_name = target_name or dataset.get('target_name')
    return {'samples': samples, 'targets': targets,
            'target_name': target_name, 'file_names': file_names}


def _fit_calibration(samples: List[List[float]], targets: List[float],
                     cv_folds: int = 5) -> Optional[Dict[str, Any]]:
    """Eine PLS-Kalibration via CalibrationAgent rechnen (Wiederverwendung
    der produktiven Kalibrationslogik inkl. Pipeline/Scaling/CV)."""
    if len(samples) < 12 or len(samples) != len(targets):
        return None
    try:
        from agents.calibration_agent import CalibrationAgent
        agent = CalibrationAgent(methods=[COMPARISON_METHOD],
                                 cv_folds=cv_folds)
        output = agent.execute({
            'spectra': samples,
            'reference_values': targets,
            'methods': [COMPARISON_METHOD],
        })
        data = getattr(output, 'data', None) or {}
        method_results = data.get('method_results') or {}
        result = method_results.get(COMPARISON_METHOD)
        if isinstance(result, dict) and result.get('status') == 'ok':
            return result
        return None
    except Exception:
        logger.exception('Single calibration fit failed (non-fatal)')
        return None


def _residuals_by_group(combined_samples, combined_targets,
                        group_labels) -> Optional[Dict[str, Any]]:
    """Residuen der kombinierten Kalibration pro Herkunftsgruppe.

    Fit per PLS auf den kombinierten Daten (sklearn-Pipeline identisch
    zum CalibrationAgent: StandardScaler + PLSRegression), Vorhersage
    auf denselben Daten, Residuen je Gruppe gesammelt. Liefert
    {'groups': {label: [residuen]}, 'fitted': bool}."""
    try:
        from sklearn.cross_decomposition import PLSRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline
        X = np.asarray(combined_samples, dtype=float)
        y = np.asarray(combined_targets, dtype=float)
        if X.ndim != 2 or X.shape[0] < 12:
            return None
        n_components = max(1, min(10, X.shape[0] - 1, X.shape[1]))
        model = Pipeline([
            ('scaler', StandardScaler()),
            ('pls', PLSRegression(n_components=n_components)),
        ])
        model.fit(X, y)
        pred = model.predict(X).ravel()
        residuals = y - pred
        groups: Dict[str, List[float]] = {}
        for label, r in zip(group_labels, residuals):
            groups.setdefault(str(label), []).append(float(r))
        return {'groups': groups, 'fitted': True}
    except Exception:
        logger.exception('Residual group fit failed (non-fatal)')
        return None


def _significance_test(groups: Dict[str, List[float]]) -> Dict[str, Any]:
    """Statistischer Test, ob die Herkunfts-Differenz die Kalibration
    signifikant beeinflusst: Levene-Test (Varianzgleichheit der Residuen)
    und Welch-t-Test (Mittelwert-Differenz). Nur scipy, keine neue
    Abhaengigkeit. Liefert Klartext-Interpretation fuer den Bericht."""
    result: Dict[str, Any] = {'performed': False}
    try:
        from scipy import stats
        labels = [l for l in groups if len(groups[l]) >= 3]
        if len(labels) < 2:
            result['reason'] = (
                'Zu wenige Residuen pro Herkunftsgruppe (min. 3 je '
                'Gruppe noetig), um einen belastbaren Test zu rechnen.')
            return result
        a = np.asarray(groups[labels[0]], dtype=float)
        b = np.asarray(groups[labels[1]], dtype=float)
        lev_stat, lev_p = stats.levene(a, b, center='median')
        t_stat, t_p = stats.ttest_ind(a, b, equal_var=False)
        alpha = 0.05
        variance_equal = lev_p > alpha
        means_equal = t_p > alpha
        if variance_equal and means_equal:
            interpretation = (
                'Kein signifikanter Einfluss nachweisbar: Residuen der '
                'Herkunftsgruppen sind homoskedastisch (Levene p='
                f'{lev_p:.3f}) und mittelwertgleich (Welch p={t_p:.3f}). '
                'Die Zusammenfuehrung ist kalibrationstechnisch '
                'unproblematisch.')
        elif not variance_equal:
            interpretation = (
                'Signifikanter Varianzunterschied (Levene p='
                f'{lev_p:.3f}): eine Herkunftsgruppe streut systematisch '
                'anders - z. B. operatives Vorgehen oder Probenmatrix. '
                'Die kombinierte Kalibration nutzen, aber die Gruppen-'
                'Kennzahlen im Bericht beachten.')
        else:
            interpretation = (
                'Signifikanter Mittelwertunterschied der Residuen (Welch '
                f'p={t_p:.3f}): eine Gruppe wird systematisch ueber-/'
                'unterschaetzt - die Zusammenfuehrung sollte fachlich '
                'begruendet werden (z. B. Drift, Operator-Effekt).')
        result.update({
            'performed': True,
            'groups': labels,
            'levene': {'statistic': float(lev_stat), 'p_value': float(lev_p),
                       'alpha': alpha, 'variance_equal': bool(variance_equal)},
            'welch_t': {'statistic': float(t_stat), 'p_value': float(t_p),
                        'alpha': alpha, 'means_equal': bool(means_equal)},
            'interpretation': interpretation,
        })
    except Exception:
        logger.exception('Significance test failed (non-fatal)')
        result['reason'] = 'Statistischer Test fehlgeschlagen (non-fatal).'
    return result


def _tolerance_levels_from_targets(targets) -> tuple:
    """OP65 (Livetest-Feedback): Toleranzstufen an die Messgroessen-
    Aufloesung koppeln. Brix ist typischerweise in 0,1-Schritten erfasst
    - dann sind +-0,5/+-1,0 sinnvolle Stufen; feinere Referenzwerte
    bekommen feinere Stufen, grobere groebere. Nie leer."""
    import numpy as np
    try:
        y = np.asarray([float(t) for t in targets], dtype=float)
        finite = y[np.isfinite(y)]
        if len(finite) < 2:
            return (0.5, 1.0)
        diffs = np.abs(np.diff(np.sort(np.unique(finite))))
        diffs = diffs[diffs > 0]
        if not len(diffs):
            return (0.5, 1.0)
        step = float(np.median(diffs))
        if step < 0.05:
            return (0.1, 0.5, 1.0)
        if step < 0.5:
            return (0.5, 1.0)
        if step < 2.0:
            return (1.0, 2.0)
        return (max(1.0, step), max(2.0, 2.0 * step))
    except Exception:
        return (0.5, 1.0)


def _pvr_chart(pvr: Dict[str, Any], target_name: Optional[str],
                dataset_label: str) -> Optional[str]:
    """OP66: Predicted-vs-Reference-Streudiagramm des Fusionsprojekts
    als EIN kombiniertem Datensatz - Wiederverwendung des produktiven
    Chart-Builders (calibration_charts._ref_vs_pred, OP20-Vertrag:
    Base64-PNG-Data-URL, ehrliches None wenn matplotlib fehlt) - keine
    Kopie der Chart-Logik."""
    try:
        from services.calibration_charts import _ref_vs_pred
        pairs = pvr.get('pairs') or []
        if not pairs:
            return None
        import numpy as np
        y_true = np.asarray([p['reference'] for p in pairs], dtype=float)
        y_pred = np.asarray([p['predicted'] for p in pairs], dtype=float)
        name = target_name or 'Zielwert'
        note = (f'{dataset_label}: {pvr.get("n", len(pairs))} Messungen, '
                f'{pvr.get("cv_folds", "?")}-fold CV')
        return _ref_vs_pred(y_true, y_pred,
                            r2=1.0 - (pvr.get('rmse') or 0.0) ** 2
                            / (float(np.var(y_true)) or 1.0),
                            rmse=float(pvr.get('rmse') or 0.0),
                            method_note=note, target_name=name)
    except Exception:
        logger.exception('Fusion PVR chart failed (non-fatal)')
        return None


def _predicted_vs_reference(samples, targets, cv_folds: int = 5,
                             tolerance_levels=None) -> Optional[Dict[str, Any]]:
    """OP64 (PO-Feedback): Kreuzvalidierung so dargestellt, wie es fachlich
    zaehlt - pro Messung die vorhergesagte gegen die TATSAECHLICHE
    Referenzgröße (Brix), nicht nur abstrakte CV-Kennzahlen. Liefert
    cross_val_predict (sklearn, vorhanden), daraus Trefferquoten innerhalb
    definierter Toleranzen und die Messwert-Paare fuer einen
    Predicted-vs-Reference-Plot."""
    if tolerance_levels is None:
        tolerance_levels = _tolerance_levels_from_targets(targets)
    try:
        import numpy as np
        from sklearn.cross_decomposition import PLSRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline
        from sklearn.model_selection import KFold, cross_val_predict
        X = np.asarray(samples, dtype=float)
        y = np.asarray(targets, dtype=float)
        if X.ndim != 2 or X.shape[0] < 12:
            return None
        n_components = max(1, min(10, X.shape[0] - 1, X.shape[1]))
        model = Pipeline([
            ('scaler', StandardScaler()),
            ('pls', PLSRegression(n_components=n_components)),
        ])
        folds = max(2, min(cv_folds, X.shape[0]))
        splitter = KFold(n_splits=folds, shuffle=True, random_state=42)
        predicted = cross_val_predict(model, X, y, cv=splitter).ravel()
        errors = np.abs(y - predicted)
        hits = {}
        for tol in tolerance_levels:
            hits[f'{float(tol)}'] = {
                'tolerance': float(tol),
                'n_within': int((errors <= tol).sum()),
                'ratio': float((errors <= tol).mean()),
            }
        return {
            'n': int(X.shape[0]),
            'cv_folds': folds,
            'pairs': [
                {'reference': float(r), 'predicted': float(p)}
                for r, p in zip(y, predicted)
            ],
            'hits_within_tolerance': hits,
            'mae': float(np.mean(errors)),
            'rmse': float(np.sqrt(np.mean(errors ** 2))),
        }
    except Exception:
        logger.exception('predicted-vs-reference failed (non-fatal)')
        return None


def comparative_calibration(fused_project, source_projects) -> Dict[str, Any]:
    """Stufe 3: drei Kalibrationen + Signifikanz-Test.

    fused_project: das Fusionsprojekt (kombinierte Daten)
    source_projects: Liste der Quell-Projekte (Einzel-Kalibrationen)

    Liefert einen Berichts-DICT mit {'status', 'target_name',
    'calibrations': {label: kennzahlen}, 'comparison': {...},
    'significance': {...}, 'conclusion': str}."""
    result: Dict[str, Any] = {
        'status': 'ok',
        'method': COMPARISON_METHOD,
        'calibrations': {},
        'conclusion': '',
    }
    groups: Dict[str, Dict[str, Any]] = {}
    for p in list(source_projects) + [fused_project]:
        data = _collect_samples(p)
        if not data['samples']:
            groups[str(p.id)] = {'data': data, 'fit': None}
            continue
        fit = _fit_calibration(data['samples'], data['targets'])
        groups[str(p.id)] = {'data': data, 'fit': fit}
        result['target_name'] = (result.get('target_name')
                                 or data['target_name'])
    for pid, entry in groups.items():
        proj = fused_project if pid == str(fused_project.id) else \
            next((p for p in source_projects if str(p.id) == pid), None)
        label = (proj.name if proj is not None else pid)
        fit = entry['fit']
        if fit is None:
            result['calibrations'][label] = {
                'status': 'not_calibratable',
                'reason': ('Keine verwertbaren Kalibrationsdaten '
                           '(Referenzspalte + min. 12 Messpunkte noetig).'),
                'n_samples': len(entry['data']['samples']),
            }
        else:
            pvr = _predicted_vs_reference(entry['data']['samples'],
                                           entry['data']['targets'])
            entry_result = {
                'status': 'ok',
                'n_samples': len(entry['data']['samples']),
                'mean_r2': fit.get('mean_r2'),
                'rmse_cv': fit.get('rmse_cv'),
                'rpd': fit.get('rpd'),
                'cv_folds': fit.get('cv_folds'),
                'predicted_vs_reference': pvr,
            }
            # OP66: Brix-Chart nur fuer das Fusionsprojekt - der
            # kombinierte Datensatz als EIN Datensatz dargestellt.
            if pid == str(fused_project.id) and pvr:
                entry_result['pvr_chart'] = _pvr_chart(
                    pvr, result.get('target_name'), label)
            result['calibrations'][label] = entry_result
    # Residuen-Analyse + Signifikanz-Test auf den kombinierten Daten
    fused_data = _collect_samples(fused_project)
    source_data = [_collect_samples(p) for p in source_projects]
    group_labels: List[str] = []
    combined_samples: List[List[float]] = []
    combined_targets: List[float] = []
    for idx, sd in enumerate(source_data):
        if not sd['samples']:
            continue
        combined_samples.extend(sd['samples'])
        combined_targets.extend(sd['targets'])
        group_labels.extend([f'Quelle {idx + 1}'] * len(sd['samples']))
    significance: Dict[str, Any] = {'performed': False}
    if combined_samples and fused_data['samples']:
        by_group = _residuals_by_group(combined_samples, combined_targets,
                                       group_labels)
        if by_group and by_group.get('fitted'):
            significance = _significance_test(by_group['groups'])
    elif not fused_data['samples']:
        significance = {'performed': False,
                         'reason': ('Fusionsprojekt hat keine verwertbaren '
                                    'Kalibrationsdaten.')}
    result['significance'] = significance
    # Schlussfolgerung (Klartext fuer den Bericht)
    ok = {label: c for label, c in result['calibrations'].items()
          if c.get('status') == 'ok'}
    fused_label = (fused_project.name if fused_project is not None
                   else 'kombiniert')
    if fused_label in ok and len(ok) >= 3:
        r2_f = ok[fused_label].get('mean_r2') or 0.0
        singles = [c.get('mean_r2') or 0.0 for l, c in ok.items()
                   if l != fused_label]
        best_single = max(singles) if singles else 0.0
        if r2_f >= best_single:
            result['conclusion'] = (
                f'Die kombinierte Kalibration ({r2_f:.3f} R2/CV) ist '
                f'nicht schlechter als die beste Einzel-Kalibration '
                f'({best_single:.3f}) - die Zusammenfuehrung ist '
                'kalibrationstechnisch sinnvoll.')
        else:
            result['conclusion'] = (
                f'Die kombinierte Kalibration ({r2_f:.3f} R2/CV) bleibt '
                f'hinter der besten Einzel-Kalibration ({best_single:.3f}) '
                'zurueck - die Heterogenitaet der Quellen wirkt sich '
                'negativ aus; Einzel-Kalibrationen bevorzugen, sofern '
                'der Signifikanz-Test keinen Gegenbeweis liefert.')
    elif fused_label not in ok:
        result['conclusion'] = (
            'Die kombinierten Daten sind nicht kalibrierbar (Referenzwerte '
            'fehlen oder zu wenige Messpunkte) - ein Kalibrationsvergleich '
            'ist fuer diesen Fall nicht moeglich.')
    else:
        result['conclusion'] = (
            'Nicht alle Quell-Projekte sind einzeln kalibrierbar - der '
            'Vergleich beschraenkt sich auf die verfuegbaren '
            'Kalibrationen.')
    if significance.get('interpretation'):
        result['conclusion'] += ' ' + significance['interpretation']
    # OP66: Klartext-Diskussionszusammenfassung fuer den Chatbot (MO 10):
    # eine kompakte, kontextfaehige Beschreibung des Fusionsergebnisses,
    # die die Nutzer-KI-Diskussion ohne erneute Rechnung anreichert.
    fused_cal = result['calibrations'].get(fused_label)
    if fused_cal and fused_cal.get('status') == 'ok':
        parts = [
            f'Method: {COMPARISON_METHOD}; Zielwert: '
            f'{result.get("target_name") or "Referenzgroesse"}.',
        ]
        for label, c in result['calibrations'].items():
            if c.get('status') == 'ok':
                pvr = c.get('predicted_vs_reference') or {}
                hit = pvr.get('hits_within_tolerance') or {}
                first_hit = next(iter(hit.values()), None)
                parts.append(
                    f'{label}: n={c.get("n_samples")}, '
                    f'R2/CV={c.get("mean_r2")}, RMSECV={c.get("rmse_cv")}, '
                    f'MAE={pvr.get("mae")}'
                    + (f', Trefferquote +-{first_hit["tolerance"]}: '
                       f'{first_hit["n_within"]}/{pvr.get("n")}'
                       if first_hit else ''))
            else:
                parts.append(f'{label}: nicht kalibrierbar.')
        parts.append('Fazit: ' + result['conclusion'])
        result['discussion_summary'] = ' '.join(parts)
    return result
