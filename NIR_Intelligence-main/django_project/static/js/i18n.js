/**
 * NIR_Mistral Framework - i18n helper (OP48c)
 * Bridges Django's translation catalogs to static JavaScript files.
 * The catalog is injected by the js18n-catalog script tag in base.html
 * (django.views.i18n.JavaScriptCatalog rendered as JSON via the
 * js18n_json view). No external JS dependency.
 */
(function () {
    'use strict';

    var catalog = window.NIR_I18N_CATALOG || {};
    window.NIR_I18N_CATALOG = catalog;

    /**
     * Translate a msgid. Falls back to the msgid itself when no catalog
     * entry exists (honest fallback, no invented translations).
     */
    function gettext(msgid) {
        return Object.prototype.hasOwnProperty.call(catalog, msgid)
            ? catalog[msgid]
            : msgid;
    }

    /**
     * Translate with a {placeholder} interpolation:
     * interpolate('Deleted {count} files.', {count: 3}, false)
     */
    function interpolate(fmt, obj, named) {
        if (named === undefined) { named = true; }
        if (!obj) { return fmt; }
        var result = fmt;
        if (named) {
            Object.keys(obj).forEach(function (key) {
                result = result.split('{' + key + '}').join(String(obj[key]));
            });
        }
        return result;
    }

    window.nirGettext = gettext;
    window.nirInterpolate = interpolate;
    window.NIR_I18N = { gettext: gettext, interpolate: interpolate };
})();
