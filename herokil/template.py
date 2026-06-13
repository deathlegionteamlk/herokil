"""
herokil.template - Template rendering with Jinja2 support.

Falls back to a simple string-template engine if Jinja2 is not installed,
so the framework works out of the box with no mandatory template dependency.
"""

import os
import re
import typing as t

try:
    import jinja2

    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False


class _SimpleTemplateEngine:
    """A minimal template engine that supports {{ var }} and {% if/for %} blocks.

    This is used as a fallback when Jinja2 is not installed. It supports
    basic variable interpolation, if/else conditionals, and for loops.
    """

    def render_string(self, source: str, **context: t.Any) -> str:
        """Render a template string with the given context variables."""
        result = self._process_blocks(source, context)
        return result

    def _process_blocks(self, source: str, context: t.Dict[str, t.Any]) -> str:
        """Process {% if %} and {% for %} blocks, then interpolate {{ }} expressions."""
        # Process {% for ... %} ... {% endfor %}
        source = self._process_for(source, context)
        # Process {% if ... %} ... {% else %} ... {% endif %}
        source = self._process_if(source, context)
        # Interpolate {{ expr }}
        source = self._interpolate(source, context)
        return source

    def _process_for(self, source: str, context: t.Dict[str, t.Any]) -> str:
        """Process {% for item in items %} ... {% endfor %} blocks."""
        pattern = re.compile(
            r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}(.*?)\{%\s*endfor\s*%\}",
            re.DOTALL,
        )

        def replace(match):
            var_name = match.group(1)
            iterable_name = match.group(2)
            body = match.group(3)
            iterable = context.get(iterable_name, [])
            parts = []
            for item in iterable:
                child_context = dict(context)
                child_context[var_name] = item
                parts.append(self._process_blocks(body, child_context))
            return "".join(parts)

        return pattern.sub(replace, source)

    def _process_if(self, source: str, context: t.Dict[str, t.Any]) -> str:
        """Process {% if condition %} ... {% else %} ... {% endif %} blocks."""
        pattern = re.compile(
            r"\{%\s*if\s+(.+?)\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}",
            re.DOTALL,
        )

        def replace(match):
            condition = match.group(1).strip()
            true_body = match.group(2)
            false_body = match.group(3)
            if self._eval_condition(condition, context):
                return self._process_blocks(true_body, context)
            else:
                return self._process_blocks(false_body, context)

        source = pattern.sub(replace, source)

        # Handle {% if %} ... {% endif %} without else
        pattern_no_else = re.compile(
            r"\{%\s*if\s+(.+?)\s*%\}(.*?)\{%\s*endif\s*%\}",
            re.DOTALL,
        )

        def replace_no_else(match):
            condition = match.group(1).strip()
            body = match.group(2)
            if self._eval_condition(condition, context):
                return self._process_blocks(body, context)
            return ""

        source = pattern_no_else.sub(replace_no_else, source)
        return source

    def _eval_condition(self, condition: str, context: t.Dict[str, t.Any]) -> bool:
        """Evaluate a simple condition expression."""
        # Support "not var" syntax
        if condition.startswith("not "):
            var = condition[4:].strip()
            return not bool(context.get(var, False))
        return bool(context.get(condition, False))

    def _interpolate(self, source: str, context: t.Dict[str, t.Any]) -> str:
        """Replace {{ expr }} with the evaluated value from context."""
        def replace(match):
            expr = match.group(1).strip()
            # Support dot notation like user.name
            parts = expr.split(".")
            value = context
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, "")
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    value = ""
                    break
            return str(value)

        return re.sub(r"\{\{\s*(.+?)\s*\}\}", replace, source)


# ── Global template state ──────────────────────────────────────────────

_simple_engine = _SimpleTemplateEngine()
_jinja_env: t.Optional["jinja2.Environment"] = None
_template_folder: t.Optional[str] = None


def _get_jinja_env(template_folder: str = None) -> "jinja2.Environment":
    """Get or create the Jinja2 environment."""
    global _jinja_env
    if _jinja_env is None:
        if template_folder is None:
            template_folder = _template_folder or "templates"
        loader = jinja2.FileSystemLoader(template_folder)
        _jinja_env = jinja2.Environment(
            loader=loader,
            autoescape=True,
            auto_reload=True,
        )
    return _jinja_env


def setup_templates(template_folder: str):
    """Configure the template system with the app's template folder.

    Called internally by Herokil.__init__ to set up template rendering.
    """
    global _template_folder, _jinja_env
    _template_folder = template_folder
    _jinja_env = None  # Reset so it will be recreated with the new folder


def render_template(template_name: str, **context: t.Any) -> str:
    """Render a template file with the given context variables.

    If Jinja2 is installed, it will be used for full-featured template
    rendering. Otherwise, the built-in simple template engine is used.

    Args:
        template_name: The filename of the template (relative to the
            template folder).
        **context: Variables to pass to the template.

    Returns:
        The rendered template string.

    Example::

        @app.route("/hello/<name>")
        def hello(name):
            return render_template("hello.html", name=name)
    """
    if HAS_JINJA2:
        env = _get_jinja_env()
        template = env.get_template(template_name)
        return template.render(**context)
    else:
        # Fallback: read file and use simple engine
        folder = _template_folder or "templates"
        filepath = os.path.join(folder, template_name)
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        return _simple_engine.render_string(source, **context)


def render_template_string(source: str, **context: t.Any) -> str:
    """Render a template string with the given context variables.

    If Jinja2 is installed, it will be used. Otherwise, the built-in
    simple template engine handles basic {{ var }}, {% if %}, and
    {% for %} syntax.

    Args:
        source: The template source string.
        **context: Variables to pass to the template.

    Returns:
        The rendered string.

    Example::

        @app.route("/greet")
        def greet():
            return render_template_string("<h1>Hello {{ name }}!</h1>", name="World")
    """
    if HAS_JINJA2:
        env = _get_jinja_env()
        template = env.from_string(source)
        return template.render(**context)
    else:
        return _simple_engine.render_string(source, **context)
