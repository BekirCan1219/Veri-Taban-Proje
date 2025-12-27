from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, session
from sqlalchemy import func, text

from app.extensions import db
from app.models.book import Book
from app.models.borrow import Borrow
from app.models.penalty import Penalty
from app.models.user import User  # ✅ eklendi (username/email için)

from app.repositories.book_repo import BookRepo
from app.repositories.borrow_repo import BorrowRepo


web_api_bp = Blueprint("web_api", __name__, url_prefix="/web/api")


# -----------------------------
# Helpers
# -----------------------------
def _require_login():
    return bool(session.get("user_id"))


def _require_admin():
    return _require_login() and session.get("role") == "admin"


def _json_error(message, code=400):
    return jsonify({"success": False, "message": message}), code


# -----------------------------
# Books
# -----------------------------
@web_api_bp.get("/books")
def books_list():
    books = BookRepo.list_all()
    return jsonify({"success": True, "data": [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "isbn": getattr(b, "isbn", None),
            "total_copies": getattr(b, "total_copies", 0),
            "available_copies": getattr(b, "available_copies", 0)
        } for b in books
    ]})


@web_api_bp.post("/books")
def books_create():
    if not _require_login():
        return _json_error("Unauthorized", 401)
    if session.get("role") != "admin":
        return _json_error("Yetkisiz (admin gerekli)", 403)

    data = request.get_json() or {}
    try:
        title = (data.get("title") or "").strip()
        author = (data.get("author") or "").strip()
        if not title or not author:
            return _json_error("title ve author zorunlu", 400)

        total = int(data.get("total_copies", 1))
        avail = int(data.get("available_copies", total))
        if total < 1:
            total = 1
        if avail < 0:
            avail = 0
        if avail > total:
            avail = total

        book = Book(
            title=title,
            author=author,
            isbn=(data.get("isbn") or None),
            total_copies=total,
            available_copies=avail
        )
        db.session.add(book)
        db.session.commit()
        return jsonify({"success": True, "id": book.id}), 201

    except Exception as e:
        db.session.rollback()
        return _json_error(str(e), 400)


@web_api_bp.put("/books/<int:book_id>")
def books_update(book_id: int):
    if not _require_login():
        return _json_error("Unauthorized", 401)
    if session.get("role") != "admin":
        return _json_error("Yetkisiz (admin gerekli)", 403)

    data = request.get_json() or {}
    try:
        book = BookRepo.get(book_id)
        if not book:
            return _json_error("Kitap bulunamadı", 404)

        if "title" in data and data["title"] is not None:
            book.title = str(data["title"]).strip()
        if "author" in data and data["author"] is not None:
            book.author = str(data["author"]).strip()
        if "isbn" in data:
            isbn = (data.get("isbn") or "").strip()
            book.isbn = isbn if isbn else None

        if "total_copies" in data and data["total_copies"] is not None:
            book.total_copies = int(data["total_copies"])
        if "available_copies" in data and data["available_copies"] is not None:
            book.available_copies = int(data["available_copies"])

        # tutarlılık
        if book.total_copies < 1:
            book.total_copies = 1
        if book.available_copies < 0:
            book.available_copies = 0
        if book.available_copies > book.total_copies:
            book.available_copies = book.total_copies

        BookRepo.update()
        return jsonify({"success": True, "data": {"id": book.id}})

    except Exception as e:
        db.session.rollback()
        return _json_error(str(e), 400)


@web_api_bp.delete("/books/<int:book_id>")
def books_delete(book_id: int):
    if not _require_login():
        return _json_error("Unauthorized", 401)
    if session.get("role") != "admin":
        return _json_error("Yetkisiz (admin gerekli)", 403)

    try:
        book = BookRepo.get(book_id)
        if not book:
            return _json_error("Kitap bulunamadı", 404)

        active_count = Borrow.query.filter(
            Borrow.book_id == book_id,
            Borrow.returned_at.is_(None)
        ).count()
        if active_count > 0:
            return _json_error("Bu kitap aktif ödünçte. Önce iadeler tamamlanmalı.", 400)

        BookRepo.delete(book)
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return _json_error(str(e), 400)


# -----------------------------
# Borrow
# -----------------------------
@web_api_bp.post("/borrow")
def borrow_create():
    if not _require_login():
        return _json_error("Unauthorized", 401)

    data = request.get_json() or {}
    try:
        uid = int(session["user_id"])
        bid = int(data.get("book_id"))
        days = int(data.get("days", 14))

        row = db.session.execute(
            text("""
                EXEC dbo.sp_borrow_book
                    @user_id = :uid,
                    @book_id = :bid,
                    @days    = :days
            """),
            {"uid": uid, "bid": bid, "days": days}
        ).fetchone()

        db.session.commit()

        return jsonify({
            "success": True,
            "borrow_id": int(row.borrow_id) if row and getattr(row, "borrow_id", None) is not None else None,
            "due_date": str(row.due_date) if row and getattr(row, "due_date", None) is not None else None
        }), 201

    except Exception as e:
        db.session.rollback()
        return _json_error(str(e), 400)


