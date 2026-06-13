"""
herokil.app - The core Herokil application class.

This module contains the central Herokil class that ties together
routing, request/response handling, templates, sessions, and the
development server.
"""

import os
import sys
import typing as t
import traceback

from herokil.routing import Map, Rule
from herokil.request import Request
from herokil.response import Response
from herokil.exceptions import HTTPException, NotFound, InternalServerError
from herokil.template import setup_templates
from herokil.ctx import _ctx
from herokil.static import serve_static


class Herokil:
    """The Herokil application object.

    Creates a new web application instance. This is the central object
    that holds your routes, configuration, and hooks.

    Args:
        import_name: The name of the application package (usually ``__name__``).
        static_url_path: URL prefix for static files (default ``/static``).
        static_folder: Path to the static files directory (default ``static``).
        template_folder: Path to the templates directory (default ``templates``).
        secret_key: A secret key for signing session cookies.

    Example::

        from herokil import Herokil

        app = Herokil(__name__)

        @app.route("/")
        def index():
            return "Hello, World!"

        if __name__ == "__main__":
            app.run()
    """

    #: The Herokil version string.
    version = "1.0.0"

    #: Default configuration values.
    default_config = {
        "DEBUG": False,
        "TESTING": False,
        "SECRET_KEY": None,
        "SERVER_NAME": None,
        "MAX_CONTENT_LENGTH": None,
        "PREFERRED_URL_SCHEME": "http",
        "JSON_SORT_KEYS": False,
        "JSONIFY_PRETTYPRINT_REGULAR": False,
    }

    def __init__(
        self,
        import_name: str,
        static_url_path: str = "/static",
        static_folder: str = "static",
        template_folder: str = "templates",
        secret_key: t.Optional[str] = None,
    ):
        self.import_name = import_name
        self.static_url_path = static_url_path
        self.static_folder = os.path.join(os.path.dirname(os.path.abspath(import_name)), static_folder)
        self.template_folder = os.path.join(os.path.dirname(os.path.abspath(import_name)), template_folder)
        self.secret_key = secret_key

        # Configuration
        self.config = dict(self.default_config)
        if secret_key:
            self.config["SECRET_KEY"] = secret_key

        # Routing
        self.url_map = Map()

        # View functions: endpoint -> callable
        self.view_functions: t.Dict[str, t.Callable] = {}

        # Hooks
        self._before_request_funcs: t.List[t.Callable] = []
        self._after_request_funcs: t.List[t.Callable] = []
        self._teardown_request_funcs: t.List[t.Callable] = []
        self._error_handlers: t.Dict[t.Union[int, type], t.Callable] = {}

        # Session interface
        self.session_interface = None
        if secret_key:
            from herokil.sessions import SecureCookieSessionInterface
            self.session_interface = SecureCookieSessionInterface()

        # Setup templates
        setup_templates(self.template_folder)

    # ── Configuration ──────────────────────────────────────────────

    def debug(self, flag: bool = True):
        """Enable or disable debug mode.

        In debug mode, the development server auto-reloads on code
        changes and shows detailed error pages.

        Args:
            flag: True to enable, False to disable.
        """
        self.config["DEBUG"] = flag
        return self

    def testing(self, flag: bool = True):
        """Enable or disable testing mode.

        Args:
            flag: True to enable, False to disable.
        """
        self.config["TESTING"] = flag
        return self

    # ── Route registration ─────────────────────────────────────────

    def route(self, rule: str, **options):
        """Register a route decorator.

        The ``rule`` argument defines the URL pattern, which can include
        variable sections using ``<name>`` or ``<converter:name>`` syntax.

        Args:
            rule: The URL rule string (e.g. ``/user/<int:id>``).
            **options: Options passed to the Rule constructor.
                - ``methods``: A list of HTTP methods (default ``['GET']``).
                - ``endpoint``: The endpoint name (default: function name).

        Returns:
            A decorator that registers the view function.

        Example::

            @app.route("/")
            def index():
                return "Hello!"

            @app.route("/user/<name>")
            def profile(name):
                return f"Hello, {name}!"

            @app.route("/api/data", methods=["GET", "POST"])
            def api_data():
                return jsonify(data="value")
        """
        def decorator(func: t.Callable) -> t.Callable:
            endpoint = options.pop("endpoint", func.__name__)
            methods = options.pop("methods", None)
            self.add_url_rule(rule, endpoint, func, methods=methods)
            return func
        return decorator

    def add_url_rule(
        self,
        rule: str,
        endpoint: t.Optional[str] = None,
        view_func: t.Optional[t.Callable] = None,
        methods: t.Optional[t.Union[list, set]] = None,
    ):
        """Register a URL rule directly (without a decorator).

        This is the lower-level API behind :meth:`route`. It's useful
        when you want to register routes programmatically.

        Args:
            rule: The URL rule string.
            endpoint: The endpoint name (default: view_func.__name__).
            view_func: The view function.
            methods: Allowed HTTP methods (default: ``['GET', 'HEAD']``).
        """
        if endpoint is None:
            if view_func is None:
                raise ValueError("Either endpoint or view_func must be provided.")
            endpoint = view_func.__name__

        rule_obj = Rule(rule, endpoint, methods=methods, view_func=view_func)
        self.url_map.add(rule_obj)
        self.view_functions[endpoint] = view_func

    # ── Hooks ──────────────────────────────────────────────────────

    def before_request(self, func: t.Callable) -> t.Callable:
        """Register a function to run before each request.

        The function is called with no arguments. If it returns a
        non-None value, that value is used as the response and the
        normal view function is not called.

        Example::

            @app.before_request
            def check_auth():
                if not is_authenticated():
                    abort(401)
        """
        self._before_request_funcs.append(func)
        return func

    def after_request(self, func: t.Callable) -> t.Callable:
        """Register a function to run after each request.

        The function receives the Response object and must return a
        Response. This is useful for modifying response headers,
        setting cookies, etc.

        Example::

            @app.after_request
            def add_security_headers(response):
                response.set_header("X-Content-Type-Options", "nosniff")
                return response
        """
        self._after_request_funcs.append(func)
        return func

    def teardown_request(self, func: t.Callable) -> t.Callable:
        """Register a function to run at the end of each request.

        Teardown functions are called even if an exception occurred
        during request processing. They receive the exception object
        (or None if no error occurred).

        Example::

            @app.teardown_request
            def close_db(exception):
                db.close()
        """
        self._teardown_request_funcs.append(func)
        return func

    def errorhandler(self, code_or_exception):
        """Register an error handler for a specific HTTP status code or exception type.

        Example::

            @app.errorhandler(404)
            def page_not_found(e):
                return "Page not found", 404

            @app.errorhandler(ValueError)
            def handle_value_error(e):
                return "Invalid value", 400
        """
        def decorator(func: t.Callable) -> t.Callable:
            self._error_handlers[code_or_exception] = func
            return func
        return decorator

    # ── Blueprint registration ─────────────────────────────────────

    def register_blueprint(self, blueprint, url_prefix: t.Optional[str] = None):
        """Register a Blueprint on this application.

        Args:
            blueprint: The Blueprint instance to register.
            url_prefix: Optional URL prefix override.
        """
        blueprint.register(self, url_prefix=url_prefix)

    # ── URL building ───────────────────────────────────────────────

    def url_for(self, endpoint: str, **values) -> str:
        """Build a URL for the given endpoint.

        Args:
            endpoint: The endpoint name.
            **values: Path parameter values.

        Returns:
            The generated URL string.
        """
        url = self.url_map.url_for(endpoint, **values)
        if url is None:
            raise ValueError(f"Could not build URL for endpoint {endpoint!r}.")
        return url

    # ── WSGI application ───────────────────────────────────────────

    def wsgi_app(self, environ: dict, start_response: t.Callable) -> t.Iterable:
        """The actual WSGI application.

        This method processes the request through the full pipeline:
        context setup, before-request hooks, routing, view dispatch,
        after-request hooks, and teardown.

        You can wrap this method to add middleware::

            app.wsgi_app = Middleware(app.wsgi_app)
        """
        # Create request object
        request = Request(environ)

        # Push request context
        _ctx.push(request_obj=request, g_obj=None)
        _ctx._app = self

        # Load session
        session_data = {}
        if self.session_interface:
            try:
                session_obj = self.session_interface.open_session(request, self)
                session_data = dict(session_obj) if session_obj else {}
            except Exception:
                session_data = {}
        _ctx._local.session = session_data

        response = None
        exception = None

        try:
            response = self._dispatch_request(request)
        except HTTPException as e:
            response = self._handle_http_exception(e)
        except Exception as e:
            exception = e
            response = self._handle_unhandled_exception(e)

        # After-request hooks
        try:
            for func in self._after_request_funcs:
                try:
                    result = func(response)
                    if result is not None:
                        response = result
                except Exception:
                    pass
        except Exception:
            pass

        # Save session
        if self.session_interface and _ctx.session is not None:
            try:
                from herokil.sessions import SecureCookieSession
                session_obj = SecureCookieSession(_ctx.session)
                session_obj.modified = _ctx.session != session_data
                self.session_interface.save_session(response, session_obj, self)
            except Exception:
                pass

        # Teardown
        for func in self._teardown_request_funcs:
            try:
                func(exception)
            except Exception:
                pass

        # Pop context
        _ctx.pop()

        return response(environ, start_response)

    def _dispatch_request(self, request: Request) -> Response:
        """Route the request and call the appropriate view function."""
        # Check for static file requests
        if self.static_url_path and request.path.startswith(self.static_url_path):
            filepath = request.path[len(self.static_url_path):].lstrip("/")
            if filepath:
                static_resp = serve_static(filepath, self.static_folder)
                if static_resp is not None:
                    return static_resp

        # Before-request hooks
        for func in self._before_request_funcs:
            result = func()
            if result is not None:
                if isinstance(result, Response):
                    return result
                return self._make_response(result)

        # Match route
        endpoint, params = self.url_map.match(request.path, request.method)

        if endpoint is None:
            raise NotFound()

        # Find view function
        view_func = self.view_functions.get(endpoint)
        if view_func is None:
            raise NotFound(f"No view function for endpoint {endpoint!r}.")

        # Call view function
        if params:
            result = view_func(**params)
        else:
            result = view_func()

        return self._make_response(result)

    def _make_response(self, result: t.Any) -> Response:
        """Convert a view function's return value into a Response object.

        Accepts:
        - A Response object (returned as-is)
        - A string (wrapped in a text/html Response)
        - A tuple of (body, status), (body, headers), or (body, status, headers)
        - A dict (converted to JSON)
        """
        if isinstance(result, Response):
            return result

        if isinstance(result, dict):
            from herokil.response import jsonify
            return jsonify(result)

        if isinstance(result, tuple):
            body = result[0]
            status = None
            headers = None

            if len(result) == 2:
                if isinstance(result[1], (dict, list)):
                    headers = result[1]
                else:
                    status = result[1]
            elif len(result) == 3:
                status = result[1]
                headers = result[2]

            if isinstance(body, dict):
                from herokil.response import jsonify
                resp = jsonify(body)
            elif isinstance(body, Response):
                resp = body
            else:
                resp = Response(body)

            if status is not None:
                if isinstance(status, int):
                    resp.status_code = status
                else:
                    resp.status = status

            if headers is not None:
                if isinstance(headers, dict):
                    for key, value in headers.items():
                        resp.set_header(key, value)
                elif isinstance(headers, (list, tuple)):
                    for key, value in headers:
                        resp.set_header(key, value)

            return resp

        # Default: treat as string
        return Response(str(result) if result is not None else "")

    def _handle_http_exception(self, exc: HTTPException) -> Response:
        """Handle an HTTPException, checking for custom error handlers."""
        # Check for custom error handler
        handler = self._error_handlers.get(exc.code) or self._error_handlers.get(type(exc))
        if handler:
            try:
                result = handler(exc)
                return self._make_response(result)
            except Exception:
                pass

        return Response(
            exc.get_body(),
            status=exc.code,
            headers=exc.get_headers(),
        )

    def _handle_unhandled_exception(self, exc: Exception) -> Response:
        """Handle an unhandled exception."""
        # Check for custom error handler
        handler = self._error_handlers.get(type(exc))
        if handler:
            try:
                result = handler(exc)
                return self._make_response(result)
            except Exception:
                pass

        handler = self._error_handlers.get(500)
        if handler:
            try:
                result = handler(exc)
                return self._make_response(result)
            except Exception:
                pass

        if self.config["DEBUG"]:
            # Show traceback in debug mode
            tb = traceback.format_exc()
            body = (
                f"<!DOCTYPE html>\n"
                f"<html>\n"
                f"<head><title>Internal Server Error</title></head>\n"
                f"<body>\n"
                f"<h1>Internal Server Error</h1>\n"
                f"<pre>{tb}</pre>\n"
                f"</body>\n"
                f"</html>"
            )
            return Response(body, status=500)

        return Response("Internal Server Error", status=500)

    # ── WSGI callable ──────────────────────────────────────────────

    def __call__(self, environ: dict, start_response: t.Callable) -> t.Iterable:
        """Make the application a WSGI callable."""
        return self.wsgi_app(environ, start_response)

    # ── Development server ─────────────────────────────────────────

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        debug: t.Optional[bool] = None,
        reloader: t.Optional[bool] = None,
        **options,
    ):
        """Start the development server.

        This is a convenience method that starts a WSGI server. It
        should **not** be used in production; use a production WSGI
        server like Gunicorn or uWSGI instead.

        Args:
            host: The hostname to listen on (default ``127.0.0.1``).
            port: The port to listen on (default ``5000``).
            debug: Enable/disable debug mode. If None, uses the config value.
            reloader: Enable/disable auto-reloader. Defaults to debug mode.
            **options: Additional options passed to the WSGI server.

        Example::

            if __name__ == "__main__":
                app.run(debug=True)
        """
        if debug is not None:
            self.config["DEBUG"] = debug

        if reloader is None:
            reloader = self.config["DEBUG"]

        if self.config["DEBUG"]:
            print(f" * Debug mode: on")
            print(f" * Restarting with reloader" if reloader else "")

        # Try Werkzeug first, then fall back to stdlib
        try:
            from werkzeug.serving import run_simple
            run_simple(
                host,
                port,
                self,
                use_reloader=reloader,
                use_debugger=self.config["DEBUG"],
                **options,
            )
        except ImportError:
            # Fall back to stdlib wsgiref
            self._run_stdlib(host, port, reloader)

    def _run_stdlib(self, host: str, port: int, reloader: bool):
        """Run using Python's built-in wsgiref server."""
        from wsgiref.simple_server import make_server

        print(f" * Herokil development server (wsgiref)")
        print(f" * Running on http://{host}:{port}/")
        print(f" * Press CTRL+C to quit")

        if reloader:
            self._run_with_reloader(host, port)
        else:
            try:
                server = make_server(host, port, self)
                server.serve_forever()
            except KeyboardInterrupt:
                print("\n * Server shutting down.")

    def _run_with_reloader(self, host: str, port: int):
        """Run the server with auto-reload on code changes."""
        import subprocess
        import sys

        while True:
            # Spawn a child process
            args = [sys.executable, "-c",
                    f"from wsgiref.simple_server import make_server; "
                    f"import importlib; "
                    f"module = importlib.import_module('{self.import_name}'); "
                    f"app = getattr(module, 'app', None); "
                    f"server = make_server('{host}', {port}, app); "
                    f"print(' * Running on http://{host}:{port}/'); "
                    f"server.serve_forever()"]

            process = subprocess.Popen(args)
            try:
                process.wait()
            except KeyboardInterrupt:
                process.terminate()
                print("\n * Server shutting down.")
                break

            if process.returncode != 0:
                print(" * Restarting due to crash...")
                import time
                time.sleep(1)

    # ── Test client ────────────────────────────────────────────────

    def test_client(self):
        """Create a test client for this application.

        Returns:
            A TestClient instance for making requests to the app.

        Example::

            client = app.test_client()
            response = client.get("/")
            assert response.status_code == 200
        """
        return TestClient(self)


