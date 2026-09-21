#!/usr/bin/env python3
# NIR Intelligence Platform - ILIAS API token service (roadmap OP2)
# Real OAuth2 token flow plus authenticated REST transport against the
# ILIAS container (docker-compose service 'ilias', srsolutions/ilias image).
# The HTTP transport is injectable; the service performs no network calls
# at import time and degrades gracefully when ILIAS is unreachable.

import logging
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("Service.ILIASApi")

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

ILIAS_DEFAULT_URL = "http://ilias:80"
DEFAULT_TOKEN_PATH = "/oauth2/token"
DEFAULT_API_PREFIX = "/api/v1"

GRANT_AUTHORIZATION_CODE = "authorization_code"
GRANT_CLIENT_CREDENTIALS = "client_credentials"
GRANT_REFRESH_TOKEN = "refresh_token"


class IliasTokenClient:
    """OAuth2 token acquisition for the ILIAS REST API.

    Fetches access tokens via POST {ilias_url}{token_path} with a
    configurable grant type, tracks expiry and refreshes tokens.
    The transport is injectable for offline tests.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None,
                 transport: Optional[Callable[..., Any]] = None):
        config = config or {}
        self.ilias_url = config.get("ilias_url", ILIAS_DEFAULT_URL).rstrip("/")
        self.token_path = config.get("token_path", DEFAULT_TOKEN_PATH)
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.default_grant = config.get("grant_type", GRANT_CLIENT_CREDENTIALS)
        self._transport = transport or self._default_transport
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.expires_at: float = 0.0
        self.token_type: str = "Bearer"

    def _default_transport(self, method: str, url: str, **kwargs):
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("requests package not available")
        return requests.request(method, url, timeout=30, **kwargs)

    def fetch_token(self, grant_type: Optional[str] = None,
                    code: Optional[str] = None,
                    refresh_token: Optional[str] = None,
                    redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Fetch a new access token from the ILIAS OAuth2 endpoint.

        Returns {"access_token", "expires_in", "token_type", "refresh_token"}.
        Raises RuntimeError on transport or protocol errors.
        """
        grant = grant_type or self.default_grant
        payload: Dict[str, Any] = {
            "grant_type": grant,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if code is not None:
            payload["code"] = code
        if redirect_uri is not None:
            payload["redirect_uri"] = redirect_uri
        if refresh_token is not None:
            payload["refresh_token"] = refresh_token

        url = f"{self.ilias_url}{self.token_path}"
        try:
            response = self._transport("POST", url, data=payload)
        except Exception as exc:
            raise RuntimeError(f"ILIAS token endpoint unreachable: {exc}") from exc
        status = getattr(response, "status_code", 0)
        if status not in (200, 201):
            raise RuntimeError(
                f"ILIAS token request failed (status {status})")
        body = response.json()
        access_token = body.get("access_token")
        if not access_token:
            raise RuntimeError("ILIAS token response has no access_token")
        self.access_token = access_token
        self.token_type = body.get("token_type", "Bearer")
        self.refresh_token = body.get("refresh_token", self.refresh_token)
        expires_in = body.get("expires_in", 3600)
        self.expires_at = time.time() + float(expires_in)
        logger.info("ILIAS access token acquired (expires in %ss)", expires_in)
        return {
            "access_token": self.access_token,
            "expires_in": expires_in,
            "token_type": self.token_type,
            "refresh_token": self.refresh_token,
        }

    def refresh(self) -> Dict[str, Any]:
        """Refresh the access token via the refresh_token grant."""
        if not self.refresh_token:
            raise RuntimeError("no refresh token available")
        return self.fetch_token(grant_type=GRANT_REFRESH_TOKEN,
                                refresh_token=self.refresh_token)

    def is_valid(self) -> bool:
        """True when a token is present and not (nearly) expired."""
        if not self.access_token:
            return False
        return time.time() < self.expires_at - 30

    def ensure_token(self) -> str:
        """Return a valid access token, refreshing when possible."""
        if self.is_valid():
            return self.access_token
        if self.refresh_token:
            self.refresh()
            return self.access_token
        self.fetch_token()
        return self.access_token

    def status(self) -> Dict[str, Any]:
        return {
            "service": "ilias_api_token",
            "ilias_url": self.ilias_url,
            "token_path": self.token_path,
            "client_id": self.client_id,
            "grant_type": self.default_grant,
            "has_token": self.access_token is not None,
            "token_valid": self.is_valid(),
            "has_refresh_token": self.refresh_token is not None,
        }


class IliasApiClient:
    """Authenticated REST client for the ILIAS API (Bearer token).

    Wraps an injectable transport, injects the Authorization header,
    retries once with a token refresh on 401 responses.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None,
                 token_client: Optional[IliasTokenClient] = None,
                 transport: Optional[Callable[..., Any]] = None):
        config = config or {}
        self.ilias_url = config.get("ilias_url", ILIAS_DEFAULT_URL).rstrip("/")
        self.api_prefix = config.get("api_prefix", DEFAULT_API_PREFIX)
        self.token_client = token_client or IliasTokenClient(config=config)
        self._transport = transport or self._default_transport
        self.last_status: Optional[int] = None

    def _default_transport(self, method: str, url: str, **kwargs):
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("requests package not available")
        return requests.request(method, url, timeout=30, **kwargs)

    def request(self, method: str, path: str, **kwargs) -> Any:
        """Authenticated request against {ilias_url}{api_prefix}{path}."""
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            if not path.startswith("/"):
                path = "/" + path
            url = f"{self.ilias_url}{self.api_prefix}{path}"
        token = self.token_client.ensure_token()
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["Authorization"] = f"{self.token_client.token_type} {token}"
        response = self._transport(method, url, headers=headers, **kwargs)
        self.last_status = getattr(response, "status_code", None)
        if self.last_status == 401:
            logger.warning("ILIAS API returned 401, refreshing token and retrying")
            token = self.token_client.ensure_token()
            headers["Authorization"] = f"{self.token_client.token_type} {token}"
            response = self._transport(method, url, headers=headers, **kwargs)
            self.last_status = getattr(response, "status_code", None)
        return response

    def get(self, path: str, **kwargs) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> Any:
        return self.request("POST", path, **kwargs)

    def list_courses(self) -> Any:
        return self.get("/courses")

    def get_course(self, course_ref_id: Any) -> Any:
        return self.get(f"/courses/{course_ref_id}")

    def find_course_ref_id_by_title(self, title: str) -> Optional[str]:
        """Look up a real course ref_id by title; None when not found."""
        response = self.list_courses()
        if getattr(response, "status_code", 0) != 200:
            return None
        body = response.json()
        courses = body.get("courses", body) if isinstance(body, dict) else body
        if not isinstance(courses, list):
            return None
        for course in courses:
            if not isinstance(course, dict):
                continue
            if course.get("title") == title:
                ref_id = course.get("ref_id")
                return str(ref_id) if ref_id is not None else None
        return None

    def status(self) -> Dict[str, Any]:
        return {
            "service": "ilias_api_client",
            "ilias_url": self.ilias_url,
            "api_prefix": self.api_prefix,
            "authenticated": self.token_client.is_valid(),
            "last_status": self.last_status,
        }


def create_ilias_token_client(config: Optional[Dict[str, Any]] = None,
                              transport: Optional[Callable[..., Any]] = None) -> IliasTokenClient:
    return IliasTokenClient(config=config, transport=transport)


def create_ilias_api_client(config: Optional[Dict[str, Any]] = None,
                            token_client: Optional[IliasTokenClient] = None,
                            transport: Optional[Callable[..., Any]] = None) -> IliasApiClient:
    return IliasApiClient(config=config, token_client=token_client,
                           transport=transport)


def check() -> bool:
    """Offline smoke check of the module (no network)."""
    token_client = create_ilias_token_client({"client_id": "check"}, transport=_smoke_token_transport)
    token_client.fetch_token()
    client = create_ilias_api_client(token_client=token_client,
                                     transport=_smoke_api_transport)
    ok = client.get("/courses").status_code == 200
    print(f"[{'PASS' if ok else 'FAIL'}] ilias_api_service check")
    return ok


def _smoke_token_transport(method, url, data=None, **kwargs):
    class _R:
        status_code = 200

        def json(self):
            return {"access_token": "smoke-token", "expires_in": 3600}

    return _R()


def _smoke_api_transport(method, url, headers=None, **kwargs):
    class _R:
        status_code = 200

        def json(self):
            return {"courses": []}

    return _R()


if __name__ == "__main__":
    raise SystemExit(0 if check() else 1)
