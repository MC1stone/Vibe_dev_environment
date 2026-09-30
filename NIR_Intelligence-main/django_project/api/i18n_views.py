# NIR Intelligence Platform - i18n JS catalog endpoint (OP48c)
# Serves the active language's translation catalog as JSON so that the
# static JS files can translate their user-facing messages (nirGettext)
# without any external JS i18n dependency. Incomplete catalogs stay
# honest: missing msgids fall back to the msgid in i18n.js.

import json

from django.http import HttpResponse, JsonResponse
from django.utils import translation
from django.utils.translation import trans_real


def _catalog_for_language(lang):
    """Return the {msgid: msgstr} catalog for the given language."""
    t = trans_real.translation(lang or 'de')
    if t is None:
        return {}
    catalog = t._catalog
    return {
        msgid: msgstr
        for msgid, msgstr in catalog.items()
        # gettext catalogs use (context, msgid) tuples for context-aware
        # entries; plain msgids are strings.
        if isinstance(msgid, str) and msgid
    }


def _request_language(request):
    """Resolve the catalog language for an unprefixed (API) route.

    LocaleMiddleware forces settings.LANGUAGE_CODE on prefix-less
    URLs when i18n_patterns with prefix_default_language=False are in
    use, so cookie and Accept-Language negotiation have to be applied
    here explicitly (check_path=False: the URL carries no language).
    """
    return translation.get_language_from_request(request, check_path=False)


def js_catalog_json(request):
    """Serve the negotiated language's catalog (msgid -> msgstr).

    Default: a tiny JavaScript bootstrap assigning window.NIR_I18N_CATALOG
    (for the <script> tag in base.html). ?format=json returns plain JSON
    for tests and debugging.
    """
    lang = _request_language(request)
    catalog = _catalog_for_language(lang)
    if request.GET.get('format') == 'json':
        return JsonResponse({'language': lang, 'catalog': catalog},
                            content_type='application/json')
    payload = json.dumps({'language': lang, 'catalog': catalog},
                         ensure_ascii=False, separators=(',', ':'))
    body = (
        'window.NIR_I18N_LANGUAGE = %s;\n'
        'window.NIR_I18N_CATALOG = %s.catalog;\n' % (json.dumps(lang), payload)
    )
    return HttpResponse(body, content_type='application/javascript; charset=utf-8')


def i18n_status(request):
    """Small status endpoint for tests/debugging (OP48c)."""
    lang = _request_language(request)
    return JsonResponse({
        'language': lang,
        'catalog_entries': len(_catalog_for_language(lang)),
    })
