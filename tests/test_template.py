"""
Tests for herokil.template - Template rendering.
"""

import os
import tempfile
import pytest
from herokil.template import render_template_string, render_template, setup_templates, _simple_engine


class TestSimpleTemplateEngine:
    """Tests for the built-in simple template engine."""

    def test_variable_interpolation(self):
        """{{ var }} is replaced with the context value."""
        result = _simple_engine.render_string("Hello, {{ name }}!", name="World")
        assert result == "Hello, World!"

    def test_multiple_variables(self):
        """Multiple {{ }} expressions are all interpolated."""
        result = _simple_engine.render_string("{{ a }} and {{ b }}", a="foo", b="bar")
        assert result == "foo and bar"

    def test_dot_notation(self):
        """{{ obj.attr }} accesses attributes with dot notation."""
        result = _simple_engine.render_string("{{ user.name }}", user={"name": "alice"})
        assert result == "alice"

    def test_if_block_true(self):
        """{% if var %} renders when the variable is truthy."""
        result = _simple_engine.render_string("{% if show %}Visible{% endif %}", show=True)
        assert result == "Visible"

    def test_if_block_false(self):
        """{% if var %} does not render when the variable is falsy."""
        result = _simple_engine.render_string("{% if show %}Visible{% endif %}", show=False)
        assert result == ""

    def test_if_else_block(self):
        """{% if/else %} renders the correct branch."""
        result = _simple_engine.render_string(
            "{% if active %}Yes{% else %}No{% endif %}", active=False
        )
        assert result == "No"

    def test_not_condition(self):
        """{% if not var %} supports negation."""
        result = _simple_engine.render_string(
            "{% if not hidden %}Shown{% endif %}", hidden=False
        )
        assert result == "Shown"

    def test_for_block(self):
        """{% for item in items %} iterates over a list."""
        result = _simple_engine.render_string(
            "{% for item in items %}{{ item }} {% endfor %}",
            items=["a", "b", "c"]
        )
        assert result == "a b c "

    def test_nested_for_and_if(self):
        """For and if blocks can be nested."""
        result = _simple_engine.render_string(
            "{% for item in items %}{% if item %}{{ item }}{% endif %}{% endfor %}",
            items=["a", "", "c"]
        )
        assert result == "ac"

    def test_missing_variable(self):
        """Missing variables render as empty string."""
        result = _simple_engine.render_string("{{ missing }}")
        assert result == ""


class TestRenderTemplateString:
    """Tests for render_template_string()."""

    def test_simple(self):
        """render_template_string interpolates variables."""
        result = render_template_string("Hello, {{ name }}!", name="World")
        assert result == "Hello, World!"


class TestRenderTemplate:
    """Tests for render_template() with file-based templates."""

    def test_render_file(self):
        """render_template reads and renders a template file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a template file
            template_path = os.path.join(tmpdir, "hello.html")
            with open(template_path, "w") as f:
                f.write("<h1>Hello, {{ name }}!</h1>")

            setup_templates(tmpdir)
            result = render_template("hello.html", name="World")
            assert "Hello, World!" in result
