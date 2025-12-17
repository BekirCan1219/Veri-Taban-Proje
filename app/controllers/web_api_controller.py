from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, session
from sqlalchemy import func
from app.models.book import Book
from app.repositories.book_repo import BookRepo
from app.repositories.borrow_repo import BorrowRepo
from app.models.borrow import Borrow
from app.extensions import db
from sqlalchemy import text
from app.models.penalty import Penalty



web_api_bp = Blueprint("web_api", __name__, url_prefix="/web/api")

def _require_login():
    if not session.get("user_id"):
        return False
    return True

@web_api_bp.get("/books")
def books_list():
    books = BookRepo.list_all()
    return jsonify({"success": True, "data": [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "isbn": b.isbn,
            "total_copies": b.total_copies,
            "available_copies": b.available_copies
        } for b in books
    ]})

@web_api_bp.post("/books")
def books_create():
    if not _require_login():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    if session.get("role") != "admin":
        return jsonify({"success": False, "message": "Yetkisiz (admin gerekli)"}), 403

    data = request.get_json() or {}
    try:
        title = (data.get("title") or "").strip()
        author = (data.get("author") or "").strip()
        if not title or not author:
            return jsonify({"success": False, "message": "title ve author zorunlu"}), 400

        total = int(data.get("total_copies", 1))
        avail = int(data.get("available_copies", total))
        if avail > total:
            avail = total

        from app.models.book import Book
        from app.extensions import db

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
        return jsonify({"success": False, "message": str(e)}), 400

@web_api_bp.post("/borrow")
def borrow_create():
    if not _require_login():
        return jsonify({"success": False, "message": "Unauthorized"}), 401

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
            "borrow_id": int(row.borrow_id) if row and row.borrow_id is not None else None,
            "due_date": str(row.due_date) if row and row.due_date is not None else None
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400

@web_api_bp.get("/borrow/my")
def borrow_my():
    if not _require_login():
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    user_id = int(session["user_id"])
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

@web_api_bp.post("/borrow/return/<int:borrow_id>")
def borrow_return(borrow_id: int):
    if not _require_login():
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        uid = int(session["user_id"])

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

        return jsonify({
            "success": True,
            "returned_at": str(returned_at) if returned_at else None
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400


@web_api_bp.put("/books/<int:book_id>")
def books_update(book_id: int):
    if not _require_login():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    if session.get("role") != "admin":
        return jsonify({"success": False, "message": "Yetkisiz (admin gerekli)"}), 403

    data = request.get_json() or {}
    try:
        book = BookRepo.get(book_id)
        if not book:
            return jsonify({"success": False, "message": "Kitap bulunamadı"}), 404

        # alanları güncelle
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

        # basit tutarlılık: available <= total
        if book.available_copies > book.total_copies:
            book.available_copies = book.total_copies
        if book.available_copies < 0:
            book.available_copies = 0
        if book.total_copies < 1:
            book.total_copies = 1
            if book.available_copies > book.total_copies:
                book.available_copies = book.total_copies

        BookRepo.update()
        return jsonify({"success": True, "data": {"id": book.id}})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@web_api_bp.delete("/books/<int:book_id>")
def books_delete(book_id: int):
    if not _require_login():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    if session.get("role") != "admin":
        return jsonify({"success": False, "message": "Yetkisiz (admin gerekli)"}), 403

    try:
        book = BookRepo.get(book_id)
        if not book:
            return jsonify({"success": False, "message": "Kitap bulunamadı"}), 404

        # Eğer aktif ödünç varsa silme (temel koruma)
        active_count = Borrow.query.filter(
            Borrow.book_id == book_id,
            Borrow.returned_at.is_(None)
        ).count()
        if active_count > 0:
            return jsonify({"success": False, "message": "Bu kitap aktif ödünçte. Önce iadeler tamamlanmalı."}), 400

        BookRepo.delete(book)
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@web_api_bp.get("/admin/stats")
def admin_stats():
    if not _require_login():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    if session.get("role") != "admin":
        return jsonify({"success": False, "message": "Yetkisiz"}), 403

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
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    if session.get("role") != "admin":
        return jsonify({"success": False, "message": "Yetkisiz"}), 403

    rows = Borrow.query.filter(Borrow.returned_at.is_(None), Borrow.due_date < datetime.utcnow()).all()
    return jsonify({"success": True, "data": [
        {
            "id": b.id,
            "user": b.user.username if b.user else None,
            "email": b.user.email if b.user else None,
            "book": b.book.title if b.book else None,
            "due_date": str(b.due_date),
            "status": b.status
        } for b in rows
    ]})

@web_api_bp.get("/admin/notifications")
def admin_notifications():
    if not _require_login():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    if session.get("role") != "admin":
        return jsonify({"success": False, "message": "Yetkisiz"}), 403

    now = datetime.utcnow()

    # 1) Gecikmiş iadeler (overdue)
    overdue_rows = Borrow.query.filter(
        Borrow.returned_at.is_(None),
        Borrow.due_date < now
    ).order_by(Borrow.due_date.asc()).limit(20).all()

    # 2) Yakında teslim (örn 2 gün içinde)
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
            "email": b.user.email if b.user and getattr(b.user, "email", None) else None,
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
            "email": b.user.email if b.user and getattr(b.user, "email", None) else None,
            "book": book_title
        })

    return jsonify({"success": True, "data": notifications})


