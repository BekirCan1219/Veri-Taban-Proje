from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.services.borrow_service import BorrowService
from app.repositories.borrow_repo import BorrowRepo

borrow_bp = Blueprint("borrow", __name__)

@borrow_bp.post("/")
@jwt_required()
def borrow_book():
    data = request.get_json() or {}
    try:
        book_id = int(data["book_id"])
        days = int(data.get("days", 14))
        b = BorrowService.borrow_book(book_id, days)
        return jsonify({"success": True, "borrow_id": b.id, "due_date": str(b.due_date)}), 201
    except KeyError:
        return jsonify({"success": False, "message": "book_id zorunlu"}), 400
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

@borrow_bp.post("/return/<int:borrow_id>")
@jwt_required()
def return_book(borrow_id):
    try:
        b = BorrowService.return_book(borrow_id)
        return jsonify({"success": True, "returned_at": str(b.returned_at)})
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

@borrow_bp.get("/my")
@jwt_required()
def my_borrows():
    user_id = int(get_jwt_identity())
    borrows = BorrowRepo.list_by_user(user_id)
    return jsonify({"success": True, "data": [
        {
            "id": x.id,
            "book_id": x.book_id,
            "book_title": x.book.title if x.book else None,
            "borrowed_at": str(x.borrowed_at),
            "due_date": str(x.due_date),
            "returned_at": str(x.returned_at) if x.returned_at else None,
            "status": x.status
        } for x in borrows
    ]})

@borrow_bp.get("/")
@jwt_required()
def all_borrows_admin_only():
    # basit admin kontrolü: claim
    role = (get_jwt() or {}).get("role")
    if role != "admin":
        return jsonify({"success": False, "message": "Yetkisiz"}), 403

    borrows = BorrowRepo.list_all()
    return jsonify({"success": True, "data": [
        {
            "id": x.id,
            "user": x.user.username if x.user else None,
            "book": x.book.title if x.book else None,
            "due_date": str(x.due_date),
            "returned_at": str(x.returned_at) if x.returned_at else None,
            "status": x.status
        } for x in borrows
    ]})
