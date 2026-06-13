<p align="center">
  <img src="https://img.shields.io/pypi/v/herokil?color=2563eb&label=pypi&style=for-the-badge" alt="PyPI">
  <img src="https://img.shields.io/pypi/pyversions/herokil?style=for-the-badge&color=2563eb" alt="Python Versions">
  <img src="https://img.shields.io/pypi/l/herokil?style=for-the-badge&color=2563eb" alt="License">
  <img src="https://img.shields.io/github/stars/death-legion/herokil?style=for-the-badge&color=2563eb" alt="Stars">
</p>

<h1 align="center">⚡ herokil</h1>

<p align="center">
  <strong>A lightweight Python web framework by Death Legion Team</strong><br>
  Simple for beginners. Flexible for growth. Fast for production.
</p>

<p align="center">
  <a href="#installation">Install</a> ·
  <a href="#quickstart">Quickstart</a> ·
  <a href="#features">Features</a> ·
  <a href="#documentation">Docs</a> ·
  <a href="#contributing">Contribute</a>
</p>

---

**herokil** is a micro web framework written in Python that makes it easy to build web applications fast — from tiny scripts to growing projects. It gives you the essentials — routing, request/response handling, templates, sessions, and blueprints — without forcing a heavy project structure or too many opinions.

If you've used Flask, you'll feel right at home. If you're new to Python web development, herokil's minimal API makes it the perfect starting point.

## ✨ Why herokil?

| Feature | herokil | Flask | Django |
|---|---|---|---|
| Zero dependencies | ✅ | ❌ | ❌ |
| Decorator-based routing | ✅ | ✅ | ❌ |
| Built-in template engine | ✅ | ✅ | ✅ |
| Blueprint / modular apps | ✅ | ✅ | Apps |
| Session support | ✅ | ✅ | ✅ |
| Test client included | ✅ | ✅ | ✅ |
| Lightweight core | ✅ | ✅ | ❌ |
| CLI scaffolding | ✅ | ❌ | ✅ |

## 📦 Installation

```bash
pip install herokil
```

With all optional dependencies:

```bash
pip install herokil[all]
```

For development:

```bash
pip install herokil[dev]
```

## 🚀 Quickstart

### Hello World in 6 Lines

```python
from herokil import Herokil

app = Herokil(__name__)

@app.route("/")
def hello():
    return "Hello, World!"

if __name__ == "__main__":
    app.run()
```

Save as `app.py` and run:

```bash
python app.py
# * Running on http://127.0.0.1:5000/
```

That's it! You have a working web application.

### URL Parameters

```python
@app.route("/user/<name>")
def profile(name):
    return f"Hello, {name}!"

@app.route("/post/<int:id>")
def post(id):
    return f"Post #{id}"
```

### JSON Responses

```python
from herokil import jsonify

@app.route("/api/status")
def status():
    return jsonify(online=True, version="1.0.0")
```

### Templates

```python
from herokil import render_template

@app.route("/page")
def page():
    return render_template("page.html", title="My Page")
```

### Redirects

```python
from herokil import redirect

@app.route("/old")
def old_route():
    return redirect("/new")
```

### Blueprints (Modular Apps)

```python
from herokil import Blueprint

api = Blueprint("api", __name__, url_prefix="/api")

@api.route("/users")
def list_users():
    return jsonify(users=["alice", "bob"])

# Register on your app
app.register_blueprint(api)
```

### Error Handling

```python
from herokil import abort

@app.route("/admin")
def admin():
    abort(403)

@app.errorhandler(404)
def not_found(e):
    return "Page not found!", 404
```

### Request Access

```python
from herokil.ctx import request

@app.route("/search")
def search():
    query = request.args.get("q", "")
    return f"Searching for: {query}"

@app.route("/submit", methods=["POST"])
def submit():
    name = request.form.get("name")
    data = request.json
    return jsonify(received=True)
```

### Sessions

```python
app = Herokil(__name__, secret_key="your-secret-key")

@app.route("/login")
def login():
    from herokil.ctx import session
    session["user"] = "alice"
    return "Logged in!"

@app.route("/profile")
def profile():
    from herokil.ctx import session
    return f"Hello, {session.get('user', 'guest')}"
```

## 🎯 Features

### Core

- **Decorator-based routing** — Register routes with `@app.route()` just like Flask
- **URL parameters** — `<name>`, `<int:id>`, `<float:price>`, `<path:filepath>`, `<uuid:id>`
- **HTTP methods** — `methods=["GET", "POST"]` per route
- **Request object** — Full access to args, form data, JSON, headers, cookies, files
- **Response object** — Flexible responses with custom status, headers, and cookies
- **JSON support** — `jsonify()` helper for API endpoints
- **Redirects** — `redirect()` with configurable status codes
- **Error handling** — `abort()` and `@app.errorhandler()` decorators
- **Before/after hooks** — `@app.before_request()`, `@app.after_request()`, `@app.teardown_request()`

### Templates

