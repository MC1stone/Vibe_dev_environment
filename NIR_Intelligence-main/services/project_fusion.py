"""OP63: Fusion analysis branch - same-sensor / cross-project data fusion.

Fachlicher Fall: zwei Projekte mit vergleichbaren Spektren (z. B.
unterschiedliche Operatoren, andere Tomaten, gleicher Sensor). Wenn die
Similarity-Suche Treffer aus einem anderen Projekt liefert, bietet die
Plattform dem Nutzer einen weiteren Analyse-Zweig an: Metadaten-Abgleich,
Zusammenfuehrung in ein NEUES Projekt (Originale bleiben unangetastet)
und spaeter Stufe 3 der vergleichende Kalibrationsvergleich.

PO-Entscheidungen (2026-10-16): Trigger = Similarity reicht; Fusion =
neues Projekt; Metadaten-Konflikte werden nur informiert, nie geblockt.
"""
import logging
import uuid as _uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _valid_project_ids(project_ids: List[Any]) -> List[str]:
    """Eingehende Projekt-IDs bereinigen: nur gueltige UUIDs, dedupliziert,
    Reihenfolge stabil. Kaputte IDs werden ignoriert statt einen 500er
    zu werfen (Vorfall 2026-10-16: String statt Array -> id__in iterierte
    zeichenweise -> ValidationError 'a' ist keine UUID)."""
    seen = set()
    valid = []
    for pid in (project_ids or []):
        try:
            text = str(_uuid.UUID(str(pid)))
        except (ValueError, AttributeError, TypeError):
            continue
        if text not in seen:
            seen.add(text)
            valid.append(text)
    return valid

# Metadaten-Felder fuer den Abgleich (nur Information, keine Blockade).
# Reihenfolge = Anzeigereihenfolge im Differenz-Bericht.
# Generische Metadaten-Vergleichsfelder (Software-Grundregel: alle
# Anwendungsfaelle, kein Fachkontext-Hardcoding). Die Felder beschreiben
# Messbedinungen, die fuer JEDE spektroskopische Anwendung relevant sind -
# unabhaengig von Probe (Tomate, Kaffee, Boden) oder Messgroesse (Brix,
# Feuchte, Protein).
GENERIC_COMPARISON_FIELDS = [
    ('operator_name', 'Operator'),
    ('sensor_model', 'Sensor/Modell'),
    ('sensor_serial', 'Sensor/Seriennummer'),
    ('sample_type', 'Probenart'),
    ('measurement_date', 'Messdatum'),
    ('integration_time', 'Integrationszeit'),
    ('resolution', 'Aufloesung'),
    ('wavelength_range', 'Wellenlaengenbereich'),
]

# Kontextfelder: alle weiteren vorhandenen Metadatenfelder werden ZUSAETZLICH
# in den Abgleich aufgenommen (z. B. tomato_variety, coffee_origin, soil_type)
# - automatisch erkannt aus den Daten, ohne feste Verdrahtung.
APPLICATION_CONTEXT_FIELD_HINTS = [
    'variety', 'sorte', 'origin', 'herkunft', 'species', 'art',
    'cultivar', 'type', 'sample_name',
]


def _comparison_fields(available_metadata) -> list:
    """Vergleichsfelder = generische Messbedingungsfelder + alle im
    Datenbestand vorgefundenen Kontextfelder (generalisiert, OP65:
    'fuer die Software generisch, fuer den Artikel Tomaten')."""
    fields = list(GENERIC_COMPARISON_FIELDS)
    seen = {key for key, _label in fields}
    try:
        keys = set()
        for meta in available_metadata or []:
            if isinstance(meta, dict):
                keys.update(str(k) for k in meta.keys())
        for k in sorted(keys):
            if k in seen or k in ('file_name', 'file_id'):
                continue
            fields.append((k, k.replace('_', ' ').title()))
    except Exception:
        pass
    return fields


def _meta_get(metadata: Optional[dict], key: str) -> str:
    """Case-insensitive Metadaten-Lookup mit Fallback auf aehnliche Keys."""
    if not metadata:
        return ''
    if key in metadata:
        return str(metadata.get(key) or '')
    for mk, mv in metadata.items():
        if str(mk).lower().replace('-', '_') == key:
            return str(mv or '')
    return ''


