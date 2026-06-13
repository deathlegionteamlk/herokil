"""
herokil.sessions - Session management using signed cookies.

Provides secure, cookie-based session storage. Session data is
serialized to JSON, base64-encoded, and cryptographically signed
using the app's secret key.
"""

import base64
import hashlib
import hmac
import json
import typing as t
import time


class SessionInterface:
    """Base class for session interfaces.

    A session interface is responsible for loading and saving session
    data between requests.
    """

    def open_session(self, request, app) -> dict:
        """Load session data from the incoming request."""
        raise NotImplementedError

    def save_session(self, response, session, app):
        """Save session data to the outgoing response."""
        raise NotImplementedError


class SecureCookieSession(dict):
    """A session implementation stored in a signed cookie.

    Behaves like a regular dictionary but tracks modifications
    so the session is only re-signed when data changes.
    """

    def __init__(self, data: t.Optional[dict] = None):
        super().__init__(data or {})
        self.modified = False

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.modified = True

    def __delitem__(self, key):
        super().__delitem__(key)
        self.modified = True

    def pop(self, key, *args):
        self.modified = True
        return super().pop(key, *args)

    def update(self, *args, **kwargs):
        self.modified = True
        super().update(*args, **kwargs)

    def clear(self):
        self.modified = True
        super().clear()


class SecureCookieSessionInterface(SessionInterface):
    """A session interface that stores session data in a signed cookie.

    The cookie value is ``base64(json(data)).signature`` where the
    signature is an HMAC-SHA256 of the data using the app's secret key.
    """

    #: The cookie name used for the session.
    cookie_name = "session"
    #: The cookie path.
    cookie_path = "/"
    #: The cookie HTTP-only flag.
    cookie_httponly = True
    #: The cookie Secure flag.
    cookie_secure = False
    #: The cookie SameSite attribute.
    cookie_samesite = "Lax"
    #: Session lifetime in seconds (None = browser session).
    cookie_max_age = None

    def _sign(self, data: str, secret_key: str) -> str:
        """Create an HMAC-SHA256 signature for the given data."""
        return hmac.new(
            secret_key.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _encode(self, session_data: dict, secret_key: str) -> str:
        """Encode and sign the session data for storage in a cookie."""
        json_str = json.dumps(session_data, separators=(",", ":"), ensure_ascii=False)
        b64 = base64.urlsafe_b64encode(json_str.encode("utf-8")).decode("utf-8")
        signature = self._sign(b64, secret_key)
        return f"{b64}.{signature}"

    def _decode(self, cookie_value: str, secret_key: str) -> t.Optional[dict]:
        """Decode and verify a signed cookie value."""
        if "." not in cookie_value:
            return None

        b64, signature = cookie_value.rsplit(".", 1)
        expected_signature = self._sign(b64, secret_key)

        if not hmac.compare_digest(signature, expected_signature):
            return None

        try:
            json_str = base64.urlsafe_b64decode(b64).decode("utf-8")
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            return None

    def open_session(self, request, app) -> SecureCookieSession:
        """Load the session from the request cookies."""
        cookie_value = request.cookies.get(self.cookie_name)
        if not cookie_value:
            return SecureCookieSession()

        secret_key = app.secret_key
        if not secret_key:
            return SecureCookieSession()

        data = self._decode(cookie_value, secret_key)
        if data is None:
            return SecureCookieSession()

        return SecureCookieSession(data)

    def save_session(self, response, session: SecureCookieSession, app):
        """Save the session to the response cookies."""
        if not session.modified:
            return

        secret_key = app.secret_key
        if not secret_key:
            return

        if not session:
            # Session is empty, delete the cookie
            response.delete_cookie(
                self.cookie_name,
                path=self.cookie_path,
            )
            return

        cookie_value = self._encode(dict(session), secret_key)
        response.set_cookie(
            self.cookie_name,
            cookie_value,
            max_age=self.cookie_max_age,
            path=self.cookie_path,
            httponly=self.cookie_httponly,
            secure=self.cookie_secure,
            samesite=self.cookie_samesite,
        )
