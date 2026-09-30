"""OP48 verification: EU multilingualism (i18n) infrastructure.

Implementierungsplan MULTILINGUAL_I18N_IMPLEMENTATIONPLAN.md, Phase 1 (OP48a):
- settings: LANGUAGES = alle 24 EU-Amtssprachen, LOCALE_PATHS,
  LocaleMiddleware, LANGUAGE_CODE 'de' (Default, unprefixiert)
- urls: i18n_patterns nur fuer UI-Seiten (prefix_default_language=False,
  API-Routen ohne Sprachpraefix), set_language-Route (/i18n/)
- locale: .po-Kataloge fuer de/en angelegt (aktiv vollstaendig);
  compilemessages-faehige Struktur

Diese Matrix verifiziert den Vertrag offline (Django-Test-Client);
keine Netz- oder Container-Abhaengigkeit.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
os.environ.setdefault('DJANGO_ALLOWED_HOSTS', 'testserver')
sys.path.insert(0, str(PROJECT := Path(__file__).resolve().parent.parent / 'django_project'))

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


# ---------------------------------------------------------------------------
# T1: settings contract (24 EU languages, locale paths, middleware)
# ---------------------------------------------------------------------------
import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402

EU_LANGUAGES = {
    'bg', 'hr', 'cs', 'da', 'nl', 'en', 'et', 'fi', 'fr', 'de', 'el', 'hu',
    'ga', 'it', 'lv', 'lt', 'mt', 'pl', 'pt', 'ro', 'sk', 'sl', 'es', 'sv',
}

check('T1a LANGUAGES defines exactly 24 EU official languages',
      len(settings.LANGUAGES) == 24
      and {code for code, _name in settings.LANGUAGES} == EU_LANGUAGES)
check('T1b LANGUAGE_CODE default is de', settings.LANGUAGE_CODE == 'de')
check('T1c USE_I18N enabled', settings.USE_I18N is True)
check('T1d LOCALE_PATHS points to django_project/locale',
      len(settings.LOCALE_PATHS) == 1 and str(settings.LOCALE_PATHS[0]).endswith('locale'))
check('T1e LocaleMiddleware active',
      any('LocaleMiddleware' in mw for mw in settings.MIDDLEWARE))
check('T1f LocaleMiddleware after SessionMiddleware',
      settings.MIDDLEWARE.index('django.middleware.locale.LocaleMiddleware')
      > settings.MIDDLEWARE.index('django.contrib.sessions.middleware.SessionMiddleware'))

# ---------------------------------------------------------------------------
# T2: locale catalogs (de/en active, po structure valid)
# ---------------------------------------------------------------------------
LOCALE_DIR = Path(settings.LOCALE_PATHS[0])
for lang in ('de', 'en'):
    po = LOCALE_DIR / lang / 'LC_MESSAGES' / 'django.po'
    check(f'T2a {lang} po catalog exists', po.exists())
    if po.exists():
        content = po.read_text(encoding='utf-8')
        check(f'T2b {lang} po catalog has valid header',
              'Content-Type: text/plain; charset=UTF-8' in content
              and f'"Language: {lang}\\n"' in content)

# ---------------------------------------------------------------------------
# T3: URL wiring (unprefixed default, prefixed other languages, API stable)
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402

client = Client()

check('T3a home reverses unprefixed (default language)', reverse('home') == '/')
check('T3b dashboard reverses unprefixed', reverse('dashboard') == '/dashboard/')
check('T3c set_language route wired',
      reverse('set_language') == '/i18n/setlang/')

response = client.post('/i18n/setlang/', data={'language': 'en'})
check('T3d set_language switches to en (302 + cookie)',
      response.status_code == 302
      and client.cookies.get('django_language', '').value == 'en')

response = client.get('/en/dashboard/')
check('T3e /en/dashboard/ renders 200', response.status_code == 200)
response = client.get('/de/dashboard/')
check('T3f default language de only reachable unprefixed (404 on /de/ prefix)',
      response.status_code == 404)
response = client.get('/dashboard/')
check('T3g unprefixed /dashboard/ renders 200 (backward compat)',
      response.status_code == 200)
response = client.get('/fr/dashboard/')
check('T3h /fr/dashboard/ renders 200 (any EU language prefixable)',
      response.status_code == 200)

response = client.get('/api/chatbot/status/')
check('T3i API routes stay unprefixed and answer', response.status_code == 200)
check('T3j api-docs route unprefixed', reverse('api-docs') == '/api/')

# non-EU prefix is rejected, not silently served
response = client.get('/zz/dashboard/')
check('T3k non-EU language prefix gets redirected (no fake locale)',
      response.status_code in (302, 404))

# ---------------------------------------------------------------------------
# T4b: catalogs are complete (no empty msgstr except the header)
# ---------------------------------------------------------------------------
for lang in ('de', 'en'):
    po = LOCALE_DIR / lang / 'LC_MESSAGES' / 'django.po'
    lines = po.read_text(encoding='utf-8').split('\n')
    empty = [lines[i] for i in range(len(lines) - 1)
             if lines[i].startswith('msgid "') and lines[i] != 'msgid ""'
             and lines[i + 1].strip() == 'msgstr ""']
    check(f'T4b {lang} catalog has no untranslated entries', not empty,
          str(empty[:3]))

# ---------------------------------------------------------------------------
# T5: OP48b localized templates render per language (de/en)
# ---------------------------------------------------------------------------
from django.template.loader import get_template  # noqa: E402

localized_pages = {
    '/': ('Der Analyse-Workflow', 'Neues Projekt anlegen'),
    '/en/': ('The analysis workflow', 'Create new project'),
    '/chatbot/': ('Analyse-Chatbot', 'Unterhaltung', 'Senden'),
    '/en/chatbot/': ('Analysis Chatbot', 'Conversation', 'Send'),
    '/login/': ('Anmelden', 'Passwort'),
    '/en/login/': ('Sign In', 'Password'),
    '/ilias/': ('ILIAS öffnen',),
    '/federated/': ('Einwilligung erteilen',),
    '/en/federated/': ('Grant consent',),
}
for url, needles in localized_pages.items():
    response = client.get(url)
    body = response.content.decode()
    ok = response.status_code == 200 and all(n in body for n in needles)
    check(f'T5 {url} renders localized', ok,
          f'status={response.status_code} missing={[n for n in needles if n not in body]}')

# language switcher present on every page (base.html)
body = client.get('/').content.decode()
check('T5b language switcher in base template',
      'id="language-select"' in body and body.count('<option') == 24
      and 'setlang' in body)

# html lang attribute follows active language
body = client.get('/en/').content.decode()
check('T5c html lang=en on /en/', '<html lang="en">' in body)
body = client.get('/').content.decode()
check('T5d html lang=de on default', '<html lang="de">' in body)

# ---------------------------------------------------------------------------
# T4: compilemessages-compatible po files (no syntax errors)
# ---------------------------------------------------------------------------
try:
    from django.core.management import call_command
    try:
        call_command('compilemessages', verbosity=0)
        check('T4a compilemessages runs clean', True)
    except Exception as exc:  # pragma: no cover - environment-dependent
        check('T4a compilemessages runs clean', False, str(exc))
except ImportError:
    check('T4a compilemessages runs clean', False, 'django.core.management missing')

# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------
print(f'\nOP48 i18n infrastructure: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED:', ', '.join(FAILED))
    sys.exit(1)
sys.exit(0)
