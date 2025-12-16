from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.services.book_service import BookService
from app.utils.decorators import role_required

book_bp = Blueprint("books", __name__)

@book_bp.get("/")
def list_books():
    books = BookService.list_books()
    return jsonify({"success": True, "data": [
        {"id": b.id, "title": b.title, "author": b.author, "isbn": b.isbn,
         "total_copies": b.total_copies, "available_copies": b.available_copies}
        for b in books
    ]})

@book_bp.get("/<int:book_id>")
def get_book(book_id):
    try:
        b = BookService.get_book(book_id)
        return jsonify({"success": True, "data": {
            "id": b.id, "title": b.title, "author": b.author, "isbn": b.isbn,
            "total_copies": b.total_copies, "available_copies": b.available_copies
        }})
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 404

@book_bp.post("/")
@jwt_required()
@role_required("admin")
def create_book():
    data = request.get_json() or {}
    try:
        b = BookService.create_book(data)
        return jsonify({"success": True, "id": b.id}), 201
    except KeyError:
        return jsonify({"success": False, "message": "title ve author zorunlu"}), 400
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

@book_bp.put("/<int:book_id>")
@jwt_required()
@role_required("admin")
def update_book(book_id):
    data = request.get_json() or {}
    try:
        b = BookService.update_book(book_id, data)
        return jsonify({"success": True, "data": {"id": b.id}})
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 404

@book_bp.delete("/<int:book_id>")
@jwt_required()
@role_required("admin")
def delete_book(book_id):
    try:
        BookService.delete_book(book_id)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 404
