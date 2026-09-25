"""OP31 verification: KI-first metadata extraction with strict
anti-hallucination and user escalation.

The mission statement runs Ollama/Mistral locally at all times - the LLM
is the PRIMARY metadata extractor. Two hard user requirements are
verified here:

1. The KI must NEVER hallucinate. The guard is enforced in code
   (services/metadata_llm.py): every LLM value must appear VERBATIM in
   the source text, otherwise it is rejected and logged. Unknown field
   names are rejected. No prompt trust.

2. Conflicts and open questions must be escalated to the user via the
   chatbot / report - the KI asks explicitly for a solution instead of
   deciding silently.

Offline test matrix (repo check() style) with a fake Ollama client - CI
has no Ollama; the real path is exercised by the same code with the
real client at runtime.

T1  LLM extraction: verbatim values are accepted, canonicalised
T2  anti-hallucination: invented values are rejected (code guard)
T3  anti-hallucination: unknown/invented field names are rejected
T4  questions pass through (capped, sanitised)
T5  JSON garbage / None answers are rejected honestly
T6  ingest integration: KI fills fields the regex layer missed
T7  conflict: deterministic hard fact wins, conflict escalates to the
    user (open_questions + recommendation + chatbot entry)
T8  offline resilience: no Ollama -> deterministic metadata kept
T9  assessment carries the KI contribution and open questions
T10 chatbot knowledge base contains the explicit user question
"""

import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

PASS = 0
FAIL = 0
FAILED = []


def check(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'[PASS] {name}')
    else:
        FAIL += 1
        FAILED.append(name)
        print(f'[FAIL] {name} {detail}')


from services.metadata_llm import (  # noqa: E402
    CANONICAL_FIELDS,
    MetadataLLMService,
    _canonical_field_name,
    _verbatim,
)

OEL_TEXT = ("Ölexperiment Spektralmessungen\n\n"
            "Die Messungen wurden von Yvonne mit dem Triadsensor unter "
            "tageslicht bedingungnen in der NIRS Werkstatt ausgeführt "
            "25′ raumtemperatur, nicht verdunkelt, 88% Luftfeuchte.\n")


class _FakeClient:
    """Deterministic Ollama stand-in returning a prepared JSON answer."""

    def __init__(self, answer):
        self._answer = answer

    def chat(self, prompt):
        return self._answer

    def is_available(self):
        return True


class _UnavailableClient:
    def chat(self, prompt):
        raise RuntimeError("ollama unreachable")

    def is_available(self):
        return False


# ---------------------------------------------------------------- T1
good = json.dumps({
    "fields": {
        "operator_name": {"value": "Yvonne", "evidence": "von Yvonne"},
        "instrument_type": {"value": "Triadsensor",
                             "evidence": "mit dem Triadsensor"},
        "temperature": {"value": "25", "evidence": "25′ raumtemperatur"},
        "humidity": {"value": "88", "evidence": "88% Luftfeuchte"},
    },
    "questions": [],
})
service = MetadataLLMService(client=_FakeClient(good))
result = service.extract(OEL_TEXT, "Oel_Meta.txt")
check('T1a LLM extraction returns verbatim fields',
      result is not None and set(result['fields']) == {
          'operator_name', 'instrument_type', 'temperature', 'humidity'},
      f'result={result}')
check('T1b canonical field folding works',
      _canonical_field_name('Operator') == 'operator_name'
      and _canonical_field_name('acquisition_time') == 'timestamp'
      and _canonical_field_name('not_a_field') is None,
      'folding broken')

# ---------------------------------------------------------------- T2
hallucinated = json.dumps({
    "fields": {
        "operator_name": {"value": "Yvonne", "evidence": "von Yvonne"},
        "temperature": {"value": "23.5",
                        "evidence": "invented: not in the text"},
    },
    "questions": [],
})
result_h = service.validate(hallucinated, OEL_TEXT.lower(), "x.txt")
check('T2a invented value rejected (not verbatim in source)',
      result_h is not None and 'temperature' not in result_h['fields']
      and any('temperature' in r for r in result_h['rejected']),
      f'result={result_h}')
check('T2b verbatim value kept in the same answer',
      result_h is not None and 'operator_name' in result_h['fields'],
      f'result={result_h}')
check('T2c verbatim guard direct checks',
      _verbatim('Yvonne', OEL_TEXT.lower()) and not _verbatim('Zoraya', OEL_TEXT.lower()),
      'guard wrong')

