"""
herokil.cli - Command-line interface for the herokil framework.

Provides the ``herokil`` command with subcommands for creating new
projects, running the development server, and running tests.
"""

import argparse
import os
import sys
import subprocess


def create_project(name: str):
    """Create a new herokil project scaffold.

    Generates a minimal project structure with an app file,
    a templates directory, and a static directory.
    """
    base = os.path.join(os.getcwd(), name)
    os.makedirs(base, exist_ok=True)
    os.makedirs(os.path.join(base, "templates"), exist_ok=True)
    os.makedirs(os.path.join(base, "static"), exist_ok=True)

    # Create app.py
    app_code = f'''"""
{name} - A herokil web application.
"""

from herokil import Herokil, render_template

app = Herokil(__name__)
app.debug(True)


@app.route("/")
def index():
    return render_template("index.html", name="{name}")


@app.route("/hello/<name>")
def hello(name):
    return f"Hello, {{name}}!"


if __name__ == "__main__":
    app.run(debug=True)
'''
    with open(os.path.join(base, "app.py"), "w") as f:
        f.write(app_code)

    # Create a basic template
    template_code = '''<!DOCTYPE html>
<html>
<head>
    <title>{{ name }}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>Welcome to {{ name }}!</h1>
    <p>This is a <a href="https://github.com/death-legion/herokil">herokil</a> application.</p>
</body>
</html>
'''
    with open(os.path.join(base, "templates", "index.html"), "w") as f:
        f.write(template_code)

    # Create a basic CSS file
    css_code = '''/* herokil project styles */
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    max-width: 800px;
    margin: 2em auto;
    padding: 0 1em;
    color: #333;
}

h1 { color: #2563eb; }
a { color: #2563eb; }
'''
    with open(os.path.join(base, "static", "style.css"), "w") as f:
        f.write(css_code)

    # Create requirements.txt
    with open(os.path.join(base, "requirements.txt"), "w") as f:
        f.write("herokil>=1.0.0\n")

    print(f"  Created project: {name}/")
    print(f"  Run it with:")
    print(f"    cd {name}")
    print(f"    python app.py")


def run_server(app_path: str = "app:app", host: str = "127.0.0.1", port: int = 5000, debug: bool = True):
    """Run the development server for the given app.

    Args:
        app_path: The import path to the app (e.g. 'app:app').
        host: Hostname to bind to.
        port: Port to listen on.
        debug: Enable debug mode.
    """
    module_path, app_name = app_path.split(":")
    import importlib
    module = importlib.import_module(module_path)
    app = getattr(module, app_name)
    app.run(host=host, port=port, debug=debug)


def main():
    """Entry point for the herokil CLI."""
    parser = argparse.ArgumentParser(
        prog="herokil",
        description="herokil - A lightweight Python web framework by Death Legion Team",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # new command
    new_parser = subparsers.add_parser("new", help="Create a new herokil project")
    new_parser.add_argument("name", help="Project name")

    # run command
    run_parser = subparsers.add_parser("run", help="Run the development server")
    run_parser.add_argument("app", nargs="?", default="app:app", help="App path (default: app:app)")
    run_parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    run_parser.add_argument("--port", "-p", type=int, default=5000, help="Port (default: 5000)")
    run_parser.add_argument("--no-debug", action="store_true", help="Disable debug mode")

    # version command
    version_parser = subparsers.add_parser("version", help="Show herokil version")

    args = parser.parse_args()

    if args.command == "new":
        create_project(args.name)
    elif args.command == "run":
        run_server(
            app_path=args.app,
            host=args.host,
            port=args.port,
            debug=not args.no_debug,
        )
    elif args.command == "version":
        from herokil import __version__
        print(f"herokil {__version__}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
