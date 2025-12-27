from functools import wraps
from flask import session, redirect, url_for, jsonify, request

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            # API ise JSON dön
            if request.path.startswith("/api") or request.is_json:
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        if session.get("role") != "admin":
            return jsonify({"error": "Forbidden"}), 403
        return view(*args, **kwargs)
    return wrapped
