"""
Tests for herokil.blueprints - Blueprint support.
"""

import pytest
from herokil import Herokil, Blueprint, abort


class TestBlueprint:
    """Tests for the Blueprint class."""

    def test_blueprint_creation(self):
        """Blueprints can be created with a name and import name."""
        bp = Blueprint("api", __name__)
        assert bp.name == "api"
        assert bp.url_prefix == ""

    def test_blueprint_url_prefix(self):
        """Blueprints can have a URL prefix."""
        bp = Blueprint("api", __name__, url_prefix="/api/v1")
        assert bp.url_prefix == "/api/v1"

    def test_blueprint_route_decorator(self):
        """The route decorator registers routes on the blueprint."""
        bp = Blueprint("api", __name__)

        @bp.route("/hello")
        def hello():
            return "Hello"

        assert "hello" in bp._view_functions

    def test_blueprint_register(self):
        """Registering a blueprint adds its routes to the app."""
        app = Herokil("test")
        bp = Blueprint("api", __name__, url_prefix="/api")

        @bp.route("/hello")
        def hello():
            return "Hello"

        app.register_blueprint(bp)
        client = app.test_client()
        resp = client.get("/api/hello")
        assert resp.status_code == 200

    def test_blueprint_multiple_routes(self):
        """A blueprint can have multiple routes."""
        app = Herokil("test")
        bp = Blueprint("api", __name__, url_prefix="/api")

        @bp.route("/users")
        def users():
            return "Users"

        @bp.route("/posts")
        def posts():
            return "Posts"

        app.register_blueprint(bp)
        client = app.test_client()
        assert client.get("/api/users").status_code == 200
        assert client.get("/api/posts").status_code == 200

    def test_blueprint_with_params(self):
        """Blueprint routes support URL parameters."""
        app = Herokil("test")
        bp = Blueprint("api", __name__, url_prefix="/api")

        @bp.route("/user/<name>")
        def user(name):
            return f"User: {name}"

        app.register_blueprint(bp)
        client = app.test_client()
        resp = client.get("/api/user/alice")
        assert "User: alice" in resp.text

    def test_blueprint_override_prefix(self):
        """register_blueprint can override the URL prefix."""
        app = Herokil("test")
        bp = Blueprint("api", __name__, url_prefix="/api")

        @bp.route("/hello")
        def hello():
            return "Hello"

        app.register_blueprint(bp, url_prefix="/v2")
        client = app.test_client()
        resp = client.get("/v2/hello")
        assert resp.status_code == 200

    def test_blueprint_before_request(self):
        """Blueprint before_request hooks run for blueprint routes."""
        app = Herokil("test")
        bp = Blueprint("api", __name__, url_prefix="/api")
        calls = []

        @bp.before_request
        def check():
            calls.append("before")

        @bp.route("/hello")
        def hello():
            calls.append("view")
            return "Hello"

        app.register_blueprint(bp)
        client = app.test_client()
        client.get("/api/hello")
        assert "before" in calls
        assert "view" in calls

    def test_blueprint_error_handler(self):
        """Blueprint error handlers are registered on the app."""
        app = Herokil("test")
        bp = Blueprint("api", __name__, url_prefix="/api")

        @bp.errorhandler(404)
        def not_found(e):
            return "API Not Found", 404

        @bp.route("/hello")
        def hello():
            return "Hello"

        app.register_blueprint(bp)
        client = app.test_client()
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_multiple_blueprints(self):
        """Multiple blueprints can be registered on the same app."""
        app = Herokil("test")

        api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")
        api_v2 = Blueprint("api_v2", __name__, url_prefix="/api/v2")

        @api_v1.route("/hello")
        def hello_v1():
            return "v1 Hello"

        @api_v2.route("/hello")
        def hello_v2():
            return "v2 Hello"

        app.register_blueprint(api_v1)
        app.register_blueprint(api_v2)

        client = app.test_client()
        resp1 = client.get("/api/v1/hello")
        resp2 = client.get("/api/v2/hello")
        assert "v1 Hello" in resp1.text
        assert "v2 Hello" in resp2.text
