"""OP76: Ollama-Status und Aktivierung aus der App.

Nutzer-Befund (2026-10-20): 'Ollama funktioniert wieder nicht - das ist
ein entscheidender Faktor der Software.' Deshalb:
1. Status-Endpoint (GET /api/ollama/status/): server-erreichbar? Modell
   vorhanden? - dieselben ehrlichen Kriterien wie der OP50-Probe.
2. Start/Aktivierung (POST /api/ollama/start/): startet den Ollama-
   Container neu und zieht das Modell falls fehlt - mit ehrlichem
   Protokoll (was laeuft, was fehlgeschlagen ist). Der Start geschieht
   ueber docker compose NUR wenn die App im Docker-Stack laeuft
   (NIR_DOCKER_STACK=1) und der Nutzer Staff ist (Diagnose-/Admin-
   Werkzeug); auf dem Host laeuft derselbe Pfad ueber die bekannten
   Kommandos. Nie still: jede Stufe wird im Verlauf gemeldet.
"""
import logging
import os
import shutil
import subprocess
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("Service.OllamaStatus")

START_TIMEOUT = int(os.environ.get("NIR_OLLAMA_START_TIMEOUT", "240"))


def ollama_status(base_url: Optional[str] = None) -> Dict[str, Any]:
    """Vollstaendiger, ehrlicher Ollama-Status fuer die App-Anzeige."""
    from services.ollama_health import (default_base_url,
                                        ollama_model_available,
                                        ollama_reachable)
    url = base_url or default_base_url()
    reachable = ollama_reachable(url, attempts=1, timeout=3)
    model = os.environ.get("NIR_LLM_MODEL", "mistral:latest")
    model_available = False
    if reachable:
        model_available = ollama_model_available(url, model)
    if reachable and model_available:
        state = 'ok'
    elif reachable:
        state = 'model_missing'
    else:
        state = 'offline'
    return {
        'state': state,
        'base_url': url,
        'model': model,
        'server_reachable': reachable,
        'model_available': model_available,
        'in_docker_stack': os.environ.get("NIR_DOCKER_STACK") == "1",
    }


def _run(cmd: list, timeout: int = 60) -> Dict[str, Any]:
    """Subprocess-Aufruf, nie werfend, Ausgabe fuer das Protokoll."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout)
        return {'ok': res.returncode == 0,
                'stdout': (res.stdout or '')[-2000:],
                'stderr': (res.stderr or '')[-2000:]}
    except FileNotFoundError:
        return {'ok': False, 'stdout': '',
                'stderr': f"Kommando nicht gefunden: {cmd[0]}"}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'stdout': '',
                'stderr': f"Timeout nach {timeout}s: {' '.join(cmd[:4])}"}


def start_ollama(base_url: Optional[str] = None,
                 started_by_staff: bool = False) -> Dict[str, Any]:
    """Ollama aus der App aktivieren (OP76).

    Im Docker-Stack: Container neu starten + Modell sicherstellen
    (Pull nur wenn fehlt - kein stiller Multi-GB-Download). Auf dem
    Host: ehrliche Anleitung, da die App dort den systemd-/Prozess-
    Ollama nicht selbst starten darf (kein stiller Daemon aus der
    Web-App heraus).
    """
    from services.ollama_health import default_base_url
    url = base_url or default_base_url()
    protocol: list = []
    status = ollama_status(url)
    if status['state'] == 'ok':
        return {'success': True, 'already_ok': True, 'status': status,
                'protocol': ['Ollama läuft bereits und das Modell ist '
                             'verfügbar.']}
    if not started_by_staff:
        return {'success': False, 'status': status,
                'protocol': ['Nur Staff (Admin) darf Ollama aus der App '
                             'starten.'],
                'reason': 'staff_required'}

    docker_avail = shutil.which('docker') is not None
    in_stack = os.environ.get("NIR_DOCKER_STACK") == "1"
    if in_stack and docker_avail:
        protocol.append('Ollama-Container wird neu gestartet …')
        res = _run(['docker', 'compose', 'restart', 'ollama'],
                   timeout=120)
        protocol.append(('docker compose restart ollama: OK'
                         if res['ok'] else
                         f"docker compose restart ollama: "
                         f"FEHLER - {res['stderr'][:200]}"))
        if not res['ok']:
            return {'success': False, 'status': ollama_status(url),
                    'protocol': protocol, 'reason': 'restart_failed'}
        # warten bis der Server antwortet (healthcheck-Startphase)
        deadline = time.time() + START_TIMEOUT
        reachable = False
        while time.time() < deadline:
            reachable = ollama_status(url)['server_reachable']
            if reachable:
                break
            time.sleep(3)
        protocol.append(('Ollama-Server antwortet.'
                         if reachable else
                         f"Ollama-Server antwortet auch nach "
                         f"{START_TIMEOUT}s nicht."))
        if not reachable:
            return {'success': False, 'status': ollama_status(url),
                    'protocol': protocol, 'reason': 'server_timeout'}
        # Modell sicherstellen (nur wenn fehlt)
        if not ollama_status(url)['model_available']:
            model = status['model']
            protocol.append(f"Modell {model} fehlt - wird geladen "
                            "(einmalig, mehrere GB möglich) …")
            res = _run(['docker', 'compose', 'exec', '-T', 'ollama',
                        'ollama', 'pull', model],
                       timeout=1800)
            protocol.append(('Modell geladen.'
                             if res['ok'] else
                             f"Modell-Pull fehlgeschlagen: "
                             f"{res['stderr'][:200]}"))
    else:
        protocol.append(
            'App läuft nicht im Docker-Stack (oder docker fehlt) - '
            'bitte Ollama manuell starten:')
        protocol.append('  Docker-Stack:  docker compose up -d ollama')
        protocol.append('  Host (systemd): sudo systemctl start ollama')
        protocol.append('  Host (manuell):  ollama serve &')
        protocol.append(f"Danach Modell pruefen: ollama list "
                        f"(erwartet: {status['model']})")
        return {'success': False, 'status': ollama_status(url),
                'protocol': protocol, 'reason': 'not_in_docker_stack'}

    final = ollama_status(url)
    return {'success': final['state'] == 'ok', 'status': final,
            'protocol': protocol}
