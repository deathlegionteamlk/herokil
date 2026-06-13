"""
herokil.routing - URL routing engine with decorator-based route registration.

Supports variable rules (<name>, <int:name>, <float:name>, <path:name>),
HTTP method constraints, and URL building via the reverse lookup system.
"""

import re
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, Tuple


# ── Converter definitions ──────────────────────────────────────────────

class BaseConverter:
    """Base class for URL parameter converters."""

    regex = r"[^/]+"
    weight = 100

    def to_python(self, value: str) -> Any:
        return value

    def to_url(self, value: Any) -> str:
        return str(value)


class StringConverter(BaseConverter):
    """Matches any string segment (default converter)."""

    regex = r"[^/]+"
    weight = 100


class IntConverter(BaseConverter):
    """Matches integer path segments."""

    regex = r"\d+"
    weight = 50

    def to_python(self, value: str) -> int:
        return int(value)

    def to_url(self, value: Any) -> str:
        return str(int(value))


class FloatConverter(BaseConverter):
    """Matches floating-point path segments."""

    regex = r"\d+\.\d+"
    weight = 50

    def to_python(self, value: str) -> float:
        return float(value)

    def to_url(self, value: Any) -> str:
        return str(float(value))


class PathConverter(BaseConverter):
    """Matches the rest of the URL path including slashes."""

    regex = r".+"
    weight = 200


class UUIDConverter(BaseConverter):
    """Matches UUID path segments."""

    regex = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    weight = 50

    def to_python(self, value: str) -> str:
        return str(value)

    def to_url(self, value: Any) -> str:
        return str(value)


DEFAULT_CONVERTERS = {
    "default": StringConverter,
    "string": StringConverter,
    "int": IntConverter,
    "float": FloatConverter,
    "path": PathConverter,
    "uuid": UUIDConverter,
}


# ── Rule parsing ───────────────────────────────────────────────────────

_PARAM_RE = re.compile(r"<(?:(\w+):)?(\w+)>")


class Rule:
    """A single URL rule that maps a URL pattern to an endpoint.

    Attributes:
        rule: The URL pattern string (e.g. '/user/<int:id>').
        endpoint: The internal name for this route.
        methods: Set of allowed HTTP methods.
        view_func: The handler function.
        converter_map: Dict mapping parameter names to converter instances.
    """

    def __init__(self, rule: str, endpoint: str, methods: Optional[set] = None,
                 view_func: Optional[Callable] = None,
                 converters: Optional[Dict[str, type]] = None):
        self.rule = rule
        self.endpoint = endpoint
        self.methods = methods or {"GET", "HEAD"}
        if isinstance(self.methods, (list, tuple)):
            self.methods = set(m.upper() for m in self.methods)
        self.view_func = view_func
        self.converter_map: Dict[str, BaseConverter] = {}
        self._converters = converters or DEFAULT_CONVERTERS
        self._regex = None
        self._parse_rule()

    def _parse_rule(self):
        """Parse the URL pattern and build a regex for matching."""
        pattern = self.rule
        self.converter_map = {}

        def _replace(match):
            converter_name = match.group(1) or "default"
            param_name = match.group(2)
            converter_cls = self._converters.get(converter_name, StringConverter)
            self.converter_map[param_name] = converter_cls()
            return f"(?P<{param_name}>{converter_cls.regex})"

        self._regex = re.compile("^" + _PARAM_RE.sub(_replace, pattern) + "$")

    def match(self, path: str) -> Optional[Dict[str, Any]]:
        """Try to match the given path, returning extracted parameters or None."""
        m = self._regex.match(path)
        if m is None:
            return None
        values = m.groupdict()
        # Convert values using their converters
        for key, converter in self.converter_map.items():
            if key in values:
                values[key] = converter.to_python(values[key])
        return values

    def build(self, values: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Build a URL from this rule, substituting the given parameter values."""
        values = values or {}

        # Build list of replacements, checking for missing values
        parts = []
        last_end = 0
        for match in _PARAM_RE.finditer(self.rule):
            converter_name = match.group(1) or "default"
            param_name = match.group(2)
            if param_name not in values:
                return None
            converter_cls = self._converters.get(converter_name, StringConverter)
            converter = converter_cls()
            parts.append(self.rule[last_end:match.start()])
            parts.append(converter.to_url(values[param_name]))
            last_end = match.end()
        parts.append(self.rule[last_end:])
        return "".join(parts)

    def __repr__(self):
        return f"Rule({self.rule!r}, {self.endpoint!r}, methods={self.methods!r})"


# ── Map (router) ───────────────────────────────────────────────────────

class Map:
    """URL routing map that stores all rules and performs matching.

    This is the core routing engine. It stores Rule objects and provides
    methods to match incoming request paths and build URLs by endpoint name.
    """

    def __init__(self, converters: Optional[Dict[str, type]] = None):
        self._rules: List[Rule] = []
        self._rules_by_endpoint: Dict[str, List[Rule]] = {}
        self._converters = converters or DEFAULT_CONVERTERS

    def add(self, rule: Rule):
        """Register a Rule with this routing map."""
        rule._converters = self._converters
        rule._parse_rule()
        self._rules.append(rule)
        self._rules_by_endpoint.setdefault(rule.endpoint, []).append(rule)

    def match(self, path: str, method: str = "GET") -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Match a path and method against the registered rules.

        Returns:
            A tuple of (endpoint, params) or (None, None) if no match.
            Raises MethodNotAllowed if a matching path exists but the
            method is not allowed.
        """
        method = method.upper()
        path_match = False

        for rule in self._rules:
            params = rule.match(path)
            if params is not None:
                path_match = True
                if method in rule.methods:
                    return rule.endpoint, params

        if path_match:
            from herokil.exceptions import MethodNotAllowed
            raise MethodNotAllowed()

        return None, None

    def url_for(self, endpoint: str, **values) -> Optional[str]:
        """Build a URL for the given endpoint with the provided values.

        Args:
            endpoint: The endpoint name to build a URL for.
            **values: Parameter values to substitute into the URL pattern.

        Returns:
            The built URL string, or None if no matching rule was found.
        """
        rules = self._rules_by_endpoint.get(endpoint, [])
        for rule in rules:
            url = rule.build(values)
            if url is not None:
                return url
        return None

    def __iter__(self):
        return iter(self._rules)
