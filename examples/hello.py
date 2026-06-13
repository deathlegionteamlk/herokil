"""
herokil Hello World Example
----------------------------

A minimal application demonstrating the core features of the
herokil web framework.

Run with::

    python hello.py
"""

from herokil import Herokil, jsonify, redirect, render_template_string, abort

app = Herokil(__name__)
app.secret_key = "dev-secret-key-change-in-production"


# ── Basic routes ───────────────────────────────────────────────────────

@app.route("/")
def index():
    """Home page with links to all demo routes."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>herokil - Hello World</title></head>
    <body>
        <h1>Welcome to herokil!</h1>
        <p>A lightweight Python web framework by <strong>Death Legion Team</strong>.</p>
        <h2>Demo Routes</h2>
        <ul>
            <li><a href="/hello">Hello World</a></li>
            <li><a href="/hello/alice">Hello, Alice!</a></li>
            <li><a href="/json">JSON Response</a></li>
            <li><a href="/template">Template Rendering</a></li>
            <li><a href="/redirect">Redirect Demo</a></li>
            <li><a href="/error">Error Handler Demo</a></li>
            <li><a href="/user/42">URL Parameter (int)</a></li>
        </ul>
    </body>
    </html>
    """


@app.route("/hello")
def hello():
    """Simple hello world route."""
    return "Hello, World!"


@app.route("/hello/<name>")
def hello_name(name):
    """Route with a string URL parameter."""
    return f"Hello, {name}!"


@app.route("/user/<int:id>")
def user(id):
    """Route with an integer URL parameter."""
    return f"User ID: {id}"


# ── JSON responses ─────────────────────────────────────────────────────

@app.route("/json")
def json_route():
    """Return a JSON response."""
    return jsonify(
        framework="herokil",
        version="1.0.0",
        author="Death Legion Team",
        features=[
            "URL routing with decorators",
            "Request and Response objects",
            "Template rendering",
            "Blueprints for modular apps",
            "Session support",
            "JSON responses",
            "Test client",
        ],
    )


# ── Template rendering ─────────────────────────────────────────────────

@app.route("/template")
def template_demo():
    """Render a template string with context variables."""
    return render_template_string(
        """
        <!DOCTYPE html>
        <html>
        <head><title>herokil Template Demo</title></head>
        <body>
            <h1>Template Rendering Demo</h1>
            <p>Hello, <strong>{{ name }}</strong>!</p>
            <p>Your items:</p>
            <ul>
                {% for item in items %}
                <li>{{ item }}</li>
                {% endfor %}
            </ul>
        </body>
        </html>
        """,
        name="Developer",
        items=["Routing", "Templates", "JSON", "Sessions"],
    )


# ── Redirects ──────────────────────────────────────────────────────────

@app.route("/redirect")
def redirect_demo():
    """Demonstrate redirect functionality."""
    return redirect("/")


# ── Error handling ─────────────────────────────────────────────────────

@app.route("/error")
def error_demo():
    """Trigger a 404 error using abort()."""
    abort(404)


@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 error page."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>404 - Page Not Found</title></head>
    <body>
        <h1>404 - Page Not Found</h1>
        <p>The page you're looking for doesn't exist.</p>
        <a href="/">Go home</a>
    </body>
    </html>
    """, 404


# ── POST handling ──────────────────────────────────────────────────────

@app.route("/submit", methods=["GET", "POST"])
def submit():
    """Handle both GET and POST requests."""
    from herokil.ctx import request as req
    if req.method == "POST":
        name = req.form.get("name", "Unknown")
        return f"Submitted: {name}"
    return """
    <form method="POST">
        <input name="name" placeholder="Your name">
        <button type="submit">Submit</button>
    </form>
    """


# ── Run the server ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("  _    _           _       _ _ _")
    print(" | |  | |         | |     | | | |")
    print(" | |__| | __ _  __| | __ _| | | |__   __ _ ___")
    print(" |  __  |/ _` |/ _` |/ _` | | | '_ \\ / _` / __|")
    print(" | |  | | (_| | (_| | (_| | | | |_) | (_| \\__ \\")
    print(" |_|  |_|\\__,_|\\__,_|\\__,_|_|_|_.__/ \\__,_|___/")
    print()
    print(" A lightweight Python web framework by Death Legion Team")
    print()
    app.run(debug=True)
