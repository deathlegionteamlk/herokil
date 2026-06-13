"""
herokil.static - Static file serving for development.

Serves files from a configured static directory. This is intended
for development only; in production, use a dedicated web server
or CDN for static assets.
"""

import os
import mimetypes
import typing as t
from herokil.response import Response


def serve_static(filepath: str, static_folder: str = "static") -> t.Optional[Response]:
    """Serve a static file from the given directory.

    Args:
        filepath: The relative path to the file within the static folder.
        static_folder: The root directory for static files.

    Returns:
        A Response with the file contents, or None if the file is not found.

    Security:
        Path traversal is prevented by resolving the absolute path
        and verifying it remains within the static folder.
    """
    # Resolve absolute paths to prevent directory traversal
    static_folder = os.path.abspath(static_folder)
    target = os.path.abspath(os.path.join(static_folder, filepath))

    # Ensure the resolved path is within the static folder
    if not target.startswith(static_folder):
        return None

    if not os.path.isfile(target):
        return None

    # Determine content type
    content_type, _ = mimetypes.guess_type(target)
    if content_type is None:
        content_type = "application/octet-stream"

    try:
        with open(target, "rb") as f:
            data = f.read()
        return Response(data, content_type=content_type)
    except (IOError, OSError):
        return None
