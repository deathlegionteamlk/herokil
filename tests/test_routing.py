"""
Tests for herokil.routing - URL routing engine.
"""

import pytest
from herokil.routing import Map, Rule, IntConverter, FloatConverter, PathConverter, UUIDConverter


class TestRule:
    """Tests for the Rule class."""

    def test_static_rule(self):
        """Static rules match exact paths."""
        rule = Rule("/hello", "hello")
        assert rule.match("/hello") == {}
        assert rule.match("/world") is None

    def test_string_parameter(self):
        """String parameters capture a single path segment."""
        rule = Rule("/user/<name>", "profile")
        result = rule.match("/user/alice")
        assert result == {"name": "alice"}
        assert rule.match("/user/") is None

    def test_int_parameter(self):
        """Int parameters capture and convert numeric path segments."""
        rule = Rule("/post/<int:id>", "post")
        result = rule.match("/post/42")
        assert result == {"id": 42}
        assert isinstance(result["id"], int)
        assert rule.match("/post/abc") is None

    def test_float_parameter(self):
        """Float parameters capture decimal numbers."""
        rule = Rule("/price/<float:amount>", "price")
        result = rule.match("/price/19.99")
        assert result == {"amount": 19.99}
        assert isinstance(result["amount"], float)

    def test_path_parameter(self):
        """Path parameters capture the rest of the URL including slashes."""
        rule = Rule("/files/<path:filepath>", "files")
        result = rule.match("/files/docs/readme.txt")
        assert result == {"filepath": "docs/readme.txt"}

    def test_uuid_parameter(self):
        """UUID parameters capture UUID-formatted strings."""
        rule = Rule("/item/<uuid:id>", "item")
        uid = "550e8400-e29b-41d4-a716-446655440000"
        result = rule.match(f"/item/{uid}")
        assert result == {"id": uid}

    def test_multiple_parameters(self):
        """Rules can have multiple parameters."""
        rule = Rule("/user/<name>/post/<int:id>", "user_post")
        result = rule.match("/user/alice/post/7")
        assert result == {"name": "alice", "id": 7}

    def test_build_static(self):
        """Static rules build their exact pattern."""
        rule = Rule("/hello", "hello")
        assert rule.build() == "/hello"

    def test_build_with_params(self):
        """Rules build URLs by substituting parameters."""
        rule = Rule("/user/<name>", "profile")
        assert rule.build({"name": "alice"}) == "/user/alice"

    def test_build_int_param(self):
        """Int parameters are converted to strings when building URLs."""
        rule = Rule("/post/<int:id>", "post")
        assert rule.build({"id": 42}) == "/post/42"

    def test_build_missing_param(self):
        """Building with missing parameters returns None."""
        rule = Rule("/user/<name>", "profile")
        assert rule.build() is None

    def test_methods_default(self):
        """Default methods are GET and HEAD."""
        rule = Rule("/", "index")
        assert rule.methods == {"GET", "HEAD"}

    def test_methods_custom(self):
        """Custom methods can be specified."""
        rule = Rule("/api", "api", methods=["POST", "PUT"])
        assert rule.methods == {"POST", "PUT"}


class TestMap:
    """Tests for the Map (router) class."""

    def test_match_static(self):
        """Map matches static routes."""
        m = Map()
        m.add(Rule("/hello", "hello"))
        endpoint, params = m.match("/hello")
        assert endpoint == "hello"
        assert params == {}

    def test_match_with_params(self):
        """Map matches routes and extracts parameters."""
        m = Map()
        m.add(Rule("/user/<name>", "profile"))
        endpoint, params = m.match("/user/bob")
        assert endpoint == "profile"
        assert params == {"name": "bob"}

    def test_match_no_match(self):
        """Map returns None when no route matches."""
        m = Map()
        m.add(Rule("/hello", "hello"))
        endpoint, params = m.match("/world")
        assert endpoint is None
        assert params is None

    def test_match_method(self):
        """Map respects HTTP method constraints."""
        m = Map()
        m.add(Rule("/api", "api_get", methods={"GET"}))
        m.add(Rule("/api", "api_post", methods={"POST"}))
        assert m.match("/api", "GET") == ("api_get", {})
        assert m.match("/api", "POST") == ("api_post", {})

    def test_match_method_not_allowed(self):
        """Map raises MethodNotAllowed for wrong method on existing path."""
        from herokil.exceptions import MethodNotAllowed
        m = Map()
        m.add(Rule("/api", "api", methods={"POST"}))
        with pytest.raises(MethodNotAllowed):
            m.match("/api", "DELETE")

    def test_url_for(self):
        """Map can build URLs by endpoint name."""
        m = Map()
        m.add(Rule("/user/<name>", "profile"))
        assert m.url_for("profile", name="alice") == "/user/alice"

    def test_url_for_unknown_endpoint(self):
        """url_for returns None for unknown endpoints."""
        m = Map()
        assert m.url_for("nonexistent") is None

    def test_multiple_rules(self):
        """Map can match against multiple registered rules."""
        m = Map()
        m.add(Rule("/", "index"))
        m.add(Rule("/about", "about"))
        m.add(Rule("/user/<name>", "profile"))
        assert m.match("/") == ("index", {})
        assert m.match("/about") == ("about", {})
        assert m.match("/user/charlie") == ("profile", {"name": "charlie"})
