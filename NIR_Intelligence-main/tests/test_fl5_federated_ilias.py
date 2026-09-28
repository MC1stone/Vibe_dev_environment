#!/usr/bin/env python3
# NIR Intelligence Platform - FL5 test matrix: federated ILIAS coordination
# Verifies that federated group sessions become ILIAS course contexts, that
# per-round status syncs metadata-only (privacy contract enforced in code),
# that existing courses are reused instead of duplicated, and that every
# ILIAS failure degrades honestly (OP2 transport-injection pattern; no
# network, no running containers).

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0
FAILED = []

PROJECT = os.path.join(os.path.dirname(__file__), "..")


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        FAILED.append(name)
        print(f"[FAIL] {name} {detail}")


from services.federated_ilias_service import (
    FederatedGroupSession,
    FederatedIliasService,
    SyncOutcome,
)
from services.ilias_api_service import IliasApiClient, IliasTokenClient


class StubResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body or {}

    def json(self):
        return self._body


class RecordingTransport:
    """Injectable transport (OP2 pattern): records calls, replays responses."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, headers=None, **kwargs):
        self.calls.append({"method": method, "url": url, "headers": headers,
                           "kwargs": kwargs})
        if self.responses:
            return self.responses.pop(0)
        return StubResponse(404)


def make_service(responses):
    transport = RecordingTransport(responses)
    config = {"ilias_url": "http://ilias:80", "client_id": "nir",
              "client_secret": "s", "grant_type": "client_credentials"}
    token_client = IliasTokenClient(config=config,
                                    transport=lambda m, u, **k: StubResponse(
                                        200, {"access_token": "tok",
                                              "expires_in": 3600,
                                              "token_type": "Bearer"}))
    client = IliasApiClient(config=config, token_client=token_client,
                            transport=transport)
    service = FederatedIliasService(config=config, client=client)
    return service, transport


# T1: session model
session = FederatedGroupSession(session_id="fed-1", title="Föderierte Session SS26",
                                group_names=["Gruppe A", "Gruppe B"],
                                strategy="fedavg")
desc = session.to_ilias_description()
check("T1a ILIAS description names groups, strategy and privacy rule",
      "Gruppe A" in desc and "fedavg" in desc and "Rohspektren bleiben lokal" in desc)

# T2: create-session context reuses an existing ILIAS course
service, transport = make_service([
    StubResponse(200, [{"ref_id": "77", "title": "Föderierte Session SS26"},
                        {"ref_id": "78", "title": "Kurs Other"}]),
])
# find_course_ref_id_by_title expects a course list body
transport.responses[0] = StubResponse(200, [
    {"ref_id": "77", "title": "Föderierte Session SS26"}])
outcome = service.create_session_context(session)
check("T2a existing course reused (no duplicate creation)",
      outcome.success and outcome.course_ref_id == "77"
      and "bereits vorhanden" in outcome.message)
check("T2b no POST issued when the course exists",
      all(c["method"] == "GET" for c in transport.calls))

# T3: create-session context creates a new course when none exists
session2 = FederatedGroupSession(session_id="fed-2", title="Neue Session",
                                 group_names=["Gruppe C"], strategy="fedprox")
service2, transport2 = make_service([
    StubResponse(200, []),
    StubResponse(201, {"ref_id": "123"}),
])
outcome2 = service2.create_session_context(session2)
check("T3a new course context created (201)",
      outcome2.success and outcome2.course_ref_id == "123")
check("T3b session status flips to synced",
      session2.status == "synced")
posted = [c for c in transport2.calls if c["method"] == "POST"]
check("T3c course POST carries metadata-only description",
      len(posted) == 1 and "Rohspektren" in posted[0]["kwargs"]["json"]["description"])

# T4: round status sync - privacy contract enforced in code
session2.rounds_completed = 3
service3, transport3 = make_service([
    StubResponse(200, [{"ref_id": "123", "title": "Neue Session"}]),
    StubResponse(201, {}),
])
outcome3 = service3.sync_round_status(
    session2, {"rmse": 0.42, "total_examples": 120})
check("T4a round status syncs to the session course context",
      outcome3.success and outcome3.course_ref_id == "123"
      and outcome3.detail.get("round") == 3)
posted_round = [c for c in transport3.calls if c["method"] == "POST"][-1]
check("T4b round payload carries aggregate metadata only",
      posted_round["kwargs"]["json"]["summary"] == {"rmse": 0.42,
                                                    "total_examples": 120}
      and posted_round["kwargs"]["json"]["groups"] == ["Gruppe C"])

try:
    service3.sync_round_status(session2, {"params": [0.1, 0.2]})
    check("T4c raw parameter payload rejected (privacy contract)", False)
except ValueError:
    check("T4c raw parameter payload rejected (privacy contract)", True)
try:
    service3.sync_round_status(session2, {"spectra": [[1, 2]]})
    check("T4d raw spectra payload rejected (privacy contract)", False)
except ValueError:
    check("T4d raw spectra payload rejected (privacy contract)", True)

# T5: honest degradation when ILIAS is unreachable
service4, transport4 = make_service([])
transport4.responses = None


def broken_transport(method, url, **kwargs):
    raise ConnectionError("ILIAS container not running")


service4.client._transport = broken_transport
outcome5 = service4.create_session_context(session2)
check("T5a unreachable ILIAS degrades honestly on context creation",
      not outcome5.success and "nicht erreichbar" in outcome5.message)
outcome6 = service4.sync_round_status(session2, {"rmse": 0.5})
check("T5b unreachable ILIAS degrades honestly on round sync",
      not outcome6.success and "nicht erreichbar" in outcome6.message)

# T6: ILIAS API rejection surfaces the HTTP status honestly
service7, transport7 = make_service([
    StubResponse(200, []),
    StubResponse(403, {"error": "forbidden"}),
])
outcome7 = service7.create_session_context(session2)
check("T6a API rejection reported with HTTP status",
      not outcome7.success and "403" in outcome7.message)

# T7: status surface
status = service4.status()
check("T7a status names the service and the privacy contract",
      status["service"] == "federated_ilias"
      and "no spectra" in status["privacy_contract"])
check("T7b status reports token state honestly",
      isinstance(status["token"], dict))

# T8: integration - OP2 client is the transport basis (no parallel client)
src = open(os.path.join(PROJECT, "services", "federated_ilias_service.py"),
           encoding="utf-8").read()
check("T8a builds on the OP2 IliasApiClient/IliasTokenClient",
      "IliasApiClient" in src and "IliasTokenClient" in src)

print(f"\n{PASS}/{PASS + FAIL} checks passed")
if FAILED:
    print("FAILED:", FAILED)
    sys.exit(1)