- **Jinja2 support** — Full Jinja2 when installed (`pip install herokil[jinja2]`)
- **Built-in engine** — Simple `{{ var }}`, `{% if %}`, `{% for %}` syntax with zero dependencies
- **`render_template()`** — Render template files from a templates directory
- **`render_template_string()`** — Render inline template strings

### Modularity

- **Blueprints** — Group routes into reusable modules with URL prefixes
- **Nested registration** — Multiple blueprints on one app
- **Blueprint hooks** — Per-blueprint before/after request handlers

### Sessions

- **Secure cookie sessions** — HMAC-SHA256 signed session cookies
- **Secret key** — Configurable via `Herokil(__name__, secret_key="...")`
- **Dict interface** — Sessions behave like regular Python dicts

### Development

- **Built-in dev server** — `app.run()` starts a server immediately
- **Debug mode** — Auto-reload and detailed error pages
- **Werkzeug support** — Enhanced dev server when Werkzeug is installed
- **Test client** — `app.test_client()` for unit testing without HTTP
- **CLI tool** — `herokil new projectname` scaffolds a new project

### Static Files

- **Auto-serving** — Static files served from `/static/` in development
- **Configurable paths** — Custom `static_folder` and `static_url_path`

## 📖 Documentation

### Creating a New Project

```bash
pip install herokil
herokil new myapp
cd myapp
python app.py
```

### Running Tests

```bash
pip install herokil[dev]
pytest
```

### Running the Example App

```bash
pip install -e .
python examples/hello.py
```

### API Reference

#### `Herokil(import_name, ...)`

Create a new application instance.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `import_name` | `str` | required | Usually `__name__` |
| `static_url_path` | `str` | `"/static"` | URL prefix for static files |
| `static_folder` | `str` | `"static"` | Path to static files |
| `template_folder` | `str` | `"templates"` | Path to templates |
| `secret_key` | `str` | `None` | Secret key for sessions |

#### `@app.route(rule, **options)`

Register a route. Options: `methods`, `endpoint`.

#### `app.run(host, port, debug)`

Start the development server.

#### `@app.before_request`

Run a function before each request.

#### `@app.after_request`

Run a function after each request (receives and must return Response).

#### `@app.errorhandler(code)`

Handle a specific HTTP error code.

#### `Blueprint(name, import_name, url_prefix)`

Create a modular group of routes.

#### `Request`

Properties: `method`, `path`, `args`, `form`, `json`, `files`, `headers`, `cookies`, `remote_addr`, `user_agent`, `content_type`, `is_json`.

#### `Response(body, status, headers, content_type)`

Methods: `set_cookie()`, `delete_cookie()`, `set_header()`, `get_data()`, `set_data()`.

#### Helpers

- `jsonify(**kwargs)` → JSON Response
- `redirect(url, code=302)` → Redirect Response
- `abort(code)` → Raise HTTPException
- `render_template(name, **ctx)` → Rendered string
- `render_template_string(source, **ctx)` → Rendered string
- `url_for(endpoint, **values)` → URL string
- `flash(message, category)` → Set flash message
- `get_flashed_messages(with_categories)` → List of messages

## 🏗️ Project Structure

```
herokil/
├── herokil/
│   ├── __init__.py       # Public API exports
│   ├── app.py            # Core Herokil class + TestClient
│   ├── routing.py        # URL routing engine
│   ├── request.py        # Request object
│   ├── response.py       # Response object + helpers
│   ├── template.py       # Template rendering (Jinja2 + fallback)
│   ├── blueprints.py     # Blueprint support
│   ├── sessions.py       # Secure cookie sessions
│   ├── ctx.py            # Request context proxies
│   ├── helpers.py        # url_for, flash, etc.
│   ├── static.py         # Static file serving
│   ├── exceptions.py     # HTTP exceptions + abort()
│   └── cli.py            # Command-line interface
├── tests/
│   ├── test_app.py
│   ├── test_routing.py
│   ├── test_request.py
│   ├── test_response.py
│   ├── test_template.py
│   ├── test_blueprints.py
│   └── test_sessions.py
├── examples/
│   └── hello.py
├── docs/
├── pyproject.toml
├── LICENSE
├── MANIFEST.in
└── README.md
```

## 🧪 Running Tests

```bash
# Install dev dependencies
pip install herokil[dev]

# Run all tests
pytest

# Run with coverage
pytest --cov=herokil --cov-report=term-missing

# Run specific test file
pytest tests/test_routing.py
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Write** your code and tests
4. **Run** the test suite: `pytest`
5. **Commit** your changes: `git commit -m "Add amazing feature"`
6. **Push** to your branch: `git push origin feature/amazing-feature`
7. **Open** a Pull Request

### Development Setup

```bash
git clone https://github.com/death-legion/herokil.git
cd herokil
pip install -e ".[dev]"
pytest
```

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

## 🏴 Credits

**herokil** is built and maintained by **Death Legion Team**.

Inspired by [Flask](https://flask.palletsprojects.com/), [Bottle](https://bottlepy.org/), and [Werkzeug](https://werkzeug.palletsprojects.com/).

---

<p align="center">
  <strong>herokil</strong> — Build fast. Grow smart. Ship it. ⚡
</p>
