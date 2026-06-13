"""
herokil.helpers - Utility functions for URL building, flash messages, etc.

These helpers work within the request context and are designed to feel
familiar to users coming from Flask.
"""

import typing as t


def url_for(endpoint: str, **values) -> str:
    """Build a URL for the given endpoint with the provided values.

    This function looks up the current application's URL map to generate
    a URL for the named endpoint, substituting any path parameters from
    the provided keyword arguments.

    Args:
        endpoint: The endpoint name (usually the view function name).
        **values: Variable parts of the URL rule.

    Returns:
        The generated URL string.

    Example::

        from herokil import url_for

        @app.route("/user/<name>")
        def profile(name):
            return f"Hello, {name}!"

        @app.route("/link")
        def link():
            return redirect(url_for("profile", name="alice"))
    """
    # Import here to avoid circular imports
    from herokil.ctx import _ctx

    app = getattr(_ctx, "_app", None)
    if app is None:
        raise RuntimeError("Working outside of application context.")

    url = app.url_map.url_for(endpoint, **values)
    if url is None:
        raise ValueError(f"Could not build URL for endpoint {endpoint!r} with values {values}.")
    return url


# ── Flash messages ─────────────────────────────────────────────────────

_flash_storage = threading_local = None


def _get_flash_storage():
    """Get the thread-local flash message storage."""
    global _flash_storage
    if _flash_storage is None:
        import threading
        _flash_storage = threading.local()
    return _flash_storage


def flash(message: str, category: str = "message"):
    """Add a flash message to be displayed on the next request.

    Flash messages are stored in the session and are typically used
    to show one-time notifications after a redirect.

    Args:
        message: The message text.
        category: A category label (e.g. 'success', 'error', 'warning').

    Example::

        @app.route("/login", methods=["POST"])
        def login():
            if check_credentials():
                flash("Logged in successfully!", "success")
                return redirect(url_for("dashboard"))
            flash("Invalid credentials.", "error")
            return redirect(url_for("login"))
    """
    from herokil.ctx import session
    try:
        flashes = session.get("_flashes", [])
    except RuntimeError:
        # Outside request context, use thread-local fallback
        storage = _get_flash_storage()
        flashes = getattr(storage, "flashes", [])

    flashes.append((category, message))

    try:
        session["_flashes"] = flashes
    except RuntimeError:
        storage = _get_flash_storage()
        storage.flashes = flashes


def get_flashed_messages(with_categories: bool = False, category_filter: t.Iterable = ()) -> t.List:
    """Retrieve flash messages, removing them from the session.

    Args:
        with_categories: If True, return (category, message) tuples
            instead of just messages.
        category_filter: If provided, only return messages in these
            categories.

    Returns:
        A list of flash messages.

    Example::

        {% for msg in get_flashed_messages() %}
            <p>{{ msg }}</p>
        {% endfor %}
    """
    from herokil.ctx import session

    try:
        flashes = session.pop("_flashes", []) if hasattr(session, "pop") else session.get("_flashes", [])
    except (RuntimeError, AttributeError):
        storage = _get_flash_storage()
        flashes = getattr(storage, "flashes", [])
        storage.flashes = []

    if category_filter:
        category_filter = set(category_filter)
        flashes = [f for f in flashes if f[0] in category_filter]

    if with_categories:
        return flashes
    return [msg for _, msg in flashes]
