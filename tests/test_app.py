"""
Tests for herokil.app - Core application and test client.
"""

import json
import pytest
from herokil import Herokil, Response, redirect, jsonify, abort, Blueprint


@pytest.fixture
def app():
    """Create a fresh Herokil app for each test."""
    app = Herokil("herokil")

    @app.route("/")
    def index():
        return "Hello, World!"

    @app.route("/greet/<name>")
    def greet(name):
        return f"Hello, {name}!"

    @app.route("/user/<int:id>")
    def user(id):
        return f"User {id}"

    @app.route("/json")
    def json_route():
        return jsonify(message="ok", code=200)

    @app.route("/redirect")
    def redirect_route():
        return redirect("/")

    @app.route("/error")
    def error_route():
        abort(404)

    @app.route("/custom-response")
    def custom_response():
        return Response("Custom", status=201, content_type="text/plain")

    @app.route("/tuple-response")
    def tuple_response():
        return "Created", 201

    @app.route("/tuple-with-headers")
    def tuple_with_headers():
        return "OK", 200, {"X-Custom": "value"}

    @app.route("/dict-response")
    def dict_response():
        return {"key": "value"}

    @app.route("/post", methods=["POST"])
    def post_route():
        return "Posted"

    return app


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


class TestAppRouting:
    """Tests for basic routing functionality."""

    def test_index(self, client):
        """GET / returns 200 and correct body."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Hello, World!" in resp.text

    def test_string_param(self, client):
        """String URL parameters are passed to the view."""
        resp = client.get("/greet/alice")
        assert resp.status_code == 200
        assert "Hello, alice!" in resp.text

    def test_int_param(self, client):
        """Integer URL parameters are converted and passed."""
        resp = client.get("/user/42")
        assert resp.status_code == 200
        assert "User 42" in resp.text

    def test_404(self, client):
        """Non-existent routes return 404."""
        resp = client.get("/nonexistent")
        assert resp.status_code == 404

    def test_method_not_allowed(self, client):
        """Wrong method on a route returns 405."""
        resp = client.delete("/post")
        assert resp.status_code == 405

    def test_post_method(self, client):
        """POST requests work on routes with POST method."""
        resp = client.post("/post")
        assert resp.status_code == 200
        assert "Posted" in resp.text


class TestAppResponses:
    """Tests for different response types."""

    def test_string_response(self, client):
        """View functions can return plain strings."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Hello, World!" in resp.text

    def test_json_response(self, client):
        """jsonify() returns JSON with correct content type."""
        resp = client.get("/json")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["message"] == "ok"
        assert "application/json" in resp.get_header("Content-Type")

    def test_redirect_response(self, client):
        """redirect() returns a redirect response."""
        resp = client.get("/redirect")
        assert resp.status_code == 302
        assert resp.get_header("Location") == "/"

    def test_custom_response_object(self, client):
        """View functions can return Response objects directly."""
        resp = client.get("/custom-response")
        assert resp.status_code == 201
        assert resp.text == "Custom"
        assert "text/plain" in resp.get_header("Content-Type")

    def test_tuple_response_with_status(self, client):
        """View functions can return (body, status) tuples."""
        resp = client.get("/tuple-response")
        assert resp.status_code == 201
        assert "Created" in resp.text

    def test_tuple_response_with_headers(self, client):
        """View functions can return (body, status, headers) tuples."""
        resp = client.get("/tuple-with-headers")
        assert resp.status_code == 200
        assert resp.get_header("X-Custom") == "value"

    def test_dict_response(self, client):
        """View functions can return dicts (auto-converted to JSON)."""
        resp = client.get("/dict-response")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["key"] == "value"


class TestAppHooks:
    """Tests for before/after request hooks."""

    def test_before_request(self):
        """before_request hooks run before the view."""
        app = Herokil("test")
        calls = []

        @app.before_request
        def check():
            calls.append("before")

        @app.route("/")
        def index():
            calls.append("view")
            return "OK"

        client = app.test_client()
        client.get("/")
        assert calls == ["before", "view"]

    def test_before_request_short_circuit(self):
        """before_request can return a response to skip the view."""
        app = Herokil("test")

        @app.before_request
        def deny():
            return Response("Denied", status=403)

        @app.route("/")
        def index():
            return "OK"

        client = app.test_client()
        resp = client.get("/")
        assert resp.status_code == 403
        assert "Denied" in resp.text

    def test_after_request(self):
        """after_request hooks can modify the response."""
        app = Herokil("test")

        @app.after_request
        def add_header(response):
            response.set_header("X-Custom", "added")
            return response

        @app.route("/")
        def index():
            return "OK"

        client = app.test_client()
        resp = client.get("/")
        assert resp.get_header("X-Custom") == "added"


class TestAppErrorHandlers:
    """Tests for custom error handlers."""

    def test_custom_404(self):
        """Custom 404 handlers override the default error page."""
        app = Herokil("test")

        @app.errorhandler(404)
        def not_found(e):
            return "Custom 404", 404

        @app.route("/")
        def index():
            return "OK"

        client = app.test_client()
        resp = client.get("/missing")
        assert resp.status_code == 404
        assert "Custom 404" in resp.text


class TestAppBlueprints:
    """Tests for Blueprint support."""

    def test_blueprint_route(self):
        """Blueprint routes are registered with their prefix."""
        app = Herokil("test")
        api = Blueprint("api", __name__, url_prefix="/api")

        @api.route("/hello")
        def hello():
            return "API Hello"

        app.register_blueprint(api)
        client = app.test_client()
        resp = client.get("/api/hello")
        assert resp.status_code == 200
        assert "API Hello" in resp.text

    def test_blueprint_with_params(self):
        """Blueprint routes support URL parameters."""
        app = Herokil("test")
        api = Blueprint("api", __name__, url_prefix="/api")

        @api.route("/user/<name>")
        def user(name):
            return f"User: {name}"

        app.register_blueprint(api)
        client = app.test_client()
        resp = client.get("/api/user/alice")
        assert "User: alice" in resp.text


class TestAppAbort:
    """Tests for the abort() function."""

    def test_abort_404(self, client):
        """abort(404) returns a 404 response."""
        resp = client.get("/error")
        assert resp.status_code == 404

    def test_abort_403(self):
        """abort(403) returns a 403 response."""
        app = Herokil("test")

        @app.route("/forbidden")
        def forbidden():
            abort(403)

        client = app.test_client()
        resp = client.get("/forbidden")
        assert resp.status_code == 403


class TestAppAddUrlRule:
    """Tests for add_url_rule (programmatic route registration)."""

    def test_add_url_rule(self):
        """add_url_rule registers a route without a decorator."""
        app = Herokil("test")
        app.add_url_rule("/hello", "hello", lambda: "Hello!")
        client = app.test_client()
        resp = client.get("/hello")
        assert "Hello!" in resp.text


class TestAppConfig:
    """Tests for application configuration."""

    def test_debug_mode(self):
        """debug() enables debug mode."""
        app = Herokil("test")
        app.debug(True)
        assert app.config["DEBUG"] is True

    def test_testing_mode(self):
        """testing() enables testing mode."""
        app = Herokil("test")
        app.testing(True)
        assert app.config["TESTING"] is True

    def test_secret_key(self):
        """secret_key is stored in config."""
        app = Herokil("test", secret_key="supersecret")
        assert app.config["SECRET_KEY"] == "supersecret"