@web_api_bp.post("/admin/run-late-check")
def admin_run_late_check():
    if not _require_login():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    if session.get("role") != "admin":
        return jsonify({"success": False, "message": "Yetkisiz"}), 403

    from datetime import datetime
    from app.services.mail_service import MailService
    from app.extensions import db
    from app.models.penalty import Penalty
    from app.models.borrow import Borrow

    DAILY_FEE = 5  # günlük ceza (istersen config’e taşı)

    now = datetime.utcnow()

    rows = Borrow.query.filter(
        Borrow.returned_at.is_(None),
        Borrow.due_date < now
    ).all()

    mailed = 0
    penalties_upserted = 0

    for b in rows:
        # 1) status overdue
        if getattr(b, "status", None) != "overdue":
            b.status = "overdue"

        # 2) ceza hesapla
        days_overdue = max(0, (now.date() - b.due_date.date()).days)
        amount = days_overdue * DAILY_FEE

        # 3) upsert (borrow_id unique)
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
            # ödenmişse bile gün/amount güncellensin mi? genelde hayır.
            # ama sen istersen is_paid True ise dokunmayız:
            if not p.is_paid:
                p.days_overdue = days_overdue
                p.daily_fee = DAILY_FEE
                p.amount = amount

        penalties_upserted += 1

        # 4) mail gönder + logla (senin MailService’in log yazdığı varsayımıyla)
        if MailService.send_overdue_mail(b):
            mailed += 1

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Gecikme kontrolü tamamlandı",
        "data": {
            "overdue_found": len(rows),
            "penalties_upserted": penalties_upserted,
            "emails_sent": mailed
        }
    })

@web_api_bp.get("/admin/mail-report")
def admin_mail_report():
    if not _require_login():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    if session.get("role") != "admin":
        return jsonify({"success": False, "message": "Yetkisiz"}), 403

    from app.extensions import db
    from app.models.notification_log import NotificationLog
    from app.models.borrow import Borrow

    rows = (
        db.session.query(NotificationLog, Borrow)
        .outerjoin(Borrow, Borrow.id == NotificationLog.borrow_id)
        .order_by(NotificationLog.sent_at.desc())
        .limit(100)
        .all()
    )

    data = []
    for n, b in rows:
        data.append({
            "id": n.id,
            "borrow_id": n.borrow_id,
            "type": n.type,
            "success": n.success,
            "sent_at": str(n.sent_at),
            "email": n.email,
            "message": n.message,
            "due_date": str(b.due_date) if b else None,
            "user_id": int(b.user_id) if b else None,
            "book_id": int(b.book_id) if b else None,
        })

    return jsonify({"success": True, "data": data})

@web_api_bp.get("/debug/session")
def debug_session():
    return jsonify({
        "keys": list(session.keys()),
        "username": session.get("username"),
        "role": session.get("role"),
        "user_id": session.get("user_id"),
    })


@web_api_bp.get("/admin/penalties")
def admin_penalties():
    if not _require_login():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    if session.get("role") != "admin":
        return jsonify({"success": False, "message": "Yetkisiz"}), 403

    only_unpaid = request.args.get("only_unpaid", "0") == "1"

    q = db.session.query(Penalty, Borrow).join(Borrow, Borrow.id == Penalty.borrow_id)

    if only_unpaid:
        q = q.filter(Penalty.is_paid == False)

    rows = q.order_by(Penalty.updated_at.desc()).limit(200).all()

    data = []
    for p, b in rows:
        data.append({
            "id": p.id,
            "borrow_id": p.borrow_id,
            "days_overdue": int(p.days_overdue),
            "daily_fee": float(p.daily_fee),
            "amount": float(p.amount),
            "is_paid": bool(p.is_paid),
            "updated_at": str(p.updated_at),
            "created_at": str(p.created_at),
            "due_date": str(b.due_date) if b else None,
            "user_id": int(b.user_id) if b else None,
            "book_id": int(b.book_id) if b else None,
            "status": getattr(b, "status", None)
        })

    return jsonify({"success": True, "data": data})