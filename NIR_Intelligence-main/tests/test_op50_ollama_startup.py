#!/usr/bin/env python3
# OP50 test matrix: robust Ollama startup -> LLM-first analysis
# (99% LLM / 1% fallback instead of permanent fallback after slow starts).
# Offline-safe: no network access required; probes are monkeypatched/mocked.
import os
import sys
import time
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "django_project"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")

PASS = 0
FAIL = 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {detail}")


# T1: ollama_health module contract
try:
    from services import ollama_health
    check("T1a ollama_health module importable", True)
except Exception as exc:
    check("T1a ollama_health module importable", False, str(exc))
    sys.exit(1)

check("T1b OLLAMA_URL wins over default base url",
      ollama_health.default_base_url() == "http://ollama:11434"
      if os.environ.get("OLLAMA_URL") == "http://ollama:11434"
      else ollama_health.default_base_url() == "http://localhost:11434")

with mock.patch.dict(os.environ, {"OLLAMA_URL": "http://unit-test:11434"}):
    check("T1c default_base_url reads OLLAMA_URL",
          ollama_health.default_base_url() == "http://unit-test:11434")

ollama_health.reset_cache()


class FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code


def fake_requests_get_factory(call_log, fail_first=0, status=200):
    state = {"n": 0}

    def fake_get(url, timeout=None):
        state["n"] += 1
        call_log.append(url)
        if state["n"] <= fail_first:
            raise OSError("connection refused (startup)")
        return FakeResponse(status)
    return fake_get


calls = []
probe_state = {"n": 0}

def fake_probe(url, timeout=None, fail_first=2):
    probe_state["n"] += 1
    calls.append(url)
    return probe_state["n"] > fail_first

import services.ollama_health as oh_mod
with mock.patch.object(oh_mod, "_probe_once", side_effect=fake_probe):
    oh_mod.reset_cache()
    start = time.monotonic()
    ok = oh_mod.ollama_reachable("http://probe-a:11434", attempts=5,
                                 timeout=0.01, backoff=0.01)
    duration = time.monotonic() - start
check("T2a retry probe succeeds after slow start (fail 2, then up)", ok)
check("T2b probe retried exactly 3 times", len(calls) == 3,
      f"calls={calls}")
check("T2c backoff applied (duration >= 2*backoff)", duration >= 0.02)

# cached success: no further probes within TTL
calls.clear()
with mock.patch.object(oh_mod, "_probe_once", side_effect=fake_probe):
    ok2 = oh_mod.ollama_reachable("http://probe-a:11434", attempts=5,
                                  timeout=0.01, backoff=0.01)
check("T2d success cached within TTL (no re-probe)", ok2 and len(calls) == 0)

# failure path: retries exhausted, honest False, cached failure
fail_probe = mock.Mock(return_value=False)
with mock.patch.object(oh_mod, "_probe_once", fail_probe):
    oh_mod.reset_cache()
    ok3 = oh_mod.ollama_reachable("http://probe-b:11434", attempts=3,
                                  timeout=0.01, backoff=0.01)
check("T2e exhausted retries -> honest False", ok3 is False)
check("T2f failure probed attempts times", fail_probe.call_count == 3)

# T3: consumers use the robust probe
try:
    import django
    django.setup()
    from services.metadata_llm import OllamaMetadataClient
    from services.chatbot_service import OllamaChatClient
    from services.embedding_service import OllamaEmbeddingClient
    from services.sensor_websearch import ollama_available
    check("T3a all Ollama clients importable", True)
except Exception as exc:
    check("T3a all Ollama clients importable", False, str(exc))
    sys.exit(1)

probe_calls = []
model_calls = []
with mock.patch.object(oh_mod, "ollama_reachable",
                       side_effect=lambda url, **kw: probe_calls.append(url) or True), \
     mock.patch.object(oh_mod, "ollama_model_available",
                       side_effect=lambda url, model=None, **kw: model_calls.append((url, model)) or True):
    ok = (OllamaMetadataClient().is_available()
          and OllamaChatClient("http://x:11434").is_available()
          and OllamaEmbeddingClient("http://x:11434").is_available()
          and ollama_available("http://x:11434"))
check("T3b metadata/chat(embedding model-aware)/embedding/websearch use robust probe",
      ok and len(probe_calls) == 2 and len(model_calls) == 2,
      f"probe_calls={probe_calls} model_calls={model_calls}")

# T4: project_crew LLM gate uses robust probe (not a 2s one-shot GET)
src = (Path(__file__).resolve().parent.parent
       / "services" / "project_crew.py").read_text(encoding="utf-8")
check("T4a project_crew gate uses ollama_reachable",
      "ollama_reachable" in src and "timeout=2" not in src)

# T4b/T4c: chat call survives the model cold start (retry on timeout,
# configurable timeout instead of the previous fixed 60s read timeout)
import requests as _requests
from services.metadata_llm import OllamaMetadataClient

check("T4b metadata client timeout configurable (NIR_LLM_TIMEOUT, default 120)",
      OllamaMetadataClient(timeout=None).timeout == 120
      if "NIR_LLM_TIMEOUT" not in os.environ
      else OllamaMetadataClient(timeout=None).timeout == int(os.environ["NIR_LLM_TIMEOUT"]))

call_count = {"n": 0}

def flaky_post(url, json=None, timeout=None):
    call_count["n"] += 1
    if call_count["n"] == 1:
        raise _requests.exceptions.Timeout("read timed out (cold start)")
    return mock.Mock(status_code=200, json=lambda: {"message": {"content": "{}"}})

