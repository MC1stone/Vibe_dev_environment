# Implementierungsplan: EU-Mehrsprachigkeit (i18n) für die NIR-IP

Status: **PLAN — wartet auf Head-of-Development-Freigabe** (nicht in Roadmap S1–S9;
gemäß `AGENTS.md` §Abgleichs-Regel vor Umsetzung als neuer Schritt, z. B. **OP48**,
in `REPOSITORY_ALIGNMENT_AND_ROADMAP.md` aufzunehmen und `TASK.md` umzuschreiben).

## 1. Ist-Aufnahme (Befund)

- `django_project/nir_web/settings.py`: `USE_I18N = True` bereits gesetzt,
  `LANGUAGE_CODE = 'en-us'` — aber **kein** `LOCALE_PATHS`, keine
  `LocaleMiddleware`, keine `i18n_patterns`, keine `.po`/`.mo`-Dateien.
- 26 Django-Templates (`django_project/templates/*.html`) mit hart-codierten
  englischen UI-Texten (z. T. deutsch, z. B. FL4 „Föderiert“-Nav-Link) —
  keinerlei `{% trans %}`/`{% blocktrans %}`.
- Frontend-JS (`django_project/static/js/*.js`, Inline-Skripte in Templates)
  mit hart-codierten Meldungen (Alerts, Status-Texte).
- Backend-Meldungen (API-Fehler, Degraded-Status, Chatbot-/ILIAS-Services)
  hart-codiert englisch; Chatbot-System-Prompt ist einsprachig.
- Quarto-Reports (`scripts/check_updates.py` u. a.) erzeugen einsprachige
  Berichte; ILIAS-Kurssynchronisation (S8/OP2) versendet einsprachige
  Lernpfad-Titel.
- Zielgruppen: Studierende, Lehrende, Laborpersonal ohne Vorwissen (Init-Prompt
  §3.3) — EU-weiter Hochschulkontext (Hochschule Weihenstephan-Triesdorf,
  ILIAS, EU) macht Mehrsprachigkeit zu einem echten Anforderungsbezug.

## 2. Zielumfang

Unterstützung **aller 24 Amtssprachen der EU**: Bulgarian (bg), Croatian (hr),
Czech (cs), Danish (da), Dutch (nl), English (en), Estonian (et), Finnish (fi),
French (fr), German (de), Greek (el), Hungarian (hu), Irish (ga), Italian (it),
Latvian (lv), Lithuanian (lt), Maltese (mt), Polish (pl), Portuguese (pt),
Romanian (ro), Slovak (sk), Slovenian (sl), Spanish (es), Swedish (sv).

Nicht-Ziele (Anti-Code-Creep): keine Maschinenübersetzung zur Laufzeit, keine
DB-Übersetzungstabellen für Nutzerinhalte in Phase 1, kein Redesign der UI,
keine RTL-Layoutumbauten (Irish ist lateinschriftlich; keine Nicht-EU-Sprachen).

## 3. Phasenplan

### Phase 1 — Infrastruktur (Backend-Gerüst, OP48a)
- `settings.py`: `LOCALE_PATHS`, `LANGUAGES` (24 Sprachen, `LANGUAGE_CODE='de'`
  als Default gemäß Ziellabor), `LocaleMiddleware` in `MIDDLEWARE`,
  `i18n_patterns()` in `nir_web/urls.py` (Präfix-URLs `/en/…`, `/de/…` …;
  Default-Sprache ohne Präfix — rückwärtskompatibel für bestehende
  API-Clients und Bookmarks).
- Basiskommando `django-admin compilemessages` in CI-Matrix; Po-Dateien
  unter `django_project/locale/<lang>/LC_MESSAGES/django.po`.
- Django-CLI: `python manage.py makemessages` als Skript
  (`scripts/i18n_makemessages.sh`), dokumentiert im QUICKSTART.