# ---------------------------------------------------------------- T3
invented_fields = json.dumps({
    "fields": {
        "operator_name": {"value": "Yvonne", "evidence": "von Yvonne"},
        "blood_type": {"value": "A+", "evidence": "made up field"},
    },
    "questions": [],
})
result_f = service.validate(invented_fields, OEL_TEXT.lower(), "x.txt")
check('T3a unknown/invented field name rejected',
      result_f is not None and 'blood_type' not in result_f['fields']
      and any('blood_type' in r for r in result_f['rejected']),
      f'result={result_f}')
check('T3b canonical list has no invented namespaces',
      'blood_type' not in CANONICAL_FIELDS, 'canonical list polluted')

# ---------------------------------------------------------------- T4
with_q = json.dumps({
    "fields": {"operator_name": {"value": "Yvonne", "evidence": "von Yvonne"}},
    "questions": ["Wurde bei 25 oder 23 Grad gemessen?", "  ", 42,
                  "x" * 400],
})
result_q = service.validate(with_q, OEL_TEXT.lower(), "x.txt")
check('T4a questions passed through capped and sanitised',
      result_q is not None
      and result_q['questions'] == ["Wurde bei 25 oder 23 Grad gemessen?"],
      f'questions={result_q["questions"] if result_q else None}')

# ---------------------------------------------------------------- T5
check('T5a non-JSON answer rejected honestly',
      service.validate('{"fields": broken', OEL_TEXT.lower()) is None)
check('T5b None answer rejected honestly', service.validate(None, 'x') is None)
check('T5c empty fields dict -> None (honest, no invented data)',
      service.validate(json.dumps({"fields": {}}), 'x') is None)
offline = MetadataLLMService(client=_UnavailableClient())
check('T5d no LLM fields with unreachable Ollama',
      offline.extract(OEL_TEXT, "x.txt") is None)

# ---------------------------------------------------------------- T6/T7/T8
tmp = tempfile.mkdtemp(prefix='op31_llm_')
prose_path = os.path.join(tmp, 'Oel_Meta.txt')
with open(prose_path, 'w', encoding='utf-8') as f:
    f.write(OEL_TEXT)

from services import project_ingest  # noqa: E402


class _Record:
    def __init__(self, path, name, rid='00000000-0000-0000-0000-000000000009'):
        self.id = rid
        self.name = name
        self.file_extension = Path(path).suffix.lower() or '.txt'
        self.file_category = 'text'

    def get_file_path(self):
        return str(path_holder['p'])


path_holder = {'p': prose_path}
record = _Record(prose_path, 'Oel_Meta.txt')

import services.metadata_llm as mllm  # noqa: E402
mllm_orig = mllm.MetadataLLMService


def run_ki_pass_with_fake(entry, file_path, answer):
    """Run the real _ki_metadata_pass against a fake Ollama client so the
    merge/conflict logic is tested deterministically offline (CI has no
    Ollama; runtime uses the real client via the same code path)."""
    mllm.MetadataLLMService = lambda *a, **k: MetadataLLMService(
        client=_FakeClient(answer))
    try:
        project_ingest._ki_metadata_pass(
            entry, file_path, project_ingest._make_loader(file_path))
    finally:
        mllm.MetadataLLMService = mllm_orig


# T6: KI-first fills fields the regex layer missed. The deterministic prose
# layer extracts operator/instrument/temperature/humidity/location but NOT
# 'notes' - the KI pass must fill it (verbatim) and confirm the rest.
ki_answer = json.dumps({
    "fields": {
        "operator_name": {"value": "Yvonne", "evidence": "von Yvonne"},
        "location": {"value": "NIRS", "evidence": "in der NIRS Werkstatt"},
        "notes": {"value": "nicht verdunkelt", "evidence":
                  ", nicht verdunkelt, 88% Luftfeuchte"},
    },
    "questions": ["Wurde die Messung bei Tageslicht oder verdunkelt wiederholt?"],
})
entry = project_ingest._ingest_single_file(record, prose_path)
check('T6a deterministic base extraction works',
      entry.get('usable') is True and entry['metadata'].get('operator_name') == 'Yvonne',
      f'meta={entry.get("metadata")}')

run_ki_pass_with_fake(entry, prose_path, ki_answer)
check('T6b KI fills fields the deterministic layer missed',
      entry['metadata'].get('notes') == 'nicht verdunkelt'
      and entry['metadata_sources'].get('notes') == 'ki',
      f'meta={entry["metadata"]} sources={entry.get("metadata_sources")}')
