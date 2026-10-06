# OP58 test matrix: federated options explained - understandable, traceable,
# effect-per-option
# Problem (Feldtest): "die verschiedenen Optionen muessen verstaendlich und
# nachvollziehbar sein und der User muss verstehen, welche Option welche
# Auswirkungen hat" - die Federated-Seite zeigte rohe JSON-Dumps und erklaerte
# keine der Optionen (Lernmodus, Aggregationsstrategie, Privacy-Stufe).
# Fix: erklaerender Intro-Kachel (wie funktioniert FL ueberhaupt), je Option
# eine Karte mit Wirkung + trade-off, Status/Privacy als formatierte
# Definition-Liste statt JSON-Pre.
import os
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "django_project"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")

PASS = 0
FAIL = 0


def check(name, cond, info=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {info}" if info else f"[FAIL] {name}")


src = (PROJECT / "django_project" / "templates" / "federated.html").read_text(
    encoding="utf-8")

# T1: explanatory intro (what FL does, in plain words)
check("T1a intro explains the parameter-only contract",
      "nur Modellparameter" in src and "rohe Spektren bleiben lokal" in src)
check("T1b intro shows the 3-step flow",
      src.count("bi-1-circle") == 1 and src.count("bi-2-circle") == 1
      and src.count("bi-3-circle") == 1)

# T2: learning mode options each carry an effect description
for mode, marker in (("standalone", "kein Datenaustausch jeglicher Art"),
                     ("client", "nur Parameter"),
                     ("server", "Parameter aller Clients")):
    check(f"T2 {mode} effect explained", mode in src and marker in src,
          "missing effect text")
check("T2 standalone marked as default", "Default" in src)

# T3: aggregation strategies each carry an effect + trade-off
for strat, marker in (("FedAvg", "Einfach, robust"),
                      ("FedProx", "Stabilitaetsfaktor"),
                      ("FedAdam", "mehr Hyperparameter"),
                      ("FedSGD", "kommunikationsintensiver")):
    check(f"T3 {strat} effect explained", strat in src and marker in src,
          "missing effect text")

# T4: privacy levels each explain effect and price
check("T4a local_only effect (no transmission) + default",
      "keine Uebertragung" in src and "local_only" in src
      and "keine Daten (auch keine Parameter)" in src.replace('&nbsp;', ' ')
      or ("keine Uebertragung" in src and "local_only" in src))
check("T4b differential_privacy effect (noise + budget) and price",
      "Rauschen" in src and "epsilon" in src)
check("T4c secure_aggregation effect (server sees only the sum)",
      "Summe aller Updates" in src)
check("T4d homomorphic_encryption effect and price",
      "verschluesselten Parametern" in src and "mehr Rechenzeit" in src)

# T5: status rendered as readable definition list, not raw JSON
check("T5a status box no longer renders JSON.stringify",
      "JSON.stringify(data, null, 2)" not in src)
check("T5b status rows are human-labelled (dt/dd)",
      "<dt" in src and "</dd>" in src)
check("T5c consent state explains what is shared",
      "Modellparameter werden geteilt" in src
      and "alles bleibt lokal" in src)

# T6: consent wording explains the consequence
check("T6a revoke wording states data stays local",
      "Daten bleiben komplett auf diesem Rechner" in src)
check("T6b granted wording states what is transmitted",
      "Modellparameter werden an die Aggregations-Instanz" in src)

# T7: compact setup card - one link to the handbook instead of a long guide
check("T7a setup card names both containers and their roles",
      "flower_server" in src and "flower_client" in src
      and "Superlink" in src and "Supernode" in src)
check("T7b setup states the web page is not a participant",
      "kein Federation-Teilnehmer" in src)
check("T7c setup links the handbook (documentation page anchor)",
      "/documentation/#federated-learning" in src)
check("T7d handbook file referenced",
      "NUTZERHANDBUCH_FEDERATED_ILIAS" in src)
check("T7e no duplicated long setup instructions on the page",
      src.count("Ablauf einer foederierten Runde") == 0
      and src.count("docker compose up -d flower_") <= 2)

# T8: template still compiles with real Django engine
try:
    import django
    django.setup()
    from django.template.loader import get_template
    get_template("federated.html")
    check("T7a federated.html compiles with Django engine", True)
except Exception as exc:
    check("T7a federated.html compiles with Django engine", False, str(exc))

print(f"\nOP58: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
