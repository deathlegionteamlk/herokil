"""
herokil.request - Request object wrapping the WSGI environ.

Provides a high-level interface to the incoming HTTP request, including
access to query parameters, form data, JSON body, headers, cookies,
and file uploads.
"""

import json
import io
from http.cookies import SimpleCookie
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote


class Request:
    """Represents an incoming HTTP request.

    Wraps the WSGI ``environ`` dictionary and provides convenient
    property-based access to all request data.

    Attributes:
        environ: The raw WSGI environ dictionary.
    """

    def __init__(self, environ: Dict[str, Any]):
        self.environ = environ
        self._args = None
        self._form = None
        self._json = None
        self._json_parsed = False
        self._files = None
        self._cookies = None
        self._data = None

    # ── HTTP method and URL ────────────────────────────────────────

    @property
    def method(self) -> str:
        """The HTTP method (GET, POST, PUT, DELETE, etc.)."""
        return self.environ.get("REQUEST_METHOD", "GET").upper()

    @property
    def path(self) -> str:
        """The path portion of the URL (e.g. '/users/42')."""
        return self.environ.get("PATH_INFO", "/")

    @property
    def full_url(self) -> str:
        """The full reconstructed request URL."""
        scheme = self.environ.get("wsgi.url_scheme", "http")
        host = self.environ.get("HTTP_HOST", "")
        if not host:
            host = self.environ.get("SERVER_NAME", "localhost")
            port = self.environ.get("SERVER_PORT", "")
            if port and port != ("443" if scheme == "https" else "80"):
                host += f":{port}"
        path = self.environ.get("SCRIPT_NAME", "") + self.environ.get("PATH_INFO", "/")
        query = self.environ.get("QUERY_STRING", "")
        url = f"{scheme}://{host}{path}"
        if query:
            url += f"?{query}"
        return url

    @property
    def url_root(self) -> str:
        """The scheme + host (e.g. 'http://localhost:5000')."""
        scheme = self.environ.get("wsgi.url_scheme", "http")
        host = self.environ.get("HTTP_HOST", "")
        if not host:
            host = self.environ.get("SERVER_NAME", "localhost")
        return f"{scheme}://{host}"

    @property
    def query_string(self) -> str:
        """The raw query string (without the '?')."""
        return self.environ.get("QUERY_STRING", "")

    @property
    def scheme(self) -> str:
        """The URL scheme ('http' or 'https')."""
        return self.environ.get("wsgi.url_scheme", "http")

    @property
    def host(self) -> str:
        """The host header value."""
        return self.environ.get("HTTP_HOST", self.environ.get("SERVER_NAME", "localhost"))

    # ── Parsed query string ────────────────────────────────────────

    @property
    def args(self) -> Dict[str, str]:
        """Parsed query string parameters as a dict.

        For multi-valued keys, only the last value is kept.
        For all values, use :meth:`args_getlist`.
        """
        if self._args is None:
            qs = parse_qs(self.query_string, keep_blank_values=True)
            self._args = {k: v[-1] for k, v in qs.items()}
        return self._args

    def args_getlist(self, key: str) -> List[str]:
        """Return all values for a query parameter as a list."""
        qs = parse_qs(self.query_string, keep_blank_values=True)
        return qs.get(key, [])

    # ── Form data ──────────────────────────────────────────────────

    @property
    def form(self) -> Dict[str, str]:
        """Parsed form data from the request body (application/x-www-form-urlencoded)."""
        if self._form is None:
            self._parse_form()
        return self._form or {}

    def form_getlist(self, key: str) -> List[str]:
        """Return all values for a form field as a list."""
        if self._form is None:
            self._parse_form()
        return self._form_multi.get(key, [])

    def _parse_form(self):
        """Parse form data and file uploads from the request body."""
        content_type = self.content_type or ""
        self._form = {}
        self._form_multi = {}
        self._files = {}

        if "application/x-www-form-urlencoded" in content_type:
            body = self.get_data(as_text=True)
            qs = parse_qs(body, keep_blank_values=True)
            self._form = {k: v[-1] for k, v in qs.items()}
            self._form_multi = qs
        elif "multipart/form-data" in content_type:
            self._parse_multipart(content_type)

    def _parse_multipart(self, content_type: str):
        """Parse multipart/form-data for file uploads."""
        try:
            boundary = content_type.split("boundary=")[1].strip()
        except (IndexError, AttributeError):
            return

        body = self.get_data()
        if not body:
            return

        boundary_bytes = boundary.encode()
        parts = body.split(b"--" + boundary_bytes)

        for part in parts[1:]:  # Skip preamble
            if part.strip() in (b"", b"--\r\n", b"--"):
                continue

            # Split headers from body
            if b"\r\n\r\n" in part:
                header_section, file_data = part.split(b"\r\n\r\n", 1)
            else:
                continue

            # Remove trailing boundary markers
            if file_data.endswith(b"\r\n"):
                file_data = file_data[:-2]

            headers = {}
            for line in header_section.decode("utf-8", errors="replace").split("\r\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    headers[key.strip().lower()] = val.strip()

            disp = headers.get("content-disposition", "")
            name = None
            filename = None

            import re
            name_match = re.search(r'name="([^"]*)"', disp)
            if name_match:
                name = name_match.group(1)
            filename_match = re.search(r'filename="([^"]*)"', disp)
            if filename_match:
                filename = filename_match.group(1)

            if name:
                if filename:
                    self._files[name] = {
                        "filename": filename,
                        "content_type": headers.get("content-type", "application/octet-stream"),
                        "data": file_data,
                    }
                else:
                    value = file_data.decode("utf-8", errors="replace")
                    self._form[name] = value
                    self._form_multi.setdefault(name, []).append(value)

    # ── JSON body ──────────────────────────────────────────────────

    @property
    def json(self) -> Any:
        """Parsed JSON body, or None if the body is not valid JSON."""
        if not self._json_parsed:
            self._json_parsed = True
            try:
                data = self.get_data(as_text=True)
                if data:
                    self._json = json.loads(data)
            except (json.JSONDecodeError, ValueError):
                self._json = None
        return self._json

    # ── Raw body ───────────────────────────────────────────────────

    def get_data(self, as_text: bool = False) -> Any:
        """Read the raw request body.

        Args:
            as_text: If True, decode the body as UTF-8 text.

        Returns:
            The request body as bytes or str.
        """
        if self._data is None:
            try:
                content_length = int(self.environ.get("CONTENT_LENGTH", 0) or 0)
            except (ValueError, TypeError):
                content_length = 0

            body = self.environ.get("wsgi.input", io.BytesIO())
            self._data = body.read(content_length) if content_length else b""

        if as_text:
            return self._data.decode("utf-8", errors="replace")
        return self._data

    # ── Files ──────────────────────────────────────────────────────

    @property
    def files(self) -> Dict[str, Any]:
        """Uploaded files from multipart/form-data requests."""
        if self._files is None:
            self._parse_form()
        return self._files or {}

    # ── Headers ────────────────────────────────────────────────────

    @property
    def headers(self) -> Dict[str, str]:
        """HTTP headers as a dict (title-cased with hyphens)."""
        headers = {}
        for key, value in self.environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").title()
                headers[header_name] = value
        if "CONTENT_TYPE" in self.environ:
            headers["Content-Type"] = self.environ["CONTENT_TYPE"]
        if "CONTENT_LENGTH" in self.environ:
            headers["Content-Length"] = self.environ["CONTENT_LENGTH"]
        return headers

    def get_header(self, name: str, default: str = None) -> Optional[str]:
        """Get a specific header by name (case-insensitive)."""
        # Normalize the lookup name
        normalized = name.upper().replace("-", "_")
        # Check content-type / content-length specially
        if normalized in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            return self.environ.get(normalized, default)
        return self.environ.get(f"HTTP_{normalized}", default)

    @property
    def content_type(self) -> Optional[str]:
        """The Content-Type header value."""
        return self.environ.get("CONTENT_TYPE")

    @property
    def content_length(self) -> int:
        """The Content-Length header as an integer."""
        try:
            return int(self.environ.get("CONTENT_LENGTH", 0) or 0)
        except (ValueError, TypeError):
            return 0

    # ── Cookies ────────────────────────────────────────────────────

    @property
    def cookies(self) -> Dict[str, str]:
        """Request cookies as a dict."""
        if self._cookies is None:
            cookie_string = self.environ.get("HTTP_COOKIE", "")
            self._cookies = {}
            if cookie_string:
                cookie = SimpleCookie()
                cookie.load(cookie_string)
                for key, morsel in cookie.items():
                    self._cookies[key] = morsel.value
        return self._cookies

    # ── Referrer / User-Agent ──────────────────────────────────────

    @property
    def referrer(self) -> Optional[str]:
        """The Referer header value."""
        return self.environ.get("HTTP_REFERER")

    @property
    def user_agent(self) -> str:
        """The User-Agent header value."""
        return self.environ.get("HTTP_USER_AGENT", "")

    @property
    def remote_addr(self) -> str:
        """The client IP address."""
        return self.environ.get("REMOTE_ADDR", "127.0.0.1")

    # ── Convenience ────────────────────────────────────────────────

    @property
    def is_json(self) -> bool:
        """True if the Content-Type header indicates JSON."""
        ct = self.content_type or ""
        return "application/json" in ct

    @property
    def is_secure(self) -> bool:
        """True if the request was made over HTTPS."""
        return self.environ.get("wsgi.url_scheme") == "https"

    def __repr__(self):
        return f"<Request {self.method} {self.path}>"