check('T6c KI question surfaces on the dataset',
      any('Tageslicht' in q for q in entry.get('open_questions', [])),
      f'questions={entry.get("open_questions")}')

# T7: conflict -> deterministic hard fact wins + escalation. The regex layer
# captures a single word ('Yvonne') while the KI reads the full verbatim name
# ('Yvonne Mueller') - a genuine granularity conflict that must never be
# resolved silently.
conflict_answer = json.dumps({
    "fields": {"operator_name": {"value": "Martin", "evidence": "not in text"}},
    "questions": [],
})
conflict_service = MetadataLLMService(client=_FakeClient(conflict_answer))
result_c = conflict_service.validate(conflict_answer, OEL_TEXT.lower(), 'x')
check('T7a conflicting LLM value without evidence is rejected by the guard',
      result_c is None or 'operator_name' not in result_c['fields'],
      f'result={result_c}')

OEL_TEXT_KONFLIKT = OEL_TEXT.replace('von Yvonne mit', 'von Yvonne Mueller mit')
conflict_path = os.path.join(tmp, 'Oel_Meta_Konflikt.txt')
with open(conflict_path, 'w', encoding='utf-8') as f:
    f.write(OEL_TEXT_KONFLIKT)
conflict_answer_pass = json.dumps({
    "fields": {"operator_name": {"value": "Yvonne Mueller",
                               "evidence": "von Yvonne Mueller"}},
    "questions": [],
})
record_c = _Record(conflict_path, 'Oel_Meta_Konflikt.txt')
entry_c = project_ingest._ingest_single_file(record_c, conflict_path)
check('T7c deterministic hard fact kept',
      entry_c['metadata'].get('operator_name') == 'Yvonne',
      f'meta={entry_c["metadata"]}')
run_ki_pass_with_fake(entry_c, conflict_path, conflict_answer_pass)
check('T7b conflict escalates to open_questions (never silent)',
      any('Metadatenkonflikt' in q and 'Yvonne' in q
          for q in entry_c.get('open_questions', [])),
      f'questions={entry_c.get("open_questions")}')
check('T7d hard fact still wins over the KI conflict',
      entry_c['metadata'].get('operator_name') == 'Yvonne',
      f'meta={entry_c["metadata"]}')

# T8: offline resilience - no Ollama, deterministic metadata survives
entry_off = {'file_name': 'x.txt', 'metadata': {'operator_name': 'Yvonne'}}
mllm.MetadataLLMService = lambda *a, **k: MetadataLLMService(
    client=_UnavailableClient())
try:
    project_ingest._ki_metadata_pass(
        entry_off, prose_path, project_ingest._make_loader(prose_path))
finally:
    mllm.MetadataLLMService = mllm_orig
check('T8a offline: deterministic metadata kept',
      entry_off['metadata'].get('operator_name') == 'Yvonne',
      f'meta={entry_off["metadata"]}')
check('T8b offline: no open questions invented',
      not entry_off.get('open_questions'), f'q={entry_off.get("open_questions")}')

# ---------------------------------------------------------------- T9
assessment = project_ingest._assess_metadata([entry_c, entry_off])
check('T9a assessment carries open questions',
      assessment.get('open_questions'), f'a={assessment.get("open_questions")}')
check('T9b assessment counts KI contribution',
      isinstance(assessment.get('ki_extracted_fields'), int),
      'ki counter missing')

# ---------------------------------------------------------------- T10
from agents.chatbot_agent import ChatbotAgent  # noqa: E402
agent = ChatbotAgent()
context = {
    "per_agent_reports": [],
    "crew_results": {"overall_quality_score": 80.0},
    "datasets": [entry_c],
    "overview_keys": [],
}
output = agent.execute(context)
kb = (output.data or {}).get('knowledge_base') or []
ki_entries = [e for e in kb if e['category'] == 'KI-Metadaten']
check('T10a chatbot carries the explicit user question',
      any('Bitte klären' in e['answer'] and 'Oel_Meta' in e['answer']
          for e in ki_entries),
      f'entries={ki_entries}')
check('T10b chatbot entry keywords include the dataset name',
      all(any('oel_meta' in k for k in e['keywords']) for e in ki_entries)
      if ki_entries else False,
      f'entries={ki_entries}')

# ---------------------------------------------------------------- summary
print()
print(f'OP31 metadata LLM matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED:', FAILED)
    sys.exit(1)
sys.exit(0)
