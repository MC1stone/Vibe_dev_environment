"""Workflow context helpers for the six-step project workflow (WORKFLOW_DESIGN.md).

Builds the stepper context (stations with states and open decisions) for the
project pages and provides the create/resolve endpoints for user decisions.
"""
import logging

from django.utils import timezone

from core.models import AnalysisProject, WorkflowDecision, WorkflowStation

logger = logging.getLogger(__name__)

STATION_COUNT = 6


def ensure_stations(project):
    """Create the six workflow stations for a project if they do not exist yet."""
    existing = {s.station for s in project.workflow_stations.all()}
    missing = [n for n in range(1, STATION_COUNT + 1) if n not in existing]
    if not missing:
        return
    WorkflowStation.objects.bulk_create([
        WorkflowStation(project=project, station=n) for n in missing
    ])


def derive_station_state(project, station):
    """Derive the state of a station from the project phase if it is still open.

    Maps the existing phase model (drafted/released/completed) onto the six
    stations so the stepper starts with a truthful position instead of
    everything-open.
    """
    if station.state != 'open':
        return station.state
    if project.phase == 'completed':
        return 'done'
    if project.phase == 'released':
        return 'done' if station.station in (1, 2, 3) else 'in_progress'
    # drafted: station 1 done (project exists with data); station 2 done as
    # soon as the ingest finished with at least one usable dataset - the
    # stepper turns green right after the data upload instead of staying
    # 'in progress' until the release.
    if station.station == 1:
        return 'done'
    if station.station == 2:
        preparation = getattr(project, 'preparation_report', None) or {}
        if preparation.get('datasets'):
            return 'done'
        return 'in_progress'
    return 'open'


def project_workflow_context(project):
    """Stepper context for the project pages (stations + open decisions)."""
    ensure_stations(project)
    stations = sorted(project.workflow_stations.all(), key=lambda s: s.station)
    for s in stations:
        s.derived_state = derive_station_state(project, s)
        s.open_decision_count = WorkflowDecision.objects.filter(
            station=s, resolved_at__isnull=True).count()

    open_decisions = list(
        WorkflowDecision.objects.filter(
            project=project, resolved_at__isnull=True
        ).select_related('station').order_by('created_at'))

    return {
        'project_id': str(project.id),
        'stations': stations,
        'open_decisions': open_decisions,
        'open_decision_count': len(open_decisions),
    }


def create_decision(project, station_number, question, options, ki_basis=''):
    """Register a pending user decision at a station (no dead ends).

    Every option needs 'id', 'label' and 'effect'; at least two options are
    required. The station switches to awaiting_user.
    """
    if len(options) < 2:
        raise ValueError('A decision requires at least two options (no dead ends)')
    for option in options:
        if not all(k in option for k in ('id', 'label', 'effect')):
            raise ValueError("Every option needs 'id', 'label' and 'effect' (no dead ends)")

    ensure_stations(project)
    station = project.workflow_stations.get(station=station_number)
    decision = WorkflowDecision.objects.create(
        project=project,
        station=station,
        question=question,
        options=options,
        ki_basis=ki_basis or '',
    )
    station.state = 'awaiting_user'
    station.save(update_fields=['state', 'updated_at'])
    logger.info('Decision %s registered for project %s at station %s',
                decision.id, project.id, station_number)
    return decision


def resolve_decision(decision, option_id, modified_values=None):
    """Resolve a pending decision with one of its options (append-only log).

    The resolution stays in the log for the final report; the station returns
    to in_progress when no other decision is pending there.
    """
    chosen = next((o for o in (decision.options or []) if o.get('id') == option_id), None)
    if chosen is None:
        raise ValueError('Unknown option for decision')

    decision.answer = {
        'option_id': option_id,
        'effect': chosen.get('effect', ''),
        'modified_values': modified_values or {},
        'resolved_at': timezone.now().isoformat(),
    }
    decision.resolved_at = timezone.now()
    decision.save(update_fields=['answer', 'resolved_at'])

    still_open = WorkflowDecision.objects.filter(
        project=decision.project,
        station=decision.station,
        resolved_at__isnull=True,
    ).exists()
    if not still_open:
        decision.station.state = 'in_progress'
        decision.station.save(update_fields=['state', 'updated_at'])
    logger.info('Decision %s resolved with option %s', decision.id, option_id)
    return decision