### Phase 2 — UI-Templates (OP48b, mit UI/UX-Expert)
- Alle 26 Templates systematisch auf `{% load i18n %}` + `{% trans %}` /
  `{% blocktrans %}` umstellen; Navigation um Sprachumschalter erweitern
  (Session + Cookie `django_language`, `set_language`-View).
- Reihenfolge nach Nutzerrelevanz: base/dashboard → analysis → files →
  chatbot → ilias → federated → Rest.
- Nur kennzeichnen, nicht neu formulieren: bestehende Texte 1:1 als
  msgids (keine inhaltlichen Änderungen ohne Anforderungsbezug).

### Phase 3 — Frontend-JS (OP48c)
- JS-Strings über `djangojs`-Katalog (` {% trans %}`-Äquivalent:
  `JSONCatalog`-View `/js-i18n/` + kleine `i18n.js`-Helper
  `gettext(msgid)`); keine neue JS-Abhängigkeit (kein i18next o. Ä.).
- Alternativ-Entscheidung (Tester Agent): Inline-JS in Templates gehört
  zu den msgids der Templates (Phase 2), eigenständige `.js`-Dateien
  an den JSON-Katalog — kleinste korrekte Lösung.

### Phase 4 — Backend-Meldungen & Chatbot (OP48d)
- API-Fehler-/Statusmeldungen der Views (`chatbot_views`, `ilias_views`,
  `federated_views`, `crewai_views`, `file_views`) auf `gettext()`/`gettext_lazy()`
  umstellen; JSON-Keys bleiben unverändert (API-Vertrag stabil).
- Chatbot: `ChatbotService`-System-Prompt lokalisiert (Antwortsprache =
  Anfragesprache bzw. `Accept-Language`); Antworten von Mistral folgen
  der Prompt-Sprache — kein separates Übersetzungsmodell.
- Quarto-Reports: Berichtssprache pro Aufruf konfigurierbar (Default de);
  nicht übersetzbare wissenschaftliche Fachterme verbleiben.

### Phase 5 — Übersetzungscontent (OP48e)
- Quelle: msgids = bestehende englische/deutsche UI-Texte.
- Pilotübersetzungen **de + en** vollständig (beide Sprachen sind im Repo
  bereits real vorhanden → kein Aufwand-Risiko).
- Restliche 22 EU-Sprachen: msgids werden als Katalog bereitgestellt;
  Übersetzungen erfolgen durch native Speaker/Fachlehrkräfte (Hochschule)
  bzw. ggf. OP4-Update-Monitor-Analogie: ein CI-Check meldet fehlende
  (leere) Kataloge ehrlich als `untranslated` — keine Fake-Übersetzungen
  (OP14/OP18-Regel: nichts simulieren).
- ILIAS (S8/OP2/FL6): Lernpfad-/Modultitel mehrsprachig im Payload
  (ILIAS unterstützt mehrsprachige Kurse); Synchronisation nimmt die
  aktive Sprache des initiierenden Nutzers.

### Phase 6 — Tests & CI (OP48f, Tester Agent)
- Neue Testmatrix `tests/test_op48_i18n.py`:
  1. Settings-Vertrag (LOCALE_PATHS, LANGUAGES=24, Middleware, i18n_patterns).
  2. set_language-View + Cookie-Propagation.
  3. Stichproben-Render je Template in de/en (echte Template-Engine,
     OP3/OP8-Muster) mit Übersetzungs-Anwesenheitsprüfung.
  4. API-Meldungen je Sprache (Statuscodes unverändert).
  5. JS-JSON-Katalog-Route.
  6. compilemessages läuft für alle vorhandenen .po-Dateien.
- CI: `compilemessages` + neue Matrix in `.github/workflows/ci.yml`
  aufnehmen; Vollregression S3–S9, OP1–OP47 muss grün bleiben.
- `manage.py check` ohne Befunde; `makemessages --no-obsolete` als
  Drift-Wächter (verhindert verwaiste msgids).

