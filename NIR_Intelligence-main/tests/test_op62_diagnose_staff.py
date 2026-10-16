#!/usr/bin/env python3
# OP62 test matrix: Diagnose section bound to staff (admin) accounts.
# Offline-safe: no network access required.
import os
import sys
from pathlib import Path

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


try:
    import django
    django.setup()
    check("T0a django setup", True)
except Exception as exc:
    check("T0a django setup", False, str(exc))
    sys.exit(1)

from django.conf import settings as dj_settings  # noqa: E402

if "testserver" not in dj_settings.ALLOWED_HOSTS:
    dj_settings.ALLOWED_HOSTS = [*dj_settings.ALLOWED_HOSTS, "testserver"]
dj_settings.DATABASES["default"]["NAME"] = ":memory:"
dj_settings.DATABASES["default"].setdefault("ATOMIC_REQUESTS", False)

from django.core.management import call_command  # noqa: E402

from django.contrib.auth import get_user_model  # noqa: E402
from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402

User = get_user_model()
call_command("migrate", interactive=False, verbosity=0)

REPO_ROOT = Path(__file__).resolve().parent.parent
TPL = REPO_ROOT / "django_project" / "templates"

# ---------------------------------------------------------------------------
# T1: base.html — settings link removed from the Diagnose submenu (redundant
#     to the user dropdown), Diagnose tab stays staff-only
# ---------------------------------------------------------------------------
tpl_src = (TPL / "base.html").read_text(encoding="utf-8")
try:
    nav = tpl_src[tpl_src.index('c-nav-main__list'):tpl_src.index('</nav>')]
    diagnose = nav[nav.index('Diagnose'):]
    check("T1a nav block extractable", True)
except ValueError as exc:
    diagnose = ""
    check("T1a nav block extractable", False, str(exc))

check("T1b Diagnose tab is staff-gated",
      '{% if user.is_staff %}' in tpl_src and 'Diagnose' in tpl_src)
check("T1c no /settings/ link inside the Diagnose submenu",
      'href="/settings/"' not in diagnose,
      "settings link still present in Diagnose submenu")
dropdown_src = tpl_src[tpl_src.index('id="userDropdown"'):
tpl_src.index('</ul>', tpl_src.index('id="userDropdown"'))]
check("T1d settings stays reachable via user dropdown for all users",
      'href="/settings/"' in dropdown_src)
check("T1e Diagnose submenu still links jobs/agents/analysis",
      all(h in diagnose for h in ('href="/jobs/"', 'href="/agents/"',
                                  'href="/analysis/"')))

# ---------------------------------------------------------------------------
# T2: URL wiring — jobs/agents/analysis routes require staff in BOTH the
#     default (de) and the i18n-prefixed patterns
# ---------------------------------------------------------------------------
urls_src = (REPO_ROOT / "django_project" / "nir_web" / "urls.py").read_text(encoding="utf-8")
for route in ("jobs", "agents", "analysis"):
    count = urls_src.count(
        f"path('{route}/', user_passes_test(lambda u: u.is_staff")
    check(f"T2a /{route}/ staff-guarded in urls.py (de + i18n, 2x)", count == 2,
          f"found {count}")

# ---------------------------------------------------------------------------
# T3: Runtime behaviour — anonymous/non-staff get redirected to login,
#     staff gets 200
# ---------------------------------------------------------------------------
client = Client()

staff = User.objects.filter(is_staff=True).first()
if staff is None:
    staff = User.objects.create_user("op62staff", password="pw",
                                     is_staff=True, email="op62@example.com")
nonstaff = User.objects.filter(is_staff=False, username="op62user").first()
if nonstaff is None:
    nonstaff = User.objects.create_user("op62user", password="pw",
                                       email="op62u@example.com")

for name in ("jobs-page", "agents-page", "analysis-page"):
    url = reverse(name)
    r = client.get(url)
    check(f"T3a anonymous /{name}/ redirected", r.status_code in (301, 302),
          f"status {r.status_code}")
    client.force_login(nonstaff)
    r = client.get(url)
    check(f"T3b non-staff /{name}/ redirected", r.status_code in (301, 302),
          f"status {r.status_code}")
    client.force_login(staff)
    r = client.get(url)
    check(f"T3c staff /{name}/ returns 200", r.status_code == 200,
          f"status {r.status_code}")
    client.logout()

# settings must stay usable for every authenticated user (no new restriction)
settings_url = reverse("settings-page")
client.force_login(nonstaff)
r = client.get(settings_url)
check("T3d non-staff /settings/ still 200 (user feature)", r.status_code == 200,
      f"status {r.status_code}")
client.logout()

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
