"""
herokil.exceptions - HTTP exception classes and abort utility.

Provides standard HTTP error responses and a convenient abort()
function to immediately stop request processing.
"""


class HTTPException(Exception):
    """Base class for all HTTP exceptions.

    Attributes:
        code: HTTP status code (e.g. 404).
        description: Human-readable description of the error.
    """

    code = 500
    description = "An internal server error occurred."

    def __init__(self, description=None, response=None):
        super().__init__()
        if description is not None:
            self.description = description
        self.response = response

    def get_body(self, environ=None, scope=None):
        """Return the HTML body for this error response."""
        return (
            f"<!DOCTYPE html>\n"
            f"<html>\n"
            f"<head><title>{self.code} {self.name}</title></head>\n"
            f"<body>\n"
            f"<h1>{self.code} {self.name}</h1>\n"
            f"<p>{self.description}</p>\n"
            f"</body>\n"
            f"</html>"
        )

    def get_headers(self, environ=None, scope=None):
        """Return the HTTP headers for this error response."""
        return [("Content-Type", "text/html; charset=utf-8")]

    @property
    def name(self):
        """Return the status name for this exception's code."""
        from http import HTTPStatus

        try:
            return HTTPStatus(self.code).phrase
        except ValueError:
            return "Unknown Error"

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.code}: {self.description}>"


class BadRequest(HTTPException):
    """400 Bad Request - The server cannot process the request."""

    code = 400
    description = "The browser (or proxy) sent a request that this server could not understand."


class Unauthorized(HTTPException):
    """401 Unauthorized - Authentication is required."""

    code = 401
    description = "The server could not verify that you are authorized to access the URL requested."


class Forbidden(HTTPException):
    """403 Forbidden - You don't have permission to access this resource."""

    code = 403
    description = "You don't have the permission to access the requested resource."


class NotFound(HTTPException):
    """404 Not Found - The requested resource was not found."""

    code = 404
    description = "The requested URL was not found on the server."


class MethodNotAllowed(HTTPException):
    """405 Method Not Allowed - The HTTP method is not allowed for this URL."""

    code = 405
    description = "The method is not allowed for the requested URL."


class InternalServerError(HTTPException):
    """500 Internal Server Error - An unexpected error occurred."""

    code = 500
    description = "An unexpected error occurred on the server."


def abort(code, description=None, response=None):
    """Immediately abort request processing and raise an HTTPException.

    Args:
        code: HTTP status code to raise.
        description: Optional description override.
        response: Optional response object.

    Raises:
        HTTPException: Always raised with the given status code.

    Example::

        from herokil import abort

        @app.route("/admin")
        def admin():
            if not is_admin():
                abort(403)
            return "Welcome, admin!"
    """
    exc_map = {
        400: BadRequest,
        401: Unauthorized,
        403: Forbidden,
        404: NotFound,
        405: MethodNotAllowed,
        500: InternalServerError,
    }
    cls = exc_map.get(code, HTTPException)
    exc = cls(description=description, response=response)
    exc.code = code
    raise exc
