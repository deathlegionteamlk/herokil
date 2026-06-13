"""
Tests for herokil.response - Response object and helpers.
"""

import json
import pytest
from herokil.response import Response, redirect, jsonify


class TestResponse:
    """Tests for the Response class."""

    def test_string_body(self):
        """Response wraps a string body."""
        r = Response("Hello")
        assert r.get_data(as_text=True) == "Hello"

    def test_bytes_body(self):
        """Response wraps a bytes body."""
        r = Response(b"Hello")
        assert r.get_data() == b"Hello"

    def test_default_status(self):
        """Response default status is 200."""
        r = Response("OK")
        assert r.status_code == 200
        assert "200" in r.status

    def test_custom_status(self):
        """Response accepts a custom status code."""
        r = Response("Created", status=201)
        assert r.status_code == 201

    def test_default_content_type(self):
        """Response default Content-Type is text/html."""
        r = Response("<h1>Hi</h1>")
        assert r.get_header("Content-Type") == "text/html; charset=utf-8"

    def test_custom_content_type(self):
        """Response accepts a custom Content-Type."""
        r = Response("plain text", content_type="text/plain")
        assert r.get_header("Content-Type") == "text/plain"

    def test_set_header(self):
        """set_header replaces an existing header."""
        r = Response("OK")
        r.set_header("X-Custom", "value1")
        assert r.get_header("X-Custom") == "value1"
        r.set_header("X-Custom", "value2")
        assert r.get_header("X-Custom") == "value2"

    def test_delete_header(self):
        """delete_header removes a header."""
        r = Response("OK")
        r.set_header("X-Custom", "value")
        r.delete_header("X-Custom")
        assert r.get_header("X-Custom") is None

    def test_data_property(self):
        """The data property provides access to the body as bytes."""
        r = Response("hello")
        assert r.data == b"hello"

    def test_data_setter(self):
        """The data property can be used to set the body."""
        r = Response("old")
        r.data = b"new"
        assert r.data == b"new"

    def test_wsgi_call(self):
        """Response is callable as a WSGI app."""
        r = Response("Hello", status=200)
        environ = {}
        status_holder = []
        headers_holder = []

        def start_response(status, headers):
            status_holder.append(status)
            headers_holder.append(headers)

        result = r(environ, start_response)
        assert status_holder[0] == "200 OK"
        # Response body is in the result iterable
        body = b"".join(part.encode() if isinstance(part, str) else part for part in result)
        assert body == b"Hello"

    def test_cookies(self):
        """set_cookie adds Set-Cookie headers."""
        r = Response("OK")
        r.set_cookie("session", "abc123", httponly=True)
        environ = {}
        status_holder = []
        headers_holder = []

        def start_response(status, headers):
            status_holder.append(status)
            headers_holder.append(headers)

        r(environ, start_response)
        cookie_headers = [v for k, v in headers_holder[0] if k == "Set-Cookie"]
        assert any("session=abc123" in c for c in cookie_headers)

    def test_delete_cookie(self):
        """delete_cookie sets the cookie to expire immediately."""
        r = Response("OK")
        r.delete_cookie("session")
        environ = {}
        status_holder = []
        headers_holder = []

        def start_response(status, headers):
            status_holder.append(status)
            headers_holder.append(headers)

        r(environ, start_response)
        cookie_headers = [v for k, v in headers_holder[0] if k == "Set-Cookie"]
        assert any("Max-Age=0" in c for c in cookie_headers)

    def test_repr(self):
        """Response has a useful repr."""
        r = Response("OK")
        assert "200" in repr(r)


class TestRedirect:
    """Tests for the redirect() helper."""

    def test_redirect_302(self):
        """redirect() creates a 302 response by default."""
        r = redirect("/new")
        assert r.status_code == 302
        assert r.get_header("Location") == "/new"

    def test_redirect_301(self):
        """redirect() accepts a custom status code."""
        r = redirect("/new", code=301)
        assert r.status_code == 301

    def test_redirect_body_contains_link(self):
        """redirect() body contains the target URL."""
        r = redirect("/new")
        assert "/new" in r.get_data(as_text=True)


class TestJsonify:
    """Tests for the jsonify() helper."""

    def test_jsonify_dict(self):
        """jsonify() creates a JSON response from a dict."""
        r = jsonify(name="alice", age=30)
        data = json.loads(r.get_data(as_text=True))
        assert data["name"] == "alice"
        assert data["age"] == 30

    def test_jsonify_list(self):
        """jsonify() creates a JSON response from a list."""
        r = jsonify([1, 2, 3])
        data = json.loads(r.get_data(as_text=True))
        assert data == [1, 2, 3]

    def test_jsonify_content_type(self):
        """jsonify() sets the Content-Type to application/json."""
        r = jsonify(msg="ok")
        assert "application/json" in r.get_header("Content-Type")

    def test_jsonify_unicode(self):
        """jsonify() handles unicode characters."""
        r = jsonify(greeting="héllo wörld")
        data = json.loads(r.get_data(as_text=True))
        assert data["greeting"] == "héllo wörld"