@web_api_bp.get("/borrow/my")
def borrow_my():
    if not _require_login():
        return _json_error("Unauthorized", 401)

    user_id = int(session["user_id"])
    borrows = BorrowRepo.list_by_user(user_id)

    return jsonify({"success": True, "data": [
        {
            "id": x.id,
            "book_id": x.book_id,
            "book_title": x.book.title if x.book else None,
            "borrowed_at": str(x.borrowed_at) if x.borrowed_at else None,
            "due_date": str(x.due_date) if x.due_date else None,
            "returned_at": str(x.returned_at) if x.returned_at else None,
            "status": x.status
        } for x in borrows
    ]})


@web_api_bp.post("/borrow/return/<int:borrow_id>")
def borrow_return(borrow_id: int):
    if not _require_login():
        return _json_error("Unauthorized", 401)

    uid = int(session["user_id"])

    try:
        # 1) iade işlemi (SP)
        row = db.session.execute(
            text("""
                EXEC dbo.sp_return_book
                    @borrow_id = :bid,
                    @user_id   = :uid
            """),
            {"bid": int(borrow_id), "uid": uid}
        ).fetchone()

        db.session.commit()

        returned_at = getattr(row, "returned_at", None) if row else None

        # 2) iade sonrası penalty upsert (ORM)
        b = Borrow.query.get(int(borrow_id))
        if b and b.user_id == uid and b.due_date:
            now = datetime.utcnow()
            if b.due_date.date() < now.date():
                DAILY_FEE = 5
                days_overdue = max(0, (now.date() - b.due_date.date()).days)
                amount = days_overdue * DAILY_FEE

                p = Penalty.query.filter_by(borrow_id=b.id).first()
                if not p:
                    p = Penalty(
                        borrow_id=b.id,
                        days_overdue=days_overdue,
                        daily_fee=DAILY_FEE,
                        amount=amount,
                        is_paid=False
                    )
                    db.session.add(p)
                else:
                    if not p.is_paid:
                        p.days_overdue = days_overdue
                        p.daily_fee = DAILY_FEE
                        p.amount = amount

                db.session.commit()

        return jsonify({"success": True, "returned_at": str(returned_at) if returned_at else None})

    except Exception as e:
        db.session.rollback()
        return _json_error(str(e), 400)


# -----------------------------
# Admin stats / overdue / notifications
# -----------------------------
@web_api_bp.get("/admin/stats")
def admin_stats():
    if not _require_login():
        return _json_error("Unauthorized", 401)
    if session.get("role") != "admin":
        return _json_error("Yetkisiz", 403)

    total_books = Book.query.count()
    total_copies = (Book.query.with_entities(func.coalesce(func.sum(Book.total_copies), 0)).scalar() or 0)

    active_borrows = Borrow.query.filter(Borrow.returned_at.is_(None)).count()
    overdue_borrows = Borrow.query.filter(Borrow.returned_at.is_(None), Borrow.due_date < datetime.utcnow()).count()

    return jsonify({
        "success": True,
        "data": {
            "total_books": int(total_books),
            "total_copies": int(total_copies),
            "active_borrows": int(active_borrows),
            "overdue_borrows": int(overdue_borrows),
        }
    })


@web_api_bp.get("/admin/overdue")
def admin_overdue_list():
    if not _require_login():
        return _json_error("Unauthorized", 401)
    if session.get("role") != "admin":
        return _json_error("Yetkisiz", 403)

    rows = Borrow.query.filter(Borrow.returned_at.is_(None), Borrow.due_date < datetime.utcnow()).all()
    return jsonify({"success": True, "data": [
        {
            "id": b.id,
            "user": b.user.username if b.user else None,
            "email": getattr(b.user, "email", None) if b.user else None,
            "book": b.book.title if b.book else None,
            "due_date": str(b.due_date),
            "status": b.status
        } for b in rows
    ]})


@web_api_bp.get("/admin/notifications")
def admin_notifications():
    if not _require_login():
        return _json_error("Unauthorized", 401)
    if session.get("role") != "admin":
        return _json_error("Yetkisiz", 403)

    now = datetime.utcnow()

    overdue_rows = Borrow.query.filter(
        Borrow.returned_at.is_(None),
        Borrow.due_date < now
    ).order_by(Borrow.due_date.asc()).limit(20).all()

    soon_limit = now + timedelta(days=2)
    due_soon_rows = Borrow.query.filter(
        Borrow.returned_at.is_(None),
        Borrow.due_date >= now,
        Borrow.due_date <= soon_limit
    ).order_by(Borrow.due_date.asc()).limit(20).all()

    notifications = []

    for b in overdue_rows:
        user_label = b.user.username if b.user and getattr(b.user, "username", None) else None
        book_title = b.book.title if b.book and getattr(b.book, "title", None) else None
        notifications.append({
            "type": "overdue",
            "borrow_id": b.id,
            "message": f"Gecikmiş iade: {book_title or 'Kitap'} - {user_label or 'Kullanıcı'}",
            "due_date": str(b.due_date),
            "user": user_label,
            "email": getattr(b.user, "email", None) if b.user else None,
            "book": book_title
        })

    for b in due_soon_rows:
        user_label = b.user.username if b.user and getattr(b.user, "username", None) else None
        book_title = b.book.title if b.book and getattr(b.book, "title", None) else None
        notifications.append({
            "type": "due_soon",
            "borrow_id": b.id,
            "message": f"Teslim tarihi yaklaşıyor: {book_title or 'Kitap'} - {user_label or 'Kullanıcı'}",
            "due_date": str(b.due_date),
            "user": user_label,
            "email": getattr(b.user, "email", None) if b.user else None,
            "book": book_title
        })

    return jsonify({"success": True, "data": notifications})


