from flask import Blueprint, request, jsonify,session
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.services.auth_service import AuthService
from app.repositories.user_repo import UserRepo

auth_bp = Blueprint("auth", __name__)

@auth_bp.post("/register", endpoint="auth_register")
def register():
    data = request.get_json() or {}

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not email or not password:
        return jsonify({"success": False, "message": "username/email/password zorunlu"}), 400

    try:
        user = AuthService.register(
            username=username,
            email=email,
            password=password,
            role="user"  # dışarıdan role alma
        )
        return jsonify({"success": True, "id": user.id, "username": user.username, "role": user.role}), 201
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400


@auth_bp.post("/login", endpoint="auth_login")
def login():
    data = request.get_json() or {}
    try:
        token, user = AuthService.login(
            (data.get("username") or "").strip(),
            (data.get("password") or "").strip()
        )
        return jsonify({
            "success": True,
            "access_token": token,
            "user": {"id": user.id, "username": user.username, "role": user.role}
        })
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 401


@auth_bp.get("/me", endpoint="auth_me")
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    user = UserRepo.get_by_id(user_id)

    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": claims.get("role", user.role)
        }
    })

@auth_bp.post("/web/login", endpoint="web_login")
def web_login():
    """
    Web UI için session tabanlı login.
    Body: { "username": "...", "password": "..." }
    Başarılı olursa session["user_id"], session["username"], session["role"] dolar.
    """
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    try:
        # AuthService.login zaten kullanıcıyı doğruluyor
        token, user = AuthService.login(username, password)

        # ✅ SESSION SET
        session.clear()
        session["user_id"] = int(user.id)
        session["username"] = user.username
        session["role"] = user.role

        return jsonify({
            "success": True,
            "message": "Web login başarılı",
            "user": {"id": user.id, "username": user.username, "role": user.role}
        })
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 401


@auth_bp.get("/web/logout", endpoint="web_logout")
def web_logout():
    session.clear()
    return jsonify({"success": True, "message": "Çıkış yapıldı"})
