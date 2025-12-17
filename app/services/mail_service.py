# app/services/mail_service.py
from datetime import datetime
from flask import current_app
from flask_mail import Message

from app.extensions import db, mail
from app.models.notification_log import NotificationLog
from app.models.borrow import Borrow  # ilişki varsa gerekmez

class MailService:
    @staticmethod
    def send_email(to_email: str, subject: str, body: str) -> tuple[bool, str | None]:
        """
        return: (success, error_text)
        """
        try:
            msg = Message(subject=subject, recipients=[to_email], body=body)
            mail.send(msg)
            return True, None
        except Exception as e:
            current_app.logger.warning(f"[MailService] Mail gönderilemedi: {e}")
            return False, str(e)

    @staticmethod
    def log_notification(
        borrow_id: int,
        notif_type: str,
        to_email: str | None,
        message: str,
        success: bool,
        error: str | None = None,
        commit: bool = False,   # DİKKAT: loop içinde commit yapma
    ) -> NotificationLog:
        row = NotificationLog(
            borrow_id=borrow_id,
            type=notif_type,
            email=to_email,
            message=message,
            success=bool(success),
            error_message=error,
            sent_at=datetime.utcnow(),
        )
        db.session.add(row)
        if commit:
            db.session.commit()
        return row

    @staticmethod
    def send_overdue_mail(borrow) -> bool:
        """
        Borrow üzerinden kullanıcı mailini bulup gecikme maili yollar ve loglar.
        """
        # user ve book ilişkilerin varsa:
        user = getattr(borrow, "user", None)
        book = getattr(borrow, "book", None)

        to_email = getattr(user, "email", None) if user else None
        username = getattr(user, "username", "Kullanıcı") if user else "Kullanıcı"
        book_title = getattr(book, "title", f"Kitap #{borrow.book_id}") if book else f"Kitap #{borrow.book_id}"

        subject = "Kütüphane: Geciken kitap iadesi"
        body = (
            f"Merhaba {username},\n\n"
            f"'{book_title}' kitabının teslim tarihi geçti.\n"
            f"Teslim tarihi: {borrow.due_date}\n\n"
            f"Lütfen en kısa sürede iade ediniz.\n"
        )

        if not to_email:
            MailService.log_notification(
                borrow_id=borrow.id,
                notif_type="overdue_mail",
                to_email=None,
                message="Kullanıcı email bulunamadı",
                success=False,
                error="missing_email",
                commit=False
            )
            return False

        ok, err = MailService.send_email(to_email, subject, body)

        MailService.log_notification(
            borrow_id=borrow.id,
            notif_type="overdue_mail",
            to_email=to_email,
            message="Mail gönderildi" if ok else "Mail gönderilemedi",
            success=ok,
            error=err,
            commit=False
        )
        return ok
