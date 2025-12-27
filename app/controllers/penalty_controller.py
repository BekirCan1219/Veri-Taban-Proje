# app/controllers/penalty_controller.py

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from app.models.penalty import Penalty
from app.models.borrow import Borrow

penalty_bp = Blueprint("penalties", __name__, url_prefix="/penalties")


def _jwt_user():
    claims = get_jwt()
    return claims.get("user_id"), claims.get("role")


@penalty_bp.get("/my")
@jwt_required()
def my_penalties():
    user_id, _role = _jwt_user()
    if not user_id:
        return jsonify({"success": False, "message": "JWT içinde user_id yok"}), 400

    # borrow üzerinden user filtrele
    rows = (
        Penalty.query
        .join(Borrow, Penalty.borrow_id == Borrow.id)
        .filter(Borrow.user_id == user_id)
        .order_by(Penalty.id.desc())
        .all()
    )

    return jsonify({
        "success": True,
        "data": [
            {
                "id": p.id,
                "borrow_id": p.borrow_id,
                "days_overdue": p.days_overdue,
                "daily_fee": float(p.daily_fee),
                "amount": float(p.amount),
                "is_paid": bool(p.is_paid),
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in rows
        ]
    })


@penalty_bp.get("/all")
@jwt_required()
def all_penalties():
    _user_id, role = _jwt_user()
    if role != "admin":
        return jsonify({"success": False, "message": "Forbidden"}), 403

    rows = Penalty.query.order_by(Penalty.id.desc()).all()
    return jsonify({
        "success": True,
        "data": [
            {
                "id": p.id,
                "borrow_id": p.borrow_id,
                "days_overdue": p.days_overdue,
                "daily_fee": float(p.daily_fee),
                "amount": float(p.amount),
                "is_paid": bool(p.is_paid),
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in rows
        ]
    })


@penalty_bp.post("/pay/<int:penalty_id>")
@jwt_required()
def pay_penalty(penalty_id: int):
    user_id, role = _jwt_user()
    if not user_id:
        return jsonify({"success": False, "message": "JWT içinde user_id yok"}), 400

    p = Penalty.query.get_or_404(penalty_id)

    # admin değilse, sadece kendi penalty'sini ödeyebilir (borrow üzerinden kontrol)
    if role != "admin":
        b = Borrow.query.get(p.borrow_id)
        if not b or b.user_id != user_id:
            return jsonify({"success": False, "message": "Forbidden"}), 403

    if p.is_paid:
        return jsonify({"success": False, "message": "Zaten ödendi"}), 400

    p.is_paid = True
    from app.extensions import db
    db.session.commit()

    return jsonify({"success": True})