def _record_metadata(record) -> Dict[str, str]:
    """Normalisierte Metadaten eines SpectrumRecord fuer den Abgleich.

    Generisch: UEBER die bekannten Felder hinaus werden alle vorhandenen
    Metadaten-Schluessel uebernommen (OP65-Generalisierung)."""
    meta = dict(record.metadata or {})
    result = {key: _meta_get(meta, key)
              for key, _label in GENERIC_COMPARISON_FIELDS}
    for k in meta:
        if k not in result and k not in ('file_name', 'file_id'):
            result[k] = str(meta.get(k) or '')
    return result


def _dataset_metadata(dataset: Dict[str, Any]) -> Dict[str, str]:
    """Normalisierte Metadaten eines Vorbereitungs-Datensatzes."""
    meta = dict(dataset.get('metadata') or {})
    result = {key: _meta_get(meta, key)
              for key, _label in GENERIC_COMPARISON_FIELDS}
    for k in meta:
        if k not in result and k not in ('file_name', 'file_id'):
            result[k] = str(meta.get(k) or '')
    return result


def metadata_diff(meta_a: Dict[str, str],
                   meta_b: Dict[str, str]) -> Dict[str, Any]:
    """Felderweise Abgleich zweier Metadaten-Mengen (nur Information).

    Liefert {'fields': [{key, label, a, b, equal}], 'differences': int,
    'equal_fields': int}. Niemals blockierend - der PO hat entschieden,
    dass Metadaten-Differenzen angezeigt, nicht bewertet werden.
    OP65: Die Feldliste ist generisch - alle in den Daten vorhandenen
    Metadatenfelder nehmen am Abgleich teil, nicht nur die bekannten.
    """
    fields = []
    differences = 0
    for key, label in _comparison_fields([meta_a, meta_b]):
        va, vb = (meta_a or {}).get(key, ''), (meta_b or {}).get(key, '')
        equal = (va == vb) and bool(va or vb)
        missing = not va and not vb
        if not equal and not missing:
            differences += 1
        fields.append({'key': key, 'label': label, 'a': va, 'b': vb,
                       'equal': equal, 'missing': missing})
    return {
        'fields': fields,
        'differences': differences,
        'equal_fields': sum(1 for f in fields if f['equal']),
    }


