"""
herokil.ctx - Request context proxies for thread-local access.

Provides proxy objects (request, session, g) that always resolve to
the current request's context, making it easy to access request data
from anywhere in your application without passing the request object
explicitly.
"""

import threading
import typing as t


class _CtxLocal:
    """Thread-local storage for request context data."""

    def __init__(self):
        self._local = threading.local()

    def push(self, request_obj=None, session_obj=None, g_obj=None):
        """Push a new request context onto the stack."""
        self._local.request = request_obj
        self._local.session = session_obj or {}
        self._local.g = g_obj or _GObject()

    def pop(self):
        """Pop the current request context."""
        self._local.request = None
        self._local.session = None
        self._local.g = None

    @property
    def request(self):
        return getattr(self._local, "request", None)

    @property
    def session(self):
        return getattr(self._local, "session", {})

    @property
    def g(self):
        return getattr(self._local, "g", None)


class _GObject:
    """A simple namespace object for storing arbitrary data during a request.

    Usage::

        from herokil import g

        @app.before_request
        def load_user():
            g.user = get_current_user()
    """

    def __getattr__(self, name: str):
        try:
            return self.__dict__[name]
        except KeyError:
            raise AttributeError(f"'g' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: t.Any):
        self.__dict__[name] = value

    def __delattr__(self, name: str):
        try:
            del self.__dict__[name]
        except KeyError:
            raise AttributeError(f"'g' object has no attribute '{name}'")

    def __contains__(self, name: str) -> bool:
        return name in self.__dict__

    def __repr__(self):
        return f"<g {self.__dict__}>"


# ── Module-level context ───────────────────────────────────────────────

_ctx = _CtxLocal()


class _RequestProxy:
    """Proxy to the current request object.

    Accesses attributes on the thread-local request, so you can
    write ``from herokil import request`` and use ``request.args``
    without passing the request around.
    """

    def __getattr__(self, name: str):
        req = _ctx.request
        if req is None:
            raise RuntimeError("Working outside of request context.")
        return getattr(req, name)

    def __repr__(self):
        req = _ctx.request
        if req is None:
            return "<Request [no context]>"
        return repr(req)


class _SessionProxy(dict):
    """Proxy to the current session dict.

    Behaves like a regular dict for the current request's session data.
    """

    def __init__(self):
        # Don't call super().__init__() - we proxy to _ctx.session
        pass

    def _get_session(self):
        s = _ctx.session
        if s is None:
            raise RuntimeError("Working outside of request context.")
        return s

    def __getitem__(self, key):
        return self._get_session().__getitem__(key)

    def __setitem__(self, key, value):
        self._get_session().__setitem__(key, value)

    def __delitem__(self, key):
        self._get_session().__delitem__(key)

    def __contains__(self, key):
        return key in self._get_session()

    def __len__(self):
        return len(self._get_session())

    def __iter__(self):
        return iter(self._get_session())

    def get(self, key, default=None):
        return self._get_session().get(key, default)

    def keys(self):
        return self._get_session().keys()

    def values(self):
        return self._get_session().values()

    def items(self):
        return self._get_session().items()

    def __repr__(self):
        try:
            return f"<Session {self._get_session()}>"
        except RuntimeError:
            return "<Session [no context]>"


class _GProxy:
    """Proxy to the current 'g' object for per-request storage."""

    def __getattr__(self, name: str):
        g = _ctx.g
        if g is None:
            raise RuntimeError("Working outside of request context.")
        return getattr(g, name)

    def __setattr__(self, name: str, value: t.Any):
        g = _ctx.g
        if g is None:
            raise RuntimeError("Working outside of request context.")
        setattr(g, name, value)

    def __repr__(self):
        g = _ctx.g
        if g is None:
            return "<g [no context]>"
        return repr(g)


# ── Public proxies ─────────────────────────────────────────────────────

request = _RequestProxy()
session = _SessionProxy()
g = _GProxy()
