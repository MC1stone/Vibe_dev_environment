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
# T6: OP48c - JS localization (catalog endpoint, i18n.js, base.html wiring)
# ---------------------------------------------------------------------------
import json as _json  # noqa: E402

js_dir = (Path(__file__).resolve().parent.parent / 'django_project'
          / 'static' / 'js')

# T6a: catalog endpoint serves negotiated JS bootstrap (default de)
resp = client.get('/js-i18n/')
body_js = resp.content.decode()
check('T6a /js-i18n/ serves JS bootstrap (de)',
      resp.status_code == 200
      and 'window.NIR_I18N_CATALOG' in body_js
      and resp['Content-Type'].startswith('application/javascript'))

# T6b: ?format=json returns plain JSON with catalog dict
resp = client.get('/js-i18n/?format=json')
try:
    data = resp.json()
except Exception:
    data = {}
check('T6b /js-i18n/?format=json returns catalog dict',
      resp.status_code == 200 and isinstance(data.get('catalog'), dict))

# T6c: Accept-Language switches the catalog language (en)
resp = client.get('/js-i18n/?format=json', HTTP_ACCEPT_LANGUAGE='en')
data_en = resp.json() if resp.status_code == 200 else {}
check('T6c Accept-Language=en yields en catalog',
      data_en.get('language') == 'en'
      and data_en.get('catalog', {}).get('Projects') == 'Projects')

# T6d: cookie django_language switches the catalog language (en)
c2 = Client()
c2.cookies.load({'django_language': 'en'})
resp = c2.get('/js-i18n/?format=json')
data_ck = resp.json() if resp.status_code == 200 else {}
check('T6d django_language cookie yields en catalog',
      data_ck.get('language') == 'en'
      and data_ck.get('catalog', {}).get('Projects') == 'Projects')

# T6e: default de catalog translates a JS msgid (fresh client: no cookie)
resp = Client().get('/js-i18n/?format=json')
data_de = resp.json() if resp.status_code == 200 else {}
check('T6e default de catalog translates JS msgid',
      data_de.get('language') == 'de'
      and data_de.get('catalog', {}).get(
          'Please select at least one file to upload.') is not None
      and data_de['catalog'].get(
          'Please select at least one file to upload.') != 'Please select at least one file to upload.')

# T6f: i18n status endpoint (unprefixed API contract)
resp = client.get('/api/i18n/status/')
st = resp.json() if resp.status_code == 200 else {}
check('T6f /api/i18n/status/ contract',
      resp.status_code == 200 and 'language' in st
      and isinstance(st.get('catalog_entries'), int))

# T6g: i18n.js helper file exists and exposes nirGettext fallback
i18n_js = (js_dir / 'i18n.js').read_text(encoding='utf-8')
check('T6g i18n.js exposes nirGettext/nirInterpolate',
      'window.nirGettext' in i18n_js
      and 'window.nirInterpolate' in i18n_js)

# T6h: base.html loads catalog bootstrap + helper before main.js
base_html = (Path(__file__).resolve().parent.parent / 'django_project'
             / 'templates' / 'base.html').read_text(encoding='utf-8')
pos_catalog = base_html.find('js-i18n-catalog')
pos_helper = base_html.find("js/i18n.js")
pos_main = base_html.find("js/main.js")
check('T6h base.html wires catalog + i18n.js before main.js',
      0 < pos_catalog < pos_helper < pos_main)

# T6i: JS msgids present in compiled de catalog (spot checks)
catalog_de = data_de.get('catalog', {})
js_msgids = [
    'Files uploaded successfully!',
    'Job created successfully!',
    'Spectrum not found',
    'Success!',
    'Unknown error',
]
missing = [m for m in js_msgids if not catalog_de.get(m)]
check('T6i JS msgids translated in de catalog', not missing, str(missing))

# T6j: page scripts use nirGettext for user-facing messages
files_js = (js_dir / 'files.js').read_text(encoding='utf-8')
check('T6j files.js uses nirGettext (no bare alert literals left)',
      'nirGettext(' in files_js
      and "alert('" not in files_js)

# ---------------------------------------------------------------------------
# T7: OP48d - backend API messages localized (gettext + language middleware)
# ---------------------------------------------------------------------------
api_dir = (Path(__file__).resolve().parent.parent / 'django_project' / 'api')

# T7a: all api view modules use gettext for error/message strings
import glob as _glob  # noqa: E402
import re as _re  # noqa: E402
api_files = sorted(_glob.glob(str(api_dir / '*.py')))
with_gettext = [
    f for f in api_files
    if 'i18n_views' not in f
    and 'from django.utils.translation import gettext' in
    Path(f).read_text(encoding='utf-8')
]
check('T7a api view modules import gettext', len(with_gettext) >= 8,
      f'{len(with_gettext)} modules')

# T7b: no bare untranslated error literals left in api views
bare = []
for f in api_files:
    if 'i18n_views' in f:
        continue
    src = Path(f).read_text(encoding='utf-8')
    for m in _re.finditer(r"['\"]error['\"]\s*:\s*['\"]([^'\"]*)['\"]", src):
        bare.append((Path(f).name, m.group(1)))
check('T7b no bare error literals left in api views', not bare, str(bare[:5]))

# T7c: chatbot error localized in de (fresh client, default language)
resp = Client().post('/api/chatbot/message/', {}, HTTP_ACCEPT_LANGUAGE='de')
err_de = resp.json().get('error') if resp.status_code == 200 or resp.status_code == 400 else None
check('T7c chatbot 400 error localized (de)',
      resp.status_code == 400 and err_de == 'question ist erforderlich',
      f'{resp.status_code} {err_de}')

# T7d: chatbot error localized in en (Accept-Language)
resp = Client().post('/api/chatbot/message/', {}, HTTP_ACCEPT_LANGUAGE='en')
err_en = resp.json().get('error') if resp.status_code == 400 else None
check('T7d chatbot error follows Accept-Language (en)',
      resp.status_code == 400 and err_en == 'question is required',
      f'{resp.status_code} {err_en}')

# T7e: chatbot error follows django_language cookie (en)
c3 = Client()
c3.cookies.load({'django_language': 'en'})
resp = c3.post('/api/chatbot/message/', {})
err_ck = resp.json().get('error') if resp.status_code == 400 else None
check('T7e chatbot error follows cookie (en)',
      resp.status_code == 400 and err_ck == 'question is required',
      f'{resp.status_code} {err_ck}')

# T7f: ApiLanguageMiddleware wired in settings
check('T7f ApiLanguageMiddleware in MIDDLEWARE',
      'nir_web.api_language_middleware.ApiLanguageMiddleware'
      in settings.MIDDLEWARE)

# T7g: backend msgids present in de catalog (spot checks)
resp = Client().get('/js-i18n/?format=json')
cat = resp.json().get('catalog', {}) if resp.status_code == 200 else {}
spot = ['File not found', 'Report not found', 'Method not allowed',
        'question is required', 'Workflow orchestrator not available']
missing_be = [m for m in spot if not cat.get(m)]
check('T7g backend msgids in compiled de catalog', not missing_be,
      str(missing_be))

# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------
print(f'\nOP48 i18n infrastructure: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED:', ', '.join(FAILED))
    sys.exit(1)
sys.exit(0)
