from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from app.services.notification_service import NotificationService

notif_bp = Blueprint("notifications", __name__)

@notif_bp.post("/run-late-check")
@jwt_required()
def run_late_check():
    role = (get_jwt() or {}).get("role")
    if role != "admin":
        return jsonify({"success": False, "message": "Yetkisiz"}), 403

    NotificationService.check_and_notify_late_returns()
    return jsonify({"success": True, "message": "Late check çalıştırıldı"})