# -----------------------------
# Admin penalties  ✅ username/email eklendi
# -----------------------------
@web_api_bp.get("/admin/penalties")
def admin_penalties():
    if not _require_login():
        return _json_error("Unauthorized", 401)
    if session.get("role") != "admin":
        return _json_error("Yetkisiz", 403)

    only_unpaid = request.args.get("only_unpaid", "0") == "1"

    q = (
        db.session.query(Penalty, Borrow, User)
        .join(Borrow, Borrow.id == Penalty.borrow_id)
        .join(User, User.id == Borrow.user_id)
    )

    if only_unpaid:
        q = q.filter(Penalty.is_paid.is_(False))

    rows = q.order_by(Penalty.updated_at.desc()).limit(200).all()

    data = []
    for p, b, u in rows:
        data.append({
            "id": p.id,
            "borrow_id": p.borrow_id,

            "username": getattr(u, "username", None),
            "email": getattr(u, "email", None),
            "user_id": int(u.id) if u else (int(b.user_id) if b else None),

            "days_overdue": int(p.days_overdue) if p.days_overdue is not None else 0,
            "daily_fee": float(p.daily_fee) if p.daily_fee is not None else 0.0,
            "amount": float(p.amount) if p.amount is not None else 0.0,
            "is_paid": bool(p.is_paid),

            "updated_at": str(p.updated_at) if getattr(p, "updated_at", None) else None,
            "created_at": str(p.created_at) if getattr(p, "created_at", None) else None,

            "due_date": str(b.due_date) if b and b.due_date else None,
            "book_id": int(b.book_id) if b else None,
            "status": getattr(b, "status", None) if b else None
        })

    return jsonify({"success": True, "data": data})


# -----------------------------
# User penalties (session based)  ✅
# -----------------------------
@web_api_bp.get("/penalties/my")
def penalties_my():
    if not _require_login():
        return _json_error("Unauthorized", 401)

    uid = int(session["user_id"])

    rows = (
        db.session.query(Penalty, Borrow)
        .join(Borrow, Borrow.id == Penalty.borrow_id)
        .filter(Borrow.user_id == uid)
        .order_by(Penalty.updated_at.desc())
        .all()
    )

    data = []
    for p, b in rows:
        data.append({
            "id": p.id,
            "borrow_id": p.borrow_id,
            "days_overdue": int(p.days_overdue) if p.days_overdue is not None else 0,
            "daily_fee": float(p.daily_fee) if p.daily_fee is not None else 0.0,
            "amount": float(p.amount) if p.amount is not None else 0.0,
            "is_paid": bool(p.is_paid),
            "created_at": str(p.created_at) if getattr(p, "created_at", None) else None,
            "updated_at": str(p.updated_at) if getattr(p, "updated_at", None) else None,
            "due_date": str(b.due_date) if b and b.due_date else None,
            "returned_at": str(b.returned_at) if b and getattr(b, "returned_at", None) else None,
            "book_id": int(b.book_id) if b else None,
            "status": getattr(b, "status", None) if b else None
        })

    return jsonify({"success": True, "data": data})


@web_api_bp.post("/penalties/pay/<int:penalty_id>")
def penalties_pay(penalty_id: int):
    if not _require_login():
        return _json_error("Unauthorized", 401)

    uid = int(session["user_id"])

    row = (
        db.session.query(Penalty, Borrow)
        .join(Borrow, Borrow.id == Penalty.borrow_id)
        .filter(Penalty.id == penalty_id, Borrow.user_id == uid)
        .first()
    )

    if not row:
        return _json_error("Ceza bulunamadı / yetkisiz", 404)

    p, _ = row

    if p.is_paid:
        return jsonify({"success": True, "message": "Bu ceza zaten ödenmiş", "data": {"id": p.id, "is_paid": True}}), 200

    p.is_paid = True
    p.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"success": True, "message": "Ödeme alındı", "data": {"id": p.id, "is_paid": True}}), 200


# -----------------------------
# Debug
# -----------------------------
@web_api_bp.get("/debug/session")
def debug_session():
    return jsonify({
        "keys": list(session.keys()),
        "username": session.get("username"),
        "role": session.get("role"),
        "user_id": session.get("user_id"),
    })


# -----------------------------
# Compatibility aliases (UI eski path kullanıyorsa kırılmasın)
# -----------------------------
@web_api_bp.get("/penalties/my/alias")
def penalties_my_alias():
    return penalties_my()
