"""OP81: Kalibrierungs-Management - Einfluss-Bewertung je Datei.

Nutzer-Anforderung (2026-10-21): 'Innerhalb eines Labors koennen
unterschiedlichste Datensaetze zu einem Projekt bestehen und
unterschiedliche Projekte koennen fuer dieselbe Kalibrierung genutzt
werden. Dateien muessen Kalibrierungen zugeordnet werden; die Liste
soll die Bewertung des Einflusses auf die Qualitaet der Kalibrierung
anzeigen. Dateien ohne Mehrwert sollen nur berichtet werden, aber
keinen Effekt auf die Kalibrierungsentwicklung haben.'

Bewertung: Leave-One-File-Out (LOFO) - RMSE der Kalibrierung mit allen
AKTIVEN Dateien vs. RMSE ohne die jeweilige Datei. Delta = Einfluss:
  delta < 0 : Datei verbessert die Kalibrierung (wichtig)
  delta ~ 0 : kein nennenswerter Einfluss
  delta > 0 : Datei verschlechtert die Kalibrierung (Kandidat fuer
              reported_only)
Schwellwert: |delta| <= NO_INFLUENCE_EPS => 'reported_only'
(Kalibrierungsentwicklung laeuft nur ueber aktive Dateien).
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

NO_INFLUENCE_EPS = 0.05
HARMFUL_THRESHOLD = 0.0


def _file_rows(assignment_file) -> Optional[Dict[str, Any]]:
    """Kalibrationsfaehige Zeilen EINER Datei aus dem Vorbereitungs-
    bericht eines Projekts ziehen, dem die Datei angehoert."""
    try:
        from core.models import AnalysisProject
        for project in AnalysisProject.objects.filter(
                files=assignment_file):
            for ds in ((project.preparation_report or {})
                       .get('datasets') or []):
                if str(ds.get('file_id')) != str(assignment_file.id) \
                        and not str(ds.get('file_id', '')).startswith(
                            f'{assignment_file.id}:'):
                    continue
                samples = ds.get('calibration_samples') or []
                targets = ds.get('reference_values') or []
                if samples and targets \
                        and len(samples) == len(targets):
                    return {
                        'samples': [[float(v) for v in row]
                                    for row in samples],
                        'targets': [float(t) for t in targets],
                        'target_name': ds.get('target_name'),
                        'file_name': ds.get('file_name') or str(
                            assignment_file.id),
                    }
    except Exception:
        logger.exception('calibration file rows lookup failed '
                         '(non-fatal)')
    return None


def evaluate_assignments(calibration) -> Dict[str, Any]:
    """LOFO-Einflussbewertung aller Zuordnungen einer Kalibrierung.

    Nutzt die produktive PLS-Kalibration (fusion_calibration.
    _fit_calibration). Aktualisiert status/influence_rmse/influence_note
    je Zuordnung und liefert eine Zusammenfassung. Dateien ohne
    Mehrwert werden auf 'reported_only' gesetzt - sie fliessen in
    KEINE nachfolgende Kalibrierungsentwicklung ein, werden aber im
    Bericht genannt (Ehrlichkeit statt stiller Entfernung).
    """
    from services.fusion_calibration import _fit_calibration
    rows_by_file: Dict[str, Dict[str, Any]] = {}
    active = []
    for a in calibration.assignments.select_related('file'):
        rows = _file_rows(a.file)
        if rows is None:
            a.influence_rmse = None
            a.influence_note = ('Keine kalibrationsfaehigen Daten '
                                '(Referenzspalte + min. 12 Messpunkte '
                                'noetig) - nur berichtet.')
            if a.status == 'active':
                a.status = 'reported_only'
            a.save()
            continue
        rows_by_file[str(a.id)] = rows
        active.append(a)

    summary = {'evaluated': 0, 'important': 0, 'neutral': 0,
               'harmful': 0, 'not_calibratable': 0,
               'baseline_rmse': None}

    def _rmse(assigns) -> Optional[float]:
        samples: List[List[float]] = []
        targets: List[float] = []
        for a in assigns:
            rows = rows_by_file.get(str(a.id))
            if rows:
                samples.extend(rows['samples'])
                targets.extend(rows['targets'])
        fit = _fit_calibration(samples, targets)
        return float(fit['rmse_cv']) if fit else None

    if not active:
        return summary
    baseline = _rmse(active)
    summary['baseline_rmse'] = baseline
    if baseline is None:
        for a in active:
            a.influence_rmse = None
            a.influence_note = ('Gesamt-Kalibrierung nicht berechenbar '
                                '(zu wenige Zeilen ueber alle Dateien).')
            a.save()
        return summary

    from django.db import transaction
    with transaction.atomic():
        for a in active:
            summary['evaluated'] += 1
            rest = [x for x in active if x.id != a.id]
            if len(rest) < 1:
                a.influence_rmse = None
                a.influence_note = ('Einzige aktive Datei - LOFO nicht '
                                    'moeglich, bleibt aktiv.')
                a.save()
                continue
            without = _rmse(rest)
            if without is None:
                a.influence_rmse = None
                a.influence_note = ('Ohne diese Datei nicht kalibrierbar '
                                    '- die Datei traegt die Kalibrierung.')
                a.save()
                summary['important'] += 1
                continue
            delta = baseline - without  # negativ = besser MIT der Datei
            a.influence_rmse = round(delta, 4)
            if delta < -NO_INFLUENCE_EPS:
                a.status = 'active'
                a.influence_note = (
                    f'Wichtig: ohne diese Datei steigt der RMSE um '
                    f'{abs(delta):.4f} - die Kalibrierung wird '
                    f'schlechter.')
                summary['important'] += 1
            elif delta > NO_INFLUENCE_EPS:
                a.status = 'reported_only'
                a.influence_note = (
                    f'Ohne Mehrwert: ohne diese Datei sinkt der RMSE um '
                    f'{delta:.4f} - die Datei verschlechtert die '
                    f'Kalibrierung. Nur berichtet, kein Effekt auf die '
                    f'Kalibrierungsentwicklung.')
                summary['harmful'] += 1
            else:
                a.status = 'reported_only'
                a.influence_note = (
                    f'Kein nennenswerter Einfluss (delta RMSE '
                    f'{delta:+.4f}) - nur berichtet, kein Effekt auf '
                    f'die Kalibrierungsentwicklung.')
                summary['neutral'] += 1
            a.save()
    return summary


def active_rows(calibration) -> Dict[str, Any]:
    """Kalibrationszeilen NUR der aktiven Dateien - die Basis fuer die
    Kalibrierungsentwicklung (reported_only fliesst nicht ein) sowie
    fuer die FL-Shard-Information (Gruppen je Datei)."""
    samples: List[List[float]] = []
    targets: List[float] = []
    groups: List[str] = []
    for a in (calibration.assignments
              .filter(status='active')
              .select_related('file')):
        rows = _file_rows(a.file)
        if rows:
            samples.extend(rows['samples'])
            targets.extend(rows['targets'])
            name = rows['file_name']
            groups.extend([name] * len(rows['samples']))
    return {'samples': samples, 'targets': targets,
            'groups': groups}