def build_fusion_offer(user, project, dataset: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Aehnliche Spektren aus ANDEREN Projekten als Fusion-Angebot aufbereiten.

    Wird aus dem Projekt-Crew-Runner (Stufe 1) aufgerufen. Nutzt die
    vorhandene Similarity-Suche (S5/FAISS) gegen die sichtbare
    Spektrendatenbank - gleiche Engine, keine Kopie. Liefert None, wenn
    keine Treffer aus anderen Projekten vorliegen (Normalfall: schweigen).
    """
    try:
        from core.models import SpectrumRecord
        from services.spectrum_database import visible_records, _dataset_grid
        grid = _dataset_grid(dataset)
        if grid is None:
            return None
        records = list(visible_records(user, grid=grid)
                        .exclude(project_id=project.id)
                        .exclude(project_id=None))
        if not records:
            return None
        from agents.faiss_agent import FaissAgent
        wavelengths = dataset.get('preview', {}).get('wavelengths', [])
        intensities = dataset.get('preview', {}).get('intensities', [])
        if not wavelengths or not intensities:
            return None
        output = FaissAgent().execute({
            'reference_spectra': [
                {'data': {'wavelength': o.wavelengths,
                          'intensity': o.intensities},
                 'wavelength_column': 'wavelength',
                 'intensity_column': 'intensity'}
                for o in records
            ],
            'reference_ids': [str(o.id) for o in records],
            'query_spectrum': {
                'data': {'wavelength': wavelengths,
                         'intensity': intensities},
                'wavelength_column': 'wavelength',
                'intensity_column': 'intensity',
            },
            'top_k': 5,
        })
        matches = output.data.get('matches', []) if output else []
        if not matches:
            return None
        by_id = {str(o.id): o for o in records}
        dataset_meta = _dataset_metadata(dataset)
        candidates = []
        seen_projects = set()
        for m in matches:
            rec = by_id.get(str(m.get('reference_id', '')))
            if rec is None:
                continue
            diff = metadata_diff(dataset_meta, _record_metadata(rec))
            candidates.append({
                'record_id': str(rec.id),
                'file_name': rec.file_name,
                'similarity': m.get('similarity'),
                'project_id': str(rec.project_id),
                'project_name': (rec.project.name if rec.project_id else None),
                'metadata_diff': diff,
            })
            seen_projects.add(str(rec.project_id))
        if not candidates:
            return None
        return {
            'available': True,
            'reason': 'comparable_spectra',
            'candidates': candidates,
            'project_count': len(seen_projects),
            'project_ids': sorted(seen_projects | {str(project.id)}),
            'explanation': (
                'Aehnliche Spektren aus anderen Projekten gefunden. '
                'Analyse-Zweig Datenfusion oeffnen? Metadaten werden '
                'abgeglichen, die Messdaten in einem neuen Projekt '
                'zusammengefuehrt und mit den Einzeldatensaetzen '
                'verglichen. Die Original-Projekte bleiben unangetastet.'),
            'preview_url': '/projects/fusion/preview/',
            'execute_url': '/projects/fusion/execute/',
        }
    except Exception:
        logger.exception('Fusion offer build failed (non-fatal)')
        return None


def build_fusion_offer_for_spectrum(user, spectrum) -> Optional[Dict[str, Any]]:
    """Quick-Check-Variante: Fusion-Angebot fuer ein Einzelspektrum.

    Wird aus der Quick-Check-Analyse (crewai_views) aufgerufen, wenn die
    Similarity-Sektion Treffer aus anderen Projekten liefert.
    """
    try:
        if not spectrum or not getattr(spectrum, 'wavelengths', None):
            return None
        from core.models import SpectrumRecord
        from services.similarity_search import find_similar_records
        class _RecordAdapter:
            """Minimal-Adapter: NIRSpectrum -> SpectrumRecord-Schema."""
            def __init__(self, s):
                self.id = s.id
                self.wavelengths = s.wavelengths
                self.intensities = s.intensities
                self.wavelength_grid = (
                    __import__('core.models', fromlist=['SpectrumRecord'])
                    .SpectrumRecord.grid_key(s.wavelengths)
                    if s.wavelengths else None)
                self.file_name = s.name or s.sample_id or 'spectrum'
        similar = find_similar_records(user, _RecordAdapter(spectrum), top_k=5)
        if not similar:
            return None
        from core.models import SpectrumRecord
        by_id = {str(o.id): o for o in
                 SpectrumRecord.objects.filter(
                     id__in=[m['record_id'] for m in similar
                             if m.get('record_id')])}
        candidates = []
        seen_projects = set()
        for m in similar:
            rec = by_id.get(m['record_id'])
            if rec is None or rec.project_id is None:
                continue
            candidates.append({
                'record_id': str(rec.id),
                'file_name': rec.file_name,
                'similarity': m.get('similarity'),
                'project_id': str(rec.project_id),
                'project_name': (rec.project.name if rec.project_id else None),
                'metadata_diff': metadata_diff(
                    {}, _record_metadata(rec)),
            })
            seen_projects.add(str(rec.project_id))
        if not candidates:
            return None
        return {
            'available': True,
            'reason': 'comparable_spectra',
            'candidates': candidates,
            'project_count': len(seen_projects),
            'project_ids': sorted(seen_projects | {str(project.id)}),
            'explanation': (
                'Aehnliche Spektren aus anderen Projekten gefunden. '
                'Analyse-Zweig Datenfusion oeffnen? Metadaten werden '
                'abgeglichen, die Messdaten in einem neuen Projekt '
                'zusammengefuehrt und mit den Einzeldatensaetzen '
                'verglichen. Die Original-Projekte bleiben unangetastet.'),
            'preview_url': '/projects/fusion/preview/',
            'execute_url': '/projects/fusion/execute/',
        }
    except Exception:
        logger.exception('Fusion offer (spectrum) build failed (non-fatal)')
        return None


def preview_fusion(user, project_ids: List[str],
                    dataset_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Metadaten-Abgleich vor der Zusammenfuehrung (Stufe 2, schreibfrei).

    Liefert die vollstaendige Differenzliste aller beteiligten Projekte
    plus die Datenmengen, die zusammengefuehrt wuerden. Der Nutzer sieht
    genau, was passieren wuerde, bevor er entscheidet (nur Information,
    keine Blockade - PO-Entscheidung).
    """
    from core.models import AnalysisProject
    project_ids = _valid_project_ids(project_ids)
    projects = AnalysisProject.objects.filter(id__in=project_ids, user=user)
    result = {
        'available': True,
        'projects': [],
        'total_datasets': 0,
        'warnings': [],
    }
    project_meta = None
    for p in projects:
        prep = p.preparation_report or {}
        datasets = prep.get('datasets', [])
        usable = [d for d in datasets if d.get('usable')]
        result['total_datasets'] += len(usable)
        meta = {}
        for d in usable:
            dm = _dataset_metadata(d)
            meta = meta or dm
        result['projects'].append({
            'project_id': str(p.id),
            'project_name': p.name,
            'phase': p.phase,
            'usable_datasets': len(usable),
            'dataset_names': [d.get('file_name') for d in usable],
            'metadata': meta,
        })
    if len(result['projects']) >= 2:
        a = result['projects'][0]['metadata']
        for other in result['projects'][1:]:
            b = other['metadata']
            other['metadata_diff_vs_first'] = metadata_diff(a, b)
    return result


def execute_fusion(user, project_ids: List[str], name: str = '',
                   description: str = '',
                   analysis_intent: str = '',
                   analysis_wishes: str = '') -> Dict[str, Any]:
    """Zusammenfuehrung in ein NEUES Projekt (Stufe 2, PO-Entscheidung).

    Die Messdaten beider Quell-Projekte werden referenziert (Original-
    Dateien bleiben in ihren Projekten unangetastet); das neue Projekt
    traegt die Herkunft (source_projects) in seiner Beschreibung und im
    Vorbereitungsbericht. Anschliessend kann der Nutzer das Projekt
    wie gewohnt vorbereiten/pruefen/releasen - inkl. Stufe 3
    (Kalibrationsvergleich) in einem Folgeschritt.
    """
    from core.models import AnalysisProject, GenericFile
    from django.db import transaction
    project_ids = _valid_project_ids(project_ids)
    sources = AnalysisProject.objects.filter(id__in=project_ids, user=user)
    if sources.count() < 2:
        return {'success': False,
                'error': 'Mindestens zwei Projekte des Nutzers erforderlich.'}
    # OP65 (Livetest-Feedback): versehentliches DOPPEL-Zusammenschieben
    # verhindern - existiert bereits ein Fusionsprojekt mit derselben
    # Quell-Kombination, wird abgelehnt (klarer Hinweis statt ewigem
    # erneuten Ingest desselben Datenmaterials).
    wanted = set(project_ids)
    for existing in AnalysisProject.objects.filter(
            user=user, preparation_report__fusion__created_by='op63_fusion'):
        efusion = (existing.preparation_report or {}).get('fusion') or {}
        existing_sources = {s.get('project_id')
                            for s in efusion.get('source_projects', [])
                            if s.get('project_id')}
        if existing_sources == wanted:
            return {
                'success': False,
                'error': ('Diese Projekte sind bereits zusammengefuehrt: '
                          + existing.name
                          + '. Bitte das bestehende Fusionsprojekt '
                          'verwenden statt erneut zusammenzufuehren.'),
                'existing_project_id': str(existing.id),
                'existing_project_url': f'/projects/{existing.id}/',
            }
    source_files = []
    source_names = []
    for p in sources:
        source_names.append(p.name)
        for f in p.files.all():
            source_files.append(f)
    if not source_files:
        return {'success': False,
                'error': 'Die Quell-Projekte enthalten keine Dateien.'}
    if not name:
        name = f"Fusionsprojekt: {' + '.join(source_names)}"
    if not description:
        description = (
            'Automatisch zusammengefuehrtes Fusionsprojekt (OP63) aus den '
            f'Projekten: {", ".join(source_names)}. '
            'Analyse-Zweig: Metadaten-Abgleich + Vergleichende Kalibration '
            'gegen die Einzeldatensaetze.')
    with transaction.atomic():
        fused = AnalysisProject.objects.create(
            user=user, name=name[:255], description=description)
        fused.files.set(source_files)
        # OP79b: FREIE Analyse-Wuensche bei der Fusion statt starrer
        # Intents (Nutzer-Wunsch: 'Flexibilitaet' - das alte Dropdown
        # hardkodierte 5 Klassen). Der freie Text (z. B. '5 Reifeklassen
        # der Tomaten', '3 Feuchtegruppen') wird ueber die generische
        # parse_wishes-Pipeline (OP77) uebersetzt - nicht verstandene
        # Wuensche ehrlich als offene Fragen im Bericht.
        wishes_text = str(analysis_wishes or '').strip()[:2000]
        if not wishes_text:
            # Abwaertskompatibilitaet: altes Dropdown-Feld
            # analysis_intent ('classification'/'regression') bleibt
            # als Shortcut erhalten und wird in Text uebersetzt.
            intent = str(analysis_intent or '').strip().lower()
            if intent in ('classification', 'klassifikation',
                          'klassifizieren'):
                wishes_text = ('Bilde Klassen aus dem Messziel und '
                               'klassifiziere die Datensätze')
            elif intent in ('regression',):
                wishes_text = ''
        user_options: Dict[str, Any] = {}
        if wishes_text:
            from services.analysis_wishes import parse_wishes
            parsed = parse_wishes(wishes_text)
            user_options['analysis_wishes'] = wishes_text
            user_options['parsed_wishes'] = parsed['wishes']
            user_options['unparsed_wishes'] = parsed['unparsed']
        fused.preparation_report = {
            'user_options': user_options,
            'fusion': {
                'source_projects': [
                    {'project_id': str(p.id), 'project_name': p.name}
                    for p in sources
                ],
                'created_by': 'op63_fusion',
                'note': ('Messdaten stammen aus den Quell-Projekten und '
                         'bleiben dort unangetastet; dieses Projekt '
                         'referenziert die Dateien fuer den Analyse-Zweig.'),
            },
        }
        fused.save()
    from threading import Thread
    from services.project_ingest import build_preparation_report

    def _prepare(pid):
        try:
            from core.models import AnalysisProject as AP
            proj = AP.objects.get(id=pid)
            build_preparation_report(proj)
        except Exception:
            logger.exception('Fusion project preparation failed')
    Thread(target=_prepare, args=(str(fused.id),), daemon=True).start()
    return {
        'success': True,
        'project_id': str(fused.id),
        'project_name': fused.name,
        'detail_url': f'/projects/{fused.id}/',
        'note': ('Fusionsprojekt angelegt; Aufbereitung laeuft im Hintergrund '
                 '(OP55-Muster).'),
    }


def metadata_suggestions(fused_project) -> Dict[str, Any]:
    """OP65 (Livetest-Feedback): KI-Metadaten-Vorschlaege im Fusionsprojekt.

    Fachfall: ein Quelldatensatz traegt Metadaten (Operator, Sensor,
    Tomatensorte, Datum), der andere nicht. Der Nutzer vermisst beim
    Fusionsprojekt die Vorschlaege. Hier werden pro Datensatz ohne
    Metadaten die Werte der ANDEREN Quelldatensaetze als Uebernahme-
    Vorschlag aufbereitet - als Angebot, nicht als stiller Import
    (Metadaten-Overrides entscheidet der Nutzer, OP13/OP30 unveraendert).
    """
    from core.models import AnalysisProject
    result: Dict[str, Any] = {'available': False, 'suggestions': []}
    try:
        fusion = (fused_project.preparation_report or {}).get('fusion') or {}
        source_ids = [s.get('project_id') for s in
                      fusion.get('source_projects', []) if s.get('project_id')]
        sources = list(AnalysisProject.objects.filter(id__in=source_ids))
        own_datasets = (fused_project.preparation_report or {}).get(
            'datasets', [])
        source_datasets = []
        for sp in sources:
            source_datasets.extend(
                (sp.preparation_report or {}).get('datasets', []))
        donors = [d for d in source_datasets
                  if d.get('usable') and (d.get('metadata') or {})]
        if not donors or not own_datasets:
            return result
        for ds in own_datasets:
            if not ds.get('usable'):
                continue
            meta = ds.get('metadata') or {}
            filled = {k: v for k, v in meta.items()
                      if str(v or '').strip() and k not in
                      ('file_name', 'file_id')}
            if len(filled) >= 4:
                continue  # Datensatz hat eigene Metadaten - kein Vorschlag
            proposals = []
            for donor in donors:
                dmeta = donor.get('metadata') or {}
                for field, value in dmeta.items():
                    if field in ('file_name', 'file_id'):
                        continue
                    if not str(value or '').strip():
                        continue
                    if field in filled:
                        continue
                    proposals.append({
                        'field': field,
                        'value': value,
                        'source_file': donor.get('file_name', ''),
                        'source_project': (
                            donor.get('project_name')
                            or 'Quellprojekt'),
                    })
            if proposals:
                # deduplizieren (Feld -> erster Vorschlag)
                seen = {}
                for p in proposals:
                    seen.setdefault(p['field'], p)
                result['suggestions'].append({
                    'file_id': ds.get('file_id'),
                    'file_name': ds.get('file_name', ''),
                    'proposals': list(seen.values()),
                })
        result['available'] = bool(result['suggestions'])
        return result
    except Exception:
        logger.exception('Metadata suggestions failed (non-fatal)')
        return result
