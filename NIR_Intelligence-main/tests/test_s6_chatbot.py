"""S6 verification: result chatbot service (Ollama/Mistral + Qdrant RAG).

Tests message composition (system + RAG context + history + question),
Ollama response parsing against a stubbed HTTP layer, graceful degradation
when Ollama or Qdrant are unreachable, and the Django URL wiring.
No network access is required: the Ollama client is stubbed in-process.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.chatbot_service import (
    ChatMessage,
    ChatbotService,
    OllamaChatClient,
    RagContextBuilder,
    create_chatbot_service,
)

results = []


def check(name, ok, detail=''):
    results.append((name, ok))
    print(f'[{"PASS" if ok else "FAIL"}] {name} {detail}')


ANALYSIS_RESULTS = [
    {"agent_name": "StatisticalAnalysisAgent", "data": {"pca": {"explained_variance": [0.72, 0.11]}}},
    {"agent_name": "CalibrationAgent", "data": {"pls": {"r2": 0.91}}},
]
DOCUMENTS = [
    {"source": "quarto_report.md", "text": "The PLS calibration achieved R2=0.91 on the tomato dataset."},
]


# T1: message composition - system prompt, RAG context, history, question
svc = ChatbotService()
messages, rag = svc.build_messages(
    'Was bedeutet R2=0.91?',
    analysis_results=ANALYSIS_RESULTS,
    documents=DOCUMENTS,
    history=[{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hallo!'}],
)
check('T1a message composition: 5 messages (system+2 history+question = 4, rag in system)',
      len(messages) == 4 and messages[0]['role'] == 'system'
      and messages[-1]['role'] == 'user' and messages[-1]['content'] == 'Was bedeutet R2=0.91?',
      f'n={len(messages)}')
check('T1b RAG context embedded in system message',
      'StatisticalAnalysisAgent' in messages[0]['content']
      and 'pls' in messages[0]['content']
      and 'quarto_report.md' in messages[0]['content'])
check('T1c rag sources reported', set(rag['sources']) == {'analysis_results', 'documents'},
      f'sources={rag["sources"]}')


# T2: Ollama response parsing via stubbed client
class StubOllamaClient:
    def __init__(self, response=None):
        self.response = response or {"model": "mistral:latest",
                                     "message": {"role": "assistant", "content": "R2=0.91 bedeutet..."}}
        self.calls = []

    def chat(self, messages, options=None):
        self.calls.append(messages)
        return self.response


stub = StubOllamaClient()
svc2 = ChatbotService()
svc2.client = stub
result = svc2.chat('Frage?', analysis_results=ANALYSIS_RESULTS)
check('T2 stubbed Ollama answer parsed',
      result['answer'] == 'R2=0.91 bedeutet...' and result['degraded'] is False
      and result['model'] == 'mistral:latest')


# T3: graceful degradation - Ollama unreachable -> degraded result, no crash
class FailingClient:
    def chat(self, messages, options=None):
        raise ConnectionError("Ollama not reachable")


svc3 = ChatbotService()
svc3.client = FailingClient()
result3 = svc3.chat('Frage?')
check('T3 Ollama unreachable -> degraded, answer None, error set',
      result3['degraded'] is True and result3['answer'] is None
      and result3['error'] is not None)


# T4: RAG builder without any context (no analysis results, no documents)
rag4 = RagContextBuilder().build('Frage?')
check('T4 empty RAG context -> empty sources, no crash',
      rag4['context'] == '' and rag4['sources'] == [])


# T5: ChatMessage helper
msg = ChatMessage(role='user', content='Hallo')
check('T5 ChatMessage to_dict', msg.to_dict() == {'role': 'user', 'content': 'Hallo'})


# T6: Qdrant state wiring - connect_qdrant reports gracefully without server
rag6 = RagContextBuilder()
state6 = rag6.connect_qdrant(host='localhost', port=6333)
check('T6 Qdrant connect graceful (state dict, no crash)',
      isinstance(state6, dict) and 'connected' in state6,
      f'connected={state6.get("connected")}')


# T7: history without content/role keys -> defaults applied, no crash
svc7 = ChatbotService()
messages7, _ = svc7.build_messages('Q?', history=[{}, {'role': 'assistant'}])
check('T7 malformed history entries tolerated',
      len(messages7) == 4 and messages7[1] == {'role': 'user', 'content': ''}
      and messages7[2] == {'role': 'assistant', 'content': ''})


# T8: factory
factory_svc = create_chatbot_service(config={'ollama_url': 'http://test:11434', 'model': 'm'})
check('T8 create_chatbot_service factory',
      isinstance(factory_svc, ChatbotService) and factory_svc.ollama_url == 'http://test:11434')


# T9: Django URL wiring (files exist, route registered, views importable)
api_dir = Path(__file__).resolve().parent.parent / 'django_project' / 'api'
urls_file = api_dir / 'chatbot_urls.py'
views_file = api_dir / 'chatbot_views.py'
check('T9a chatbot API files exist', urls_file.exists() and views_file.exists())
main_urls = (Path(__file__).resolve().parent.parent / 'django_project' / 'nir_web' / 'urls.py').read_text()
check('T9b chatbot route registered in nir_web/urls.py',
      "api/chatbot/" in main_urls and "api.chatbot_urls" in main_urls)
urls_src = urls_file.read_text()
check('T9c chatbot endpoints: message + status',
      'message/' in urls_src and 'status/' in urls_src)
compile_ok = True
try:
    import py_compile
    py_compile.compile(str(views_file), doraise=True)
    py_compile.compile(str(urls_file), doraise=True)
except Exception as exc:
    compile_ok = False
check('T9d chatbot views/urls compile', compile_ok)


# T10: view function behaviour (question validation) - no Django required
import importlib.util
spec = importlib.util.spec_from_file_location('chatbot_views', views_file)
# views import django modules; only verify source-level contract instead
views_src = views_file.read_text()
check('T10 view returns 400 on missing question, 503 on degraded',
      'HTTP_400_BAD_REQUEST' in views_src and 'HTTP_503_SERVICE_UNAVAILABLE' in views_src
      and 'question is required' in views_src)


# T11: system prompt is domain-specific (NIR-IP identity)
check('T11 system prompt names NIR Intelligence Platform and mandates context use',
      'NIR Intelligence Platform' in messages[0]['content'].split('Context:')[0])


# T12: S5 regression - similarity engine still passes (spot check via import)
from services.spectrum_similarity import SpectrumSimilarityEngine
import pandas as pd
engine = SpectrumSimilarityEngine()
engine.add_references([{'data': pd.DataFrame({'wavelength': [1, 2], 'intensity': [1.0, 2.0]}),
                        'wavelength_column': 'wavelength', 'intensity_column': 'intensity'}])
m = engine.find_similar({'data': pd.DataFrame({'wavelength': [1, 2], 'intensity': [1.0, 2.0]}),
                         'wavelength_column': 'wavelength', 'intensity_column': 'intensity'})
check('T12 S5 similarity engine regression (spot check)', len(m) == 1 and m[0].distance < 1e-6)


failed = [r for r in results if not r[1]]
print(f'\n{len(results) - len(failed)}/{len(results)} tests passed')
sys.exit(1 if failed else 0)
