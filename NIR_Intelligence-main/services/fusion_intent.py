"""OP79 Stufe 2: Fusion-Wunsch-Erkennung aus natuerlicher Sprache.

Der Nutzer aeussert im Chat z. B. 'Fusioniere mein Tomaten-Projekt mit
dem Reifeklassen-Projekt' oder 'fuehre die beiden Tomaten-Projekte
zusammen'. Dieser Dienst matchet deterministisch gegen die eigene
Projektliste des Nutzers (kein LLM-Raten: Namen muessen im Text
vorkommen oder eindeutig als Nummer benannt sein) und liefert einen
strukturellen Vorschlag. Die AUSFUEHRUNG passiert nie automatisch -
der Chat antwortet mit einer Bestätigungskarte (project_ids), der
Nutzer klickt 'Zusammenfuehren'.
"""
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_FUSION_WORDS = (
    'fusioniere', 'fusionieren', 'fuehr', 'führ', 'zusammen',
    'merge', 'kombinier', 'combinier', 'zusammenfuehren',
    'zusammenführen', 'verschmelz', 'vereine', 'vereinigen',
)


def detect_fusion_intent(text: str,
                        projects: List[Dict[str, Any]]) \
        -> Optional[Dict[str, Any]]:
    """Erkennt einen Zusammenfuehrungs-Wunsch im Freitext.

    projects: [{'id': ..., 'name': ...}, ...] - die eigene Projektliste
    des Nutzers (Context des Panels). Liefert None, wenn kein Fusions-
    Wunsch erkennbar ist; sonst ein Dict mit den passenden Projekt-IDs
    (2+ = direkt ausfuehrbar, 1 = Kandidat fehlt, 0 = keine Namen
    erkannt) und einem ehrlichen Hinweistext.
    """
    if not text:
        return None
    t = ' '.join(str(text).lower().split())
    if not any(w in t for w in _FUSION_WORDS):
        return None
    matched = []
    for p in projects or []:
        name = str(p.get('name') or '')
        if not name:
            continue
        # Projektnamen als ganzes Wort(e) im Text suchen
        nm = ' '.join(name.lower().split())
        if nm and nm in t:
            matched.append({'id': str(p['id']), 'name': name})
    # 'beide', 'alle' + genau 2 Projekte in der Liste
    if not matched and projects and len(projects) == 2:
        if any(w in t for w in ('beide', 'alle', 'die beiden')):
            matched = [{'id': str(p['id']),
                        'name': str(p.get('name') or '')}
                       for p in projects]
    if len(matched) < 2:
        hint = ('Ich habe einen Zusammenfuehrungs-Wunsch erkannt, aber '
                + ('nur ein Projekt' if len(matched) == 1
                   else 'keines Ihrer Projekte')
                + ' eindeutig identifiziert. Bitte nennen Sie zwei '
                'Projektnamen, z. B. "Fusioniere <Projekt A> und '
                '<Projekt B>".')
        return {'kind': 'fusion', 'project_ids': [m['id'] for m in matched],
                'projects': matched, 'ready': False, 'hint': hint}
    return {
        'kind': 'fusion',
        'project_ids': [m['id'] for m in matched[:2]],
        'projects': matched[:2],
        'ready': True,
        'hint': ('Zusammenfuehrung vorbereitet: die Messdaten werden in '
                 'einem NEUEN Fusionsprojekt zusammengefuehrt (Original-'
                 'projekte bleiben unangetastet). Bitte bestaetigen Sie.'),
    }
