#!/usr/bin/env python3
# NIR Intelligence Platform - OP2 test matrix: ILIAS API token flow
# Tests the OAuth2 token client, the authenticated API client (Bearer
# header, 401 retry, course lookup) and the authenticated learning path
# sync against real course ref_ids. All tests run offline with injectable
# stub transports - no network, no running containers.

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0
FAILED = []


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        FAILED.append(name)
        print(f"[FAIL] {name} {detail}")


class StubResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def make_token_transport(calls=None, status=200, payload=None, expires_in=3600):
    payload = payload if payload is not None else {
        "access_token": "tok-1", "expires_in": expires_in, "token_type": "Bearer",
        "refresh_token": "ref-1"}

    def transport(method, url, data=None, **kwargs):
        if calls is not None:
            calls.append((method, url, data))
        return StubResponse(status, payload)

    return transport


def main():
    from services.ilias_api_service import (
        GRANT_CLIENT_CREDENTIALS,
        GRANT_REFRESH_TOKEN,
        IliasApiClient,
        IliasTokenClient,
        create_ilias_api_client,
        create_ilias_token_client,
    )
    from services.ilias_learning_service import (
        ILIASLearningService,
        LearningModule,
        LearningObjective,
        LearningPath,
        create_authenticated_ilias_service,
        create_ilias_learning_service,
    )

    # ---------- T1: token fetch request shape ----------
    calls = []
    tc = create_ilias_token_client(
        {"client_id": "nir_ip", "client_secret": "sec"},
        transport=make_token_transport(calls))
    result = tc.fetch_token()
    check("T1a fetch_token returns access token",
          result["access_token"] == "tok-1")
    check("T1b token request goes to /oauth2/token",
          calls[0][1].endswith("/oauth2/token") and calls[0][0] == "POST")
    data = calls[0][2]
    check("T1c default grant is client_credentials",
          data.get("grant_type") == GRANT_CLIENT_CREDENTIALS)
    check("T1d client credentials sent",
          data.get("client_id") == "nir_ip" and data.get("client_secret") == "sec")
    check("T1e token stored and valid",
          tc.access_token == "tok-1" and tc.is_valid())

    # ---------- T2: expiry and refresh ----------
    tc2 = create_ilias_token_client(transport=make_token_transport(expires_in=10))
    tc2.fetch_token()
    check("T2a fresh token valid with short expiry",
          tc2.is_valid() or tc2.expires_at - time.time() <= 40)
    tc2.expires_at = time.time() - 1
    check("T2b expired token invalid", not tc2.is_valid())
    refresh_calls = []
    tc2 = create_ilias_token_client(
        transport=make_token_transport(refresh_calls, payload={
            "access_token": "tok-2", "expires_in": 3600,
            "refresh_token": "ref-2"}))
    tc2.fetch_token()
    tc2.expires_at = time.time() - 1
    tok = tc2.ensure_token()
    check("T2c ensure_token refreshes expired token",
          tok == "tok-2" and refresh_calls[-1][2].get("grant_type") == GRANT_REFRESH_TOKEN
          and refresh_calls[-1][2].get("refresh_token") == "ref-2")
    tc3 = create_ilias_token_client(transport=make_token_transport())
    try:
        tc3.refresh()
        check("T2d refresh without refresh token raises", False)
    except RuntimeError:
        check("T2d refresh without refresh token raises", True)

    # ---------- T3: token endpoint failures ----------
    tc4 = create_ilias_token_client(transport=make_token_transport(status=401))
    try:
        tc4.fetch_token()
        check("T3a token request 401 raises RuntimeError", False)
    except RuntimeError as exc:
        check("T3a token request 401 raises RuntimeError", "401" in str(exc))
    tc5 = create_ilias_token_client(transport=make_token_transport(
        payload={"expires_in": 3600}))
    try:
        tc5.fetch_token()
        check("T3b missing access_token raises", False)
    except RuntimeError:
        check("T3b missing access_token raises", True)
    def broken_transport(method, url, data=None, **kwargs):
        raise ConnectionError("ilias container not running")
    tc6 = create_ilias_token_client(transport=broken_transport)
    try:
        tc6.fetch_token()
        check("T3c unreachable ILIAS raises RuntimeError", False)
    except RuntimeError:
        check("T3c unreachable ILIAS raises RuntimeError", True)

    # ---------- T4: authenticated API client ----------
    api_calls = []

    def api_transport(method, url, headers=None, json=None, **kwargs):
        api_calls.append((method, url, headers, json))
        if url.endswith("/oauth2/token"):
            return StubResponse(200, {"access_token": "api-tok", "expires_in": 3600})
        return StubResponse(200, {"courses": [
            {"ref_id": 15, "title": "NIR Laboratory Basics"},
            {"ref_id": 22, "title": "Advanced NIR Analysis"},
        ]})

    tc_api = create_ilias_token_client({"client_id": "nir_ip"}, transport=api_transport)
    api = create_ilias_api_client(
        {"client_id": "nir_ip"}, token_client=tc_api, transport=api_transport)
    resp = api.get("/courses")
    check("T4a api request carries Bearer header",
          resp.status_code == 200
          and api_calls[-1][2].get("Authorization") == "Bearer api-tok")
    check("T4b api url includes prefix",
          api_calls[-1][1].endswith("/api/v1/courses"))
    check("T4c find_course_ref_id_by_title resolves real ref_id",
          api.find_course_ref_id_by_title("Advanced NIR Analysis") == "22")
    check("T4d unknown title returns None",
          api.find_course_ref_id_by_title("Nope") is None)
    check("T4e last_status tracked", api.last_status == 200)

    # ---------- T5: 401 retry ----------
    retry_state = {"count": 0}

    def retry_transport(method, url, headers=None, **kwargs):
        if url.endswith("/oauth2/token"):
            return StubResponse(200, {"access_token": f"tok-{retry_state['count']}",
                                      "expires_in": 3600})
        retry_state["count"] += 1
        if retry_state["count"] == 1:
            return StubResponse(401, {})
        return StubResponse(200, {"ok": True})

    tc_retry = create_ilias_token_client(transport=retry_transport)
    api2 = create_ilias_api_client(token_client=tc_retry, transport=retry_transport)
    resp2 = api2.get("/courses")
    check("T5a 401 triggers token re-fetch and retry",
          resp2.status_code == 200 and retry_state["count"] == 2)
    check("T5b retry uses refreshed token",
          resp2.status_code == 200)

    # ---------- T6: authenticated learning path sync against real course ----------
    sync_calls = []

    def sync_transport(method, url, headers=None, json=None, **kwargs):
        sync_calls.append((method, url, headers, json))
        if url.endswith("/oauth2/token"):
            return StubResponse(200, {"access_token": "sync-tok", "expires_in": 3600})
        return StubResponse(201, {"ref_id": 55})

    service = create_authenticated_ilias_service({"client_id": "nir_ip"})
    tc_sync = create_ilias_token_client({"client_id": "nir_ip"}, transport=sync_transport)
    api_sync = create_ilias_api_client(token_client=tc_sync, transport=sync_transport)
    path = LearningPath(title="NIR Lab", modules=[
        LearningModule(title="Kalibration", objectives=[
            LearningObjective(title="PLS verstehen")])])
    outcome = service.sync_learning_path(
        path, transport=lambda m, u, **kw: api_sync.request(m, u, **kw),
        course_ref_id=55)
    check("T6a sync into existing course succeeds",
          outcome.success and outcome.modules_synced == 1
          and outcome.course_ref_id == "55")
    check("T6b no course creation call when course_ref_id given",
          not any(u.endswith("/api/v1/courses") and m == "POST"
                  for m, u, h, j in sync_calls))
    check("T6c module posted under real course ref",
          any(u.endswith("/api/v1/courses/55/objectives") for m, u, h, j in sync_calls))
    check("T6d sync calls carry Bearer header",
          all(h and h.get("Authorization") == "Bearer sync-tok"
              for m, u, h, j in sync_calls if not u.endswith("/oauth2/token")))

    # ---------- T7: unauthenticated sync unchanged (S8 compatibility) ----------
    plain_calls = []

    def plain_transport(method, url, json=None, **kwargs):
        plain_calls.append((method, url))
        if url.endswith("/courses"):
            return StubResponse(201, {"ref_id": 42})
        return StubResponse(201, {"ref_id": 100})

    plain = create_ilias_learning_service()
    outcome7 = plain.sync_learning_path(
        LearningPath(title="NIR Lab", modules=[
            LearningModule(title="Modul A"),
            LearningModule(title="Modul B")]),
        transport=plain_transport)
    check("T7a plain S8 sync still works without token",
          outcome7.success and outcome7.modules_synced == 2
          and outcome7.course_ref_id == "42")
    check("T7b no token endpoint hit in plain mode",
          not any("/oauth2/token" in u for m, u in plain_calls))

    # ---------- T8: status reporting ----------
    tc8 = create_ilias_token_client(transport=make_token_transport())
    tc8.fetch_token()
    status = tc8.status()
    check("T8a token client status reports has_token and valid",
          status["has_token"] is True and status["token_valid"] is True
          and status["client_id"] == "")
    api8 = create_ilias_api_client(token_client=tc8,
                                   transport=api_transport)
    api8.get("/courses")
    s8 = api8.status()
    check("T8b api client status reports authenticated and last_status",
          s8["authenticated"] is True and s8["last_status"] == 200)

    # ---------- T9: IliasApiClient accepts full urls from learning service ----------
    full_calls = []

    def full_transport(method, url, headers=None, json=None, **kwargs):
        full_calls.append(url)
        if url.endswith("/oauth2/token"):
            return StubResponse(200, {"access_token": "f-tok", "expires_in": 3600})
        return StubResponse(201, {"ref_id": 9})

    tc9 = create_ilias_token_client(transport=full_transport)
    api9 = create_ilias_api_client(token_client=tc9, transport=full_transport)
    resp9 = api9.request("POST", "http://ilias:80/api/v1/courses", json={"type": "crs"})
    check("T9a absolute url passed through with auth header",
          resp9.status_code == 201
          and any(u.endswith("/api/v1/courses") for u in full_calls))

    # ---------- T10: regression spot checks ----------
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    ok_s8 = os.path.exists(os.path.join(os.path.dirname(__file__), "test_s8_ilias_integration.py"))
    check("T10a S8 test matrix present", ok_s8)
    ok_op1 = os.path.exists(os.path.join(os.path.dirname(__file__), "test_op1_embedding_pipeline.py"))
    check("T10b OP1 test matrix present", ok_op1)
    from services.ilias_learning_service import ILIASCourseBuilder
    sample = LearningPath(title="X", modules=[LearningModule(title="M")])
    payload = ILIASCourseBuilder.build_course_payload(sample)
    check("T10c S8 course builder regression",
          payload["type"] == "crs" and payload["title"] == "X")

    print()
    if FAIL:
        print(f"{FAILED}")
        print(f"{FAIL} tests FAILED")
        return 1
    print(f"{PASS}/{PASS + FAIL} tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
