"""
herokil.response - Response object and helper functions.

Provides the Response class for building HTTP responses, along with
convenience helpers like redirect() and jsonify().
"""

import json
import typing as t
from datetime import datetime, timezone
from http.cookies import SimpleCookie


class Response:
    """Represents an outgoing HTTP response.

    Wraps response body, status code, and headers into a single object
    that can be returned from view functions and converted to a WSGI
    response by the framework.

    Args:
        response: The response body (str, bytes, or iterable).
        status: HTTP status code (int) or status string (e.g. '200 OK').
        headers: Optional dict or list of (name, value) header tuples.
        content_type: The Content-Type header value.

    Example::

        @app.route("/hello")
        def hello():
            return Response("Hello!", status=200, content_type="text/plain")
    """

    #: Default content type if none is specified.
    default_content_type = "text/html; charset=utf-8"
    #: Default status code.
    default_status = 200

    def __init__(
        self,
        response: t.Any = None,
        status: t.Optional[t.Union[int, str]] = None,
        headers: t.Optional[t.Union[dict, list]] = None,
        content_type: t.Optional[str] = None,
    ):
        # Body
        if response is None:
            self.response = []
        elif isinstance(response, (str, bytes, bytearray)):
            self.response = [response]
        elif isinstance(response, list):
            self.response = response
        else:
            self.response = [str(response)]

        # Status
        if status is None:
            self.status_code = self.default_status
        elif isinstance(status, int):
            self.status_code = status
        else:
            # Parse "200 OK" format
            self.status_code = int(status.split()[0])

        # Headers
        self.headers: t.List[t.Tuple[str, str]] = []
        if headers:
            if isinstance(headers, dict):
                for key, value in headers.items():
                    self.headers.append((key, str(value)))
            elif isinstance(headers, (list, tuple)):
                for item in headers:
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        self.headers.append((str(item[0]), str(item[1])))

        # Content-Type
        if content_type:
            # Replace any existing Content-Type
            self.headers = [(k, v) for k, v in self.headers if k.lower() != "content-type"]
            self.headers.append(("Content-Type", content_type))
        elif not any(k.lower() == "content-type" for k, _ in self.headers):
            self.headers.append(("Content-Type", self.default_content_type))

        # Cookies
        self._cookies: t.Optional[SimpleCookie] = None

    # ── Body helpers ───────────────────────────────────────────────

    def get_data(self, as_text: bool = False) -> t.Union[bytes, str]:
        """Return the response body as bytes (or str if as_text=True)."""
        parts = []
        for part in self.response:
            if isinstance(part, str):
                part = part.encode("utf-8")
            parts.append(part)
        data = b"".join(parts)
        if as_text:
            return data.decode("utf-8")
        return data

    def set_data(self, data: t.Union[str, bytes]):
        """Set the response body, replacing any existing content."""
        self.response = [data]

    @property
    def data(self) -> bytes:
        """The response body as bytes."""
        return self.get_data()

    @data.setter
    def data(self, value: t.Union[str, bytes]):
        self.set_data(value)

    # ── Status ─────────────────────────────────────────────────────

    @property
    def status(self) -> str:
        """The HTTP status line (e.g. '200 OK')."""
        from http import HTTPStatus

        try:
            return f"{self.status_code} {HTTPStatus(self.status_code).phrase}"
        except ValueError:
            return str(self.status_code)

    @status.setter
    def status(self, value: t.Union[int, str]):
        if isinstance(value, int):
            self.status_code = value
        else:
            self.status_code = int(str(value).split()[0])

    # ── Headers ────────────────────────────────────────────────────

    def get_header(self, name: str, default: t.Optional[str] = None) -> t.Optional[str]:
        """Get a response header by name (case-insensitive)."""
        name_lower = name.lower()
        for key, value in self.headers:
            if key.lower() == name_lower:
                return value
        return default

    def set_header(self, name: str, value: str):
        """Set a response header, replacing any existing header with the same name."""
        name_lower = name.lower()
        self.headers = [(k, v) for k, v in self.headers if k.lower() != name_lower]
        self.headers.append((name, str(value)))

    def delete_header(self, name: str):
        """Remove a response header by name."""
        name_lower = name.lower()
        self.headers = [(k, v) for k, v in self.headers if k.lower() != name_lower]

    # ── Cookies ────────────────────────────────────────────────────

    def set_cookie(
        self,
        key: str,
        value: str = "",
        max_age: t.Optional[int] = None,
        expires: t.Optional[t.Union[int, datetime, str]] = None,
        path: str = "/",
        domain: t.Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: t.Optional[str] = None,
    ):
        """Set a cookie on the response.

        Args:
            key: Cookie name.
            value: Cookie value.
            max_age: Number of seconds the cookie should last.
            expires: Specific expiry time.
            path: Cookie path (default '/').
            domain: Cookie domain.
            secure: Set the Secure flag.
            httponly: Set the HttpOnly flag.
            samesite: SameSite attribute ('Strict', 'Lax', or 'None').
        """
        if self._cookies is None:
            self._cookies = SimpleCookie()

        self._cookies[key] = value

        morsel = self._cookies[key]
        if max_age is not None:
            morsel["max-age"] = max_age
        if expires is not None:
            if isinstance(expires, datetime):
                expires = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
            morsel["expires"] = expires
        if path:
            morsel["path"] = path
        if domain:
            morsel["domain"] = domain
        if secure:
            morsel["secure"] = True
        if httponly:
            morsel["httponly"] = True
        if samesite:
            morsel["samesite"] = samesite

    def delete_cookie(self, key: str, path: str = "/", domain: t.Optional[str] = None):
        """Delete a cookie by setting it to expire immediately."""
        self.set_cookie(key, value="", max_age=0, path=path, domain=domain)

    # ── WSGI interface ─────────────────────────────────────────────

    def __call__(self, environ: dict, start_response: t.Callable) -> t.Iterable:
        """Produce a WSGI response."""
        # Build header list
        headers = list(self.headers)

        # Add cookie headers
        if self._cookies:
            for morsel in self._cookies.values():
                headers.append(("Set-Cookie", morsel.OutputString()))

        start_response(self.status, headers)
        return self.response

    def __repr__(self):
        return f"<Response {self.status_code} [{len(self.get_data())} bytes]>"