## 4. Agentenzuordnung (Development Agent Framework)

| Agent | Rolle in OP48 |
|---|---|
| Head of Development | Freigabe, Umfangs-Deckelung, Roadmap-Update, Konfliktlösung |
| Django Agent | Phase 1, 2, 4 (Settings, URLs, Templates, Views) |
| UI/UX Expert | Sprachumschalter, Nutzerführung, Zielgruppe ohne Vorwissen |
| Tester Agent | Akzeptanzkriterien vorab, Testmatrix Phase 6, Regressionen |
| Quarto Agent | lokalisierte Berichte (Phase 4) |
| ILIAS Agent | mehrsprachige Kurs-Sync (Phase 5) |
| MCP Agent | `Accept-Language`-Propagation an externe Tools (nur falls Anforderungsbezug) |
| Spektroskopie-Experte | Sicherstellung, dass Fachterminologie (Wellenlänge, Brix, Kalibration) in Übersetzungen erhalten bleibt |

## 5. Abhängigkeiten & Risiken

- Keine neuen Python-/JS-Paketabhängigkeiten — Django-i18n ist Bestandteil
  des Frameworks (Anti-Code-Creep erfüllt).
- Risiko URL-Verträge: API-Routen bewusst **nicht** spra­chpräfixiert
  (`i18n_patterns` nur für UI-Seiten) — bestehende Clients (OP7-Bridge,
  Background-Crew, Ansible-Healthchecks) bleiben unberührt.
- Risiko Übersetzungsqualität: nur de/en sofort „vollständig“; andere
  Sprachen ehrlich als incomplete gemeldet (keine Scheinvollständigkeit).
- Aufwandsschwerpunkt Phase 2 (26 Templates); inkrementell je Template
  committen, damit Review klein bleibt.

## 6. Selbstprüfung gemäß Init-Prompt §7 (schriftlich)

1. **Steuerdateien gelesen?** Ja — AGENTS.md, Init-Prompt, Mission Statement,
   TASK.md, task_definition.yaml, system_manifest.json, Roadmap.
2. **Anforderung in einem Satz:** Die Plattform-UI, Backend-Meldungen,
   Berichte und ILIAS-Sync sollen für alle 24 EU-Amtssprachen
   lokalisiertierbar sein (aktiv: de/en vollständig).
3. **Nicht-Ziele:** Laufzeit-Übersetzung, Redesign, Nicht-EU-Sprachen,
   DB-Übersetzung nutzergenerierter Inhalte in Phase 1.
4. **Betroffene Master Objectives:** MO 10 (Chatbot), MO 13
   (Dokumentation) — indirekt alle UI-zugänglichen Objectives.
5. **Roadmap-Bezug:** Nicht in S1–S9 → Freigabe + Roadmap-Erweiterung
   um OP48 erforderlich (dieser Plan).
6. **Kleinste Lösung:** Django-Bordmittel, keine neuen Abhängigkeiten,
   Templates 1:1-Kennzeichnung ohne inhaltliche Änderung.
7. **Befreit?** Nein — dieser Plan ist der Freigabe-Antrag; Implementierung
   beginnt erst nach Head-of-Development-Zustimmung und Roadmap-Update
   (OP48-Eintrag + TASK.md-Umschreibung).

## 7. Erfolgs-/Abnahmekriterien

- UI in de und en vollständig umschaltbar (Sprachumschalter, Cookie-Persistenz).
- 24 Sprachkataloge angelegt; fehlende Übersetzungen ehrlich als
  `untranslated` erkannt (CI), de/en ohne Lücken.
- API-Statuscodes und JSON-Keys identisch zu vorher (Vertragsstabilität).
- `tests/test_op48_i18n.py` grün; Vollregression S3–S9, OP1–OP47 grün.
- `manage.py check` und `compilemessages` ohne Befunde.