with mock.patch.object(_requests, "post", side_effect=flaky_post):
    client = OllamaMetadataClient(timeout=120)
    content = client.chat("prompt")
check("T4c chat retries once after cold-start read timeout", content == "{}" and call_count["n"] == 2)

call_count["n"] = 0
timeout_post = mock.Mock(side_effect=_requests.exceptions.Timeout("down"))
with mock.patch.object(_requests, "post", timeout_post):
    try:
        OllamaMetadataClient(timeout=120).chat("prompt")
        raised = False
    except _requests.exceptions.Timeout:
        raised = True
check("T4d exhausted chat retries raise honestly (caller catches non-fatal)",
      raised and timeout_post.call_count == 2)

# T4e: model-aware probe - reachable Ollama without the model must
# report unavailable (an implicit multi-GB pull would time out anyway)
from services.ollama_health import ollama_model_available, reset_cache

reset_cache()
payload_up = {"models": [{"name": "mistral:latest"}, {"name": "nomic-embed-text:latest"}]}
with mock.patch.object(oh_mod, "_probe_once", return_value=True):
    with mock.patch("requests.get",
                    return_value=mock.Mock(status_code=200, json=lambda: payload_up)):
        reset_cache()
        check("T4e model present -> model probe True",
              ollama_model_available("http://x:11434", "mistral"))
        reset_cache()
        check("T4f model missing -> model probe False (honest, no silent pull)",
              not ollama_model_available("http://x:11434", "llama3"))
        reset_cache()
        check("T4g bare family name matches :latest tag",
              ollama_model_available("http://x:11434", "mistral:latest"))

# T5: compose wiring - services wait for healthy ollama
import yaml
compose = yaml.safe_load(
    (Path(__file__).resolve().parent.parent / "docker-compose.yml").read_text())
check("T5a dev django_app waits for healthy ollama",
      compose["services"]["django_app"]["depends_on"]["ollama"]
      == {"condition": "service_healthy"})
check("T5b dev background_crew waits for healthy ollama",
      compose["services"]["background_crew"]["depends_on"]["ollama"]
      == {"condition": "service_healthy"})
bc_env = compose["services"]["background_crew"]["environment"]
check("T5c dev background_crew has OLLAMA_URL",
      any(e.startswith("OLLAMA_URL=http://ollama:11434") for e in bc_env))
check("T5d dev ollama keep-alive set",
      "OLLAMA_KEEP_ALIVE=24h" in compose["services"]["ollama"]["environment"])
hc = compose["services"]["ollama"]["healthcheck"]
check("T5e dev ollama healthcheck tolerant to slow start",
      hc.get("start_period") == "60s" and int(hc["retries"]) >= 10)

prod = yaml.safe_load(
    (Path(__file__).resolve().parent.parent / "docker-compose.prod.yml").read_text())
prod_web_dep = prod["services"]["web"]["depends_on"].get("ollama")
check("T5f prod web waits for healthy ollama",
      prod_web_dep == {"condition": "service_healthy"})

host_backend = yaml.safe_load(
    (Path(__file__).resolve().parent.parent
     / "packaging" / "docker-compose.host-backend.yml").read_text())
check("T5g host-backend ollama healthcheck + keep-alive",
      host_backend["services"]["ollama"].get("healthcheck") is not None
      and "OLLAMA_KEEP_ALIVE=24h" in host_backend["services"]["ollama"]["environment"])

# T5h: consistent container name + automatic model loader (ollama_init)
check("T5h dev ollama container_name nir_ollama (replaces the legacy 6-week container)",
      compose["services"]["ollama"].get("container_name") == "nir_ollama")
init = compose["services"].get("ollama_init")
check("T5i dev ollama_init one-shot model loader present",
      init is not None and init.get("restart") == "no"
      and init["depends_on"]["ollama"] == {"condition": "service_healthy"})
check("T5j dev ollama_init pulls NIR_LLM_MODEL + NIR_EMBEDDING_MODEL idempotently",
      init is not None and "ollama pull" in init["command"][0]
      and "NIR_LLM_MODEL" in init["command"][0]
      and "NIR_EMBEDDING_MODEL" in init["command"][0]
      and "bereits vorhanden" in init["command"][0])
check("T5k prod ollama container_name nir_ollama (stringency)",
      prod["services"]["ollama"].get("container_name") == "nir_ollama"
      and "ollama pull" in prod["services"]["ollama_init"]["command"][0])
check("T5l host-backend ollama_init present",
      "ollama pull" in host_backend["services"]["ollama_init"]["command"][0])

# T5m: ILIAS waits for a healthy MariaDB (no more DB race -> crash loop)
check("T5m dev ilias depends on healthy ilias_db (no startup DB race)",
      compose["services"]["ilias"]["depends_on"]["ilias_db"]
      == {"condition": "service_healthy"})
hc_db = compose["services"]["ilias_db"].get("healthcheck") or {}
check("T5n dev ilias_db has a healthcheck tolerant to slow first init",
      "mysqladmin" in (hc_db.get("test") or [""])[-1]
      and int(hc_db.get("retries", 0)) >= 20)
check("T5o prod ilias depends on healthy ilias_db",
      prod["services"]["ilias"]["depends_on"]["ilias_db"]
      == {"condition": "service_healthy"})

print(f"\nOP50 ollama robust startup matrix: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
