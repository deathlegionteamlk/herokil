"""
herokil - A lightweight Python web framework by Death Legion Team.

A microframework that feels simple for beginners, yet flexible enough
to grow into bigger applications. Inspired by Flask, built for speed.

Usage::

    from herokil import Herokil

    app = Herokil(__name__)

    @app.route("/")
    def hello():
        return "Hello, World!"

    if __name__ == "__main__":
        app.run()
"""

__version__ = "1.0.0"
__author__ = "Death Legion Team"
__license__ = "MIT"

from herokil.app import Herokil
from herokil.request import Request
from herokil.response import Response, redirect, jsonify
from herokil.blueprints import Blueprint
from herokil.exceptions import (
    HTTPException,
    BadRequest,
    Unauthorized,
    Forbidden,
    NotFound,
    MethodNotAllowed,
    InternalServerError,
    abort,
)
from herokil.template import render_template, render_template_string
from herokil.helpers import url_for, flash, get_flashed_messages
from herokil.ctx import request as request_proxy, session as session_proxy, g as g_proxy

__all__ = [
    "Herokil",
    "Request",
    "Response",
    "Blueprint",
    "redirect",
    "jsonify",
    "HTTPException",
    "BadRequest",
    "Unauthorized",
    "Forbidden",
    "NotFound",
    "MethodNotAllowed",
    "InternalServerError",
    "abort",
    "render_template",
    "render_template_string",
    "url_for",
    "flash",
    "get_flashed_messages",
    "request_proxy",
    "session_proxy",
    "g_proxy",
]
