"""
Tests for herokil.request - Request object.
"""

import io
import pytest
from herokil.request import Request


def make_environ(
    method="GET",
    path="/",
    query_string="",
    body=b"",
    content_type=None,
    headers=None,
    cookies=None,
):
    """Helper to build a WSGI environ dict for testing."""
    environ = {
        "REQUEST_METHOD": method,
        "SCRIPT_NAME": "",
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "5000",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(body),
        "wsgi.errors": io.StringIO(),
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
        "CONTENT_LENGTH": str(len(body)),
    }
    if content_type:
        environ["CONTENT_TYPE"] = content_type
    if headers:
        for key, value in headers.items():
            environ[f"HTTP_{key.upper().replace('-', '_')}"] = value
    if cookies:
        environ["HTTP_COOKIE"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    return environ


class TestRequest:
    """Tests for the Request class."""

    def test_method(self):
        """Request.method returns the HTTP method."""
        req = Request(make_environ(method="POST"))
        assert req.method == "POST"

    def test_path(self):
        """Request.path returns the URL path."""
        req = Request(make_environ(path="/hello/world"))
        assert req.path == "/hello/world"

    def test_query_string(self):
        """Request.query_string returns the raw query string."""
        req = Request(make_environ(query_string="name=alice&age=30"))
        assert req.query_string == "name=alice&age=30"

    def test_args(self):
        """Request.args returns parsed query parameters."""
        req = Request(make_environ(query_string="name=alice&age=30"))
        assert req.args["name"] == "alice"
        assert req.args["age"] == "30"

    def test_args_empty(self):
        """Request.args is empty when no query string is provided."""
        req = Request(make_environ())
        assert req.args == {}

    def test_form(self):
        """Request.form parses URL-encoded form data."""
        body = b"name=alice&age=30"
        req = Request(make_environ(
            method="POST",
            body=body,
            content_type="application/x-www-form-urlencoded",
        ))
        assert req.form["name"] == "alice"
        assert req.form["age"] == "30"

    def test_json(self):
        """Request.json parses JSON body."""
        import json
        body = json.dumps({"name": "alice", "age": 30}).encode()
        req = Request(make_environ(
            method="POST",
            body=body,
            content_type="application/json",
        ))
        assert req.json["name"] == "alice"
        assert req.json["age"] == 30

    def test_json_invalid(self):
        """Request.json returns None for invalid JSON."""
        req = Request(make_environ(
            method="POST",
            body=b"not json",
            content_type="application/json",
        ))
        assert req.json is None

    def test_get_data(self):
        """Request.get_data returns the raw body bytes."""
        body = b"hello world"
        req = Request(make_environ(body=body))
        assert req.get_data() == body

    def test_get_data_as_text(self):
        """Request.get_data(as_text=True) returns the body as a string."""
        body = b"hello world"
        req = Request(make_environ(body=body))
        assert req.get_data(as_text=True) == "hello world"

    def test_headers(self):
        """Request.headers returns parsed HTTP headers."""
        req = Request(make_environ(headers={
            "Accept": "text/html",
            "X-Custom": "value",
        }))
        assert req.headers["Accept"] == "text/html"
        assert req.headers["X-Custom"] == "value"

    def test_cookies(self):
        """Request.cookies returns parsed cookies."""
        req = Request(make_environ(cookies={"session_id": "abc123", "theme": "dark"}))
        assert req.cookies["session_id"] == "abc123"
        assert req.cookies["theme"] == "dark"

    def test_content_type(self):
        """Request.content_type returns the Content-Type header."""
        req = Request(make_environ(content_type="application/json"))
        assert req.content_type == "application/json"

    def test_content_length(self):
        """Request.content_length returns the Content-Length as an integer."""
        req = Request(make_environ(body=b"12345"))
        assert req.content_length == 5

    def test_user_agent(self):
        """Request.user_agent returns the User-Agent header."""
        req = Request(make_environ(headers={"User-Agent": "TestBot/1.0"}))
        assert req.user_agent == "TestBot/1.0"

    def test_remote_addr(self):
        """Request.remote_addr returns the client IP."""
        req = Request(make_environ())
        assert req.remote_addr == "127.0.0.1"

    def test_is_json(self):
        """Request.is_json detects JSON content type."""
        req = Request(make_environ(content_type="application/json"))
        assert req.is_json is True
        req2 = Request(make_environ(content_type="text/html"))
        assert req2.is_json is False

    def test_scheme(self):
        """Request.scheme returns the URL scheme."""
        req = Request(make_environ())
        assert req.scheme == "http"

    def test_host(self):
        """Request.host returns the Host header."""
        req = Request(make_environ(headers={"Host": "example.com"}))
        assert req.host == "example.com"

    def test_full_url(self):
        """Request.full_url reconstructs the full request URL."""
        req = Request(make_environ(
            path="/hello",
            query_string="name=world",
            headers={"Host": "example.com"},
        ))
        assert "example.com" in req.full_url
        assert "/hello" in req.full_url

    def test_repr(self):
        """Request has a useful repr."""
        req = Request(make_environ(method="GET", path="/test"))
        assert "GET" in repr(req)
        assert "/test" in repr(req)
