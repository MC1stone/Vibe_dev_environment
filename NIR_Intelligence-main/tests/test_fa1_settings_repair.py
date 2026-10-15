#!/usr/bin/env python3
"""Settings-Seite reparieren (FA1-Umfeld, Vorfall 2026-10-15).

Die Einstellungsseite war 'komplett inaktiv' mit zwei Ursachen:
  - main.js wurde doppelt geladen (base.html UND settings.html) ->
    Uncaught SyntaxError: Identifier 'NIR_MISTRAL' has already been declared
  - /api/users/preferences/ existierte nicht (404) - Model und Serializer
    existierten bereits, nur View/Route fehlten.

Matrix prueft: Duplikat-Script entfernt, Preferences-Endpoint GET/PUT
(get_or_create, Teil-Update), Route registriert.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'django_project'))

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


# --- Django offline aufsetzen (wie FA1-Matrix) ---------------------------
import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='settings-repair-test',
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3',
                                'NAME': ':memory:'}},
        INSTALLED_APPS=[
            'django.contrib.contenttypes', 'django.contrib.auth',
            'django.contrib.sessions', 'core', 'api',
        ],
        MIDDLEWARE=[],
        ROOT_URLCONF=None,
        USE_TZ=True,
        NIR_FRAMEWORK_PATH=str(ROOT),
        QUARTO_PATH='quarto',
    )
django.setup()

from django.core.management import call_command  # noqa: E402
call_command('migrate', verbosity=0, interactive=False)

from django.test import RequestFactory  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()

# --- T1: main.js nur noch einmal geladen ---------------------------------
base_html = (ROOT / 'django_project' / 'templates' / 'base.html'
             ).read_text(encoding='utf-8')
settings_html = (ROOT / 'django_project' / 'templates' / 'settings.html'
                 ).read_text(encoding='utf-8')
check('T1a base.html laedt main.js einmal',
      base_html.count('js/main.js') == 1, str(base_html.count('js/main.js')))
check('T1b settings.html laedt main.js nicht mehr doppelt',
      settings_html.count('js/main.js') == 0,
      str(settings_html.count('js/main.js')))

# --- T2: Route registriert ------------------------------------------------
urls_src = (ROOT / 'django_project' / 'nir_web' / 'urls.py'
            ).read_text(encoding='utf-8')
check('T2a Route api/users/preferences/ registriert',
      'api/users/preferences/' in urls_src)
check('T2b UserPreferencesView importiert',
      'UserPreferencesView' in urls_src)

# --- T3: GET legt Preferences an und liefert sie --------------------------
from api.views import UserPreferencesView  # noqa: E402

rf = RequestFactory()
user = User.objects.create_user('sruser', 'sr@example.com', 'Passwort123')


def _req(method, payload=None):
    req = getattr(rf, method)('/api/users/preferences/',
                               data=payload or {},
                               content_type='application/json')
    req.data = payload or {}
    req.user = user
    return req


view = UserPreferencesView()
resp = view.get(_req('get'))
check('T3a GET liefert 200 mit Defaults',
      resp.status_code == 200 and resp.data.get('theme') == 'light',
      f'status={resp.status_code} data_keys={list(resp.data)[:5]}')

# --- T4: PUT aktualisiert Teilmenge -------------------------------------
resp = view.put(_req('put', {'theme': 'dark',
                             'email_notifications': False}))
check('T4a PUT aktualisiert theme und email_notifications',
      resp.status_code == 200 and resp.data.get('theme') == 'dark'
      and resp.data.get('email_notifications') is False,
      f'status={resp.status_code}')

resp = view.get(_req('get'))
check('T4b GET liefert aktualisierte Werte',
      resp.data.get('theme') == 'dark')

# --- T5: ungültige Daten -> 400 ------------------------------------------
resp = view.put(_req('put', {'theme': None}))
check('T5a PUT mit ungueltigen Daten -> 400',
      resp.status_code == 400, f'status={resp.status_code}')

print(f'\nSettings-Repair-Matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', FAILED)
    sys.exit(1)
