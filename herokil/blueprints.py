"""
herokil.blueprints - Blueprint support for modular application organization.

Blueprints let you group related routes, templates, and static files
together, then register them on an application. This makes large
applications easier to organize and allows reuse of components across
projects.
"""

import typing as t
from herokil.routing import Map, Rule


class Blueprint:
    """A blueprint defines a group of related routes and handlers.

    Instead of registering routes directly on the app, you create a
    Blueprint, add routes to it, then register the blueprint on the
    app with an optional URL prefix.

    Args:
        name: The blueprint name (must be unique per app).
        import_name: The import name (usually ``__name__``).
        url_prefix: Optional prefix applied to all routes in this blueprint.
        static_folder: Optional static file folder for this blueprint.
        template_folder: Optional template folder for this blueprint.

    Example::

        from herokil import Blueprint

        api = Blueprint("api", __name__, url_prefix="/api")

        @api.route("/users")
        def list_users():
            return jsonify(users=["alice", "bob"])

        # Later, in your app:
        app.register_blueprint(api)
    """

    def __init__(
        self,
        name: str,
        import_name: str,
        url_prefix: t.Optional[str] = None,
        static_folder: t.Optional[str] = None,
        template_folder: t.Optional[str] = None,
    ):
        self.name = name
        self.import_name = import_name
        self.url_prefix = (url_prefix or "").rstrip("/")
        self.static_folder = static_folder
        self.template_folder = template_folder

        self._rules: t.List[Rule] = []
        self._view_functions: t.Dict[str, t.Callable] = {}
        self._before_request_funcs: t.List[t.Callable] = []
        self._after_request_funcs: t.List[t.Callable] = []
        self._error_handlers: t.Dict[int, t.Callable] = {}

    def route(self, rule: str, **options):
        """Register a route on this blueprint.

        Works exactly like :meth:`Herokil.route`, but the route is
        stored in the blueprint until :meth:`register` is called.

        Args:
            rule: The URL rule string.
            **options: Options passed to Rule (e.g. methods=['POST']).
        """
        def decorator(func: t.Callable) -> t.Callable:
            endpoint = options.pop("endpoint", func.__name__)
            methods = options.pop("methods", None)
            rule_obj = Rule(rule, endpoint, methods=methods, view_func=func)
            self._rules.append(rule_obj)
            self._view_functions[endpoint] = func
            return func
        return decorator

    def before_request(self, func: t.Callable) -> t.Callable:
        """Register a function to run before each request in this blueprint.

        Example::

            @api.before_request
            def check_auth():
                if not is_authenticated():
                    abort(401)
        """
        self._before_request_funcs.append(func)
        return func

    def after_request(self, func: t.Callable) -> t.Callable:
        """Register a function to run after each request in this blueprint.

        The function receives the Response object and must return a Response.
        """
        self._after_request_funcs.append(func)
        return func

    def errorhandler(self, code_or_exception):
        """Register an error handler for this blueprint.

        Args:
            code_or_exception: An HTTP status code or exception class.

        Example::

            @api.errorhandler(404)
            def not_found(e):
                return jsonify(error="Not found"), 404
        """
        def decorator(func: t.Callable) -> t.Callable:
            if isinstance(code_or_exception, int):
                self._error_handlers[code_or_exception] = func
            else:
                self._error_handlers[code_or_exception] = func
            return func
        return decorator

    def register(self, app, url_prefix: t.Optional[str] = None):
        """Register this blueprint on the given application.

        This is called internally by :meth:`Herokil.register_blueprint`.

        Args:
            app: The Herokil application instance.
            url_prefix: Optional override for the blueprint's URL prefix.
        """
        prefix = url_prefix or self.url_prefix

        # Register routes with the prefix
        for rule in self._rules:
            full_rule = prefix + rule.rule if prefix else rule.rule
            # Avoid double slashes
            full_rule = full_rule.replace("//", "/")
            app.add_url_rule(
                full_rule,
                endpoint=f"{self.name}.{rule.endpoint}",
                view_func=rule.view_func,
                methods=rule.methods,
            )

        # Register hooks
        for func in self._before_request_funcs:
            app.before_request(func)

        for func in self._after_request_funcs:
            app.after_request(func)

        # Register error handlers
        for code_or_exc, handler in self._error_handlers.items():
            app.errorhandler(code_or_exc)(handler)
