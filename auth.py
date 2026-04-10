
"""Authentication and authorization helpers."""
from __future__ import annotations

from functools import wraps
from typing import Callable, Any

from flask import session, jsonify, redirect, url_for, request


def current_user_id() -> str | None:
    return session.get("user_id")


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Authentication required"}), 401
            return redirect(url_for("login_page"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles: str):
    """Require one of the given roles for a view."""
    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any):
            user = session.get("user")
            if not user or user.get("role") not in roles:
                if request.path.startswith("/api/"):
                    return jsonify({"success": False, "message": "Access denied"}), 403
                return redirect(url_for("login_page"))
            return view(*args, **kwargs)
        return wrapped
    return decorator