# ── Helper functions ───────────────────────────────────────────────────


def redirect(location: str, code: int = 302) -> Response:
    """Create a redirect response.

    Args:
        location: The URL to redirect to.
        code: HTTP status code (default 302).

    Returns:
        A Response object that redirects to the given location.

    Example::

        @app.route("/old")
        def old():
            return redirect("/new")
    """
    body = (
        f"<!DOCTYPE html>\n"
        f"<html>\n"
        f"<head><title>Redirecting...</title></head>\n"
        f"<body>\n"
        f"<h1>Redirecting...</h1>\n"
        f"<p>You should be redirected automatically to <a href=\"{location}\">{location}</a>.</p>\n"
        f"</body>\n"
        f"</html>"
    )
    response = Response(body, status=code, headers=[("Location", location)])
    return response


def jsonify(*args, **kwargs) -> Response:
    """Create a JSON response from the given data.

    If a single argument is provided, it is used as the root value.
    If keyword arguments are provided, they are collected into a dict.

    Args:
        *args: Positional data (at most one).
        **kwargs: Key-value data.

    Returns:
        A Response with Content-Type application/json.

    Example::

        @app.route("/api/user")
        def user():
            return jsonify(name="Alice", age=30)
    """
    indent = None
    sort_keys = False

    if args and kwargs:
        raise TypeError("jsonify() takes either positional or keyword arguments, not both.")
    elif len(args) > 1:
        raise TypeError("jsonify() takes at most 1 positional argument.")

    if args:
        data = args[0]
    else:
        data = kwargs

    body = json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
    return Response(body, content_type="application/json; charset=utf-8")
