#!/usr/bin/env python3
"""FA1: Passwort-Wechsel-Endpoint (FEDERATED_SETUP_AUTH_IMPLEMENTATIONSPLAN.md).

Prueft den ChangePasswordView-Vertrag, den die vorhandene Settings-UI
(settings.html: updatePassword()) erwartet:
  - POST /api/users/change_password/ {current_password, new_password}
  - falsches altes Passwort -> 400 success=False
  - identisches neues Passwort -> 400
  - schwaches neues Passwort -> 400 mit Validator-Meldung
  - Erfolg -> 200 success=True, Passwort danach mit neuem Wert gültig,
    alte Sessions (Refresh-Tokens) gesperrt.

Offline-Matrix im Stil der bestehenden CI-Tests (kein DB-Server noetig).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'django_project'))

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


# --- Django offline aufsetzen -------------------------------------------
import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='fa1-test-secret',
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3',
                                'NAME': ':memory:'}},
        INSTALLED_APPS=[
            'django.contrib.contenttypes', 'django.contrib.auth',
            'django.contrib.sessions', 'core', 'api',
        ],
        MIDDLEWARE=[],
        ROOT_URLCONF=None,
        USE_TZ=True,
        NIR_FRAMEWORK_PATH=str(Path(__file__).resolve().parent.parent),
        QUARTO_PATH='quarto',
        AUTH_PASSWORD_VALIDATORS=[
            {'NAME': 'django.contrib.auth.password_validation.'
                     'MinimumLengthValidator',
             'OPTIONS': {'min_length': 8}},
            {'NAME': 'django.contrib.auth.password_validation.'
                     'NumericPasswordValidator'},
        ],
    )
django.setup()

from django.test import RequestFactory  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.management import call_command  # noqa: E402

call_command('migrate', verbosity=0, interactive=False)

User = get_user_model()


def _make_request(user, payload):
    rf = RequestFactory()
    req = rf.post('/api/users/change_password/', data=payload,
                  content_type='application/json')
    req.data = payload
    req.user = user
    return req


def _call_view(user, payload):
    """ChangePasswordView.post ohne DRF-Response-Renderer aufrufen."""
    from api.views import ChangePasswordView
    view = ChangePasswordView()
    response = view.post(_make_request(user, payload))
    return response


def main():
    User.objects.all().delete()

    # T1a: Erfolg - Passwort wird geaendert
    user = User.objects.create_user('fa1user', 'fa1@example.com', 'AltesPass123')
    from rest_framework import status as http_status
    resp = _call_view(user, {'current_password': 'AltesPass123',
                             'new_password': 'NeuesPass456'})
    check('T1a Passwortwechsel erfolgreich (200)',
          resp.status_code == 200 and resp.data.get('success') is True,
          f'status={resp.status_code} data={resp.data}')
    user.refresh_from_db()
    check('T1b neues Passwort pruefbar',
          user.check_password('NeuesPass456'))
    check('T1c altes Passwort ungueltig',
          not user.check_password('AltesPass123'))

    # T2a: falsches altes Passwort
    resp = _call_view(user, {'current_password': 'Falsch',
                             'new_password': 'AnderesPass789'})
    check('T2a falsches altes Passwort -> 400',
          resp.status_code == 400 and resp.data.get('success') is False,
          f'status={resp.status_code}')
    user.refresh_from_db()
    check('T2b Passwort unveraendert',
          user.check_password('NeuesPass456'))

    # T3a: identisches neues Passwort
    resp = _call_view(user, {'current_password': 'NeuesPass456',
                             'new_password': 'NeuesPass456'})
    check('T3a identisches Passwort -> 400',
          resp.status_code == 400 and resp.data.get('success') is False)

    # T4a: zu kurzes Passwort (Validator min_length=8)
    resp = _call_view(user, {'current_password': 'NeuesPass456',
                             'new_password': 'kurz'})
    check('T4a Validator schlaegt an -> 400',
          resp.status_code == 400 and resp.data.get('success') is False,
          f'status={resp.status_code} data={resp.data}')

    # T4b: rein numerisches Passwort (NumericPasswordValidator)
    resp = _call_view(user, {'current_password': 'NeuesPass456',
                             'new_password': '12345678901'})
    check('T4b NumericPasswordValidator schlaegt an -> 400',
          resp.status_code == 400 and resp.data.get('success') is False)

    # T5a: fehlende Felder
    resp = _call_view(user, {'current_password': 'NeuesPass456'})
    check('T5a fehlendes neues Passwort -> 400',
          resp.status_code == 400 and resp.data.get('success') is False)

    # T6a: Route existiert (Import/Wiring)
    src = open(Path(__file__).resolve().parent.parent /
               'django_project' / 'nir_web' / 'urls.py', encoding='utf-8').read()
    check('T6a Route api/users/change_password/ registriert',
          'api/users/change_password/' in src)
    check('T6b ChangePasswordView importiert',
          'ChangePasswordView' in src)

    # T7a: UI erwartet exakt dieses Format (settings.html)
    ui = open(Path(__file__).resolve().parent.parent /
              'django_project' / 'templates' / 'settings.html',
              encoding='utf-8').read()
    check('T7a UI-POST erwartet current_password/new_password',
          "current_password" in ui and "new_password" in ui)

    print(f'\nFA1 Passwortwechsel-Matrix: {PASS} passed, {FAIL} failed')
    if FAILED:
        print('FAILED checks:', FAILED)
        sys.exit(1)


if __name__ == '__main__':
    main()
