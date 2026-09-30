# NIR Intelligence Platform - API language middleware (OP48d)
# LocaleMiddleware forces settings.LANGUAGE_CODE on prefix-less URLs
# (i18n_patterns with prefix_default_language=False). API routes are
# deliberately unprefixed, so cookie / Accept-Language negotiation must
# be re-applied there for translated API messages.

from django.utils import translation


class ApiLanguageMiddleware:
    """Re-negotiate the active language for unprefixed API routes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info.startswith(('/api/', '/js-i18n/')):
            language = translation.get_language_from_request(
                request, check_path=False)
            translation.activate(language)
        response = self.get_response(request)
        if response.status_code != 204:
            response.setdefault('Content-Language', translation.get_language())
        return response