class TestClient:
    """A simple test client for making requests to a Herokil application.

    Uses the same WSGI interface that a real HTTP server would use,
    but without going over the network. This allows fast, isolated
    testing of your application.
    """

    def __init__(self, app: Herokil):
        self.app = app
        app.config["TESTING"] = True

    def _make_environ(self, method: str, path: str, data: t.Optional[dict] = None,
                      json_data: t.Optional[t.Any] = None,
                      headers: t.Optional[dict] = None,
                      content_type: t.Optional[str] = None) -> dict:
        """Build a WSGI environ dict for the given request parameters."""
        import io
        import json as json_lib

        body = b""
        if data:
            from urllib.parse import urlencode
            body = urlencode(data).encode("utf-8")
            if content_type is None:
                content_type = "application/x-www-form-urlencoded"
        elif json_data is not None:
            body = json_lib.dumps(json_data).encode("utf-8")
            if content_type is None:
                content_type = "application/json"

        if content_type is None:
            content_type = "text/html; charset=utf-8"

        # Split path and query string
        if "?" in path:
            path_info, query_string = path.split("?", 1)
        else:
            path_info = path
            query_string = ""

        environ = {
            "REQUEST_METHOD": method.upper(),
            "SCRIPT_NAME": "",
            "PATH_INFO": path_info,
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
            "CONTENT_TYPE": content_type,
            "CONTENT_LENGTH": str(len(body)),
        }

        if headers:
            for key, value in headers.items():
                key_upper = key.upper().replace("-", "_")
                if key_upper not in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                    environ[f"HTTP_{key_upper}"] = value

        return environ

    def _request(self, method: str, path: str, **kwargs) -> "TestResponse":
        """Make a request and return a TestResponse."""
        environ = self._make_environ(method, path, **kwargs)
        response_started = []
        response_headers = []

        def start_response(status, headers):
            response_started.append(status)
            response_headers.append(headers)

        result = self.app(environ, start_response)

        # Collect response body
        body_parts = []
        for part in result:
            if isinstance(part, str):
                body_parts.append(part.encode("utf-8"))
            elif isinstance(part, bytes):
                body_parts.append(part)
        body = b"".join(body_parts)

        status_code = int(response_started[0].split()[0]) if response_started else 500
        headers = response_headers[0] if response_headers else []

        return TestResponse(body, status_code, headers)

    def get(self, path: str, **kwargs) -> "TestResponse":
        """Make a GET request."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> "TestResponse":
        """Make a POST request."""
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> "TestResponse":
        """Make a PUT request."""
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> "TestResponse":
        """Make a DELETE request."""
        return self._request("DELETE", path, **kwargs)

    def patch(self, path: str, **kwargs) -> "TestResponse":
        """Make a PATCH request."""
        return self._request("PATCH", path, **kwargs)

    def head(self, path: str, **kwargs) -> "TestResponse":
        """Make a HEAD request."""
        return self._request("HEAD", path, **kwargs)

    def options(self, path: str, **kwargs) -> "TestResponse":
        """Make an OPTIONS request."""
        return self._request("OPTIONS", path, **kwargs)


class TestResponse:
    """A response object returned by the TestClient.

    Provides easy access to the response body, status code, and headers
    for making assertions in tests.
    """

    def __init__(self, data: bytes, status_code: int, headers: list):
        self.data = data
        self.status_code = status_code
        self.headers = headers

    @property
    def text(self) -> str:
        """The response body as a string."""
        return self.data.decode("utf-8", errors="replace")

    def get_json(self) -> t.Any:
        """Parse the response body as JSON."""
        import json
        return json.loads(self.text)

    def get_header(self, name: str) -> t.Optional[str]:
        """Get a response header by name (case-insensitive)."""
        name_lower = name.lower()
        for key, value in self.headers:
            if key.lower() == name_lower:
                return value
        return None

    def __repr__(self):
        return f"<TestResponse {self.status_code} [{len(self.data)} bytes]>"
