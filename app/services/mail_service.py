# app/services/mail_service.py
from __future__ import annotations

from datetime import datetime
from flask import current_app
from flask_mail import Message

from app.extensions import db, mail
from app.models.notification_log import NotificationLog


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
        borrow_id: int | None,
        notif_type: str,
        to_email: str | None,
        message: str,
        success: bool,
        error: str | None = None,
        commit: bool = False,  # loop içinde commit yapma
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
    def _borrow_labels(borrow):
        user = getattr(borrow, "user", None)
        book = getattr(borrow, "book", None)

        to_email = getattr(user, "email", None) if user else None
        username = getattr(user, "username", "Kullanıcı") if user else "Kullanıcı"
        book_title = getattr(book, "title", f"Kitap #{getattr(borrow, 'book_id', '-')}")
        due_date = getattr(borrow, "due_date", None)

        return to_email, username, book_title, due_date

    @staticmethod
    def send_overdue_mail(borrow) -> bool:
        """
        Borrow üzerinden kullanıcı mailini bulup gecikme maili yollar ve loglar.
        commit=False bırak: dışarıda tek commit yapılmalı.
        """
        to_email, username, book_title, due_date = MailService._borrow_labels(borrow)

        subject = "Kütüphane: Geciken kitap iadesi"
        body = (
            f"Merhaba {username},\n\n"
            f"'{book_title}' kitabının teslim tarihi geçti.\n"
            f"Teslim tarihi: {due_date}\n\n"
            f"Lütfen en kısa sürede iade ediniz.\n"
        )

        if not to_email:
            MailService.log_notification(
                borrow_id=getattr(borrow, "id", None),
                notif_type="overdue_mail",
                to_email=None,
                message="Kullanıcı email bulunamadı",
                success=False,
                error="missing_email",
                commit=False,
            )
            return False

        ok, err = MailService.send_email(to_email, subject, body)

        MailService.log_notification(
            borrow_id=getattr(borrow, "id", None),
            notif_type="overdue_mail",
            to_email=to_email,
            message="Mail gönderildi" if ok else "Mail gönderilemedi",
            success=ok,
            error=err,
            commit=False,
        )
        return ok

    @staticmethod
    def send_due_soon_mail(borrow) -> bool:
        """
        Teslim tarihi yaklaşanlar için mail + log.
        """
        to_email, username, book_title, due_date = MailService._borrow_labels(borrow)

        subject = "Kütüphane: Teslim tarihi yaklaşıyor"
        body = (
            f"Merhaba {username},\n\n"
            f"'{book_title}' kitabının teslim tarihi yaklaşıyor.\n"
            f"Teslim tarihi: {due_date}\n\n"
            f"İade etmeyi unutmayınız.\n"
        )

        if not to_email:
            MailService.log_notification(
                borrow_id=getattr(borrow, "id", None),
                notif_type="due_soon_mail",
                to_email=None,
                message="Kullanıcı email bulunamadı",
                success=False,
                error="missing_email",
                commit=False,
            )
            return False

        ok, err = MailService.send_email(to_email, subject, body)

        MailService.log_notification(
            borrow_id=getattr(borrow, "id", None),
            notif_type="due_soon_mail",
            to_email=to_email,
            message="Mail gönderildi" if ok else "Mail gönderilemedi",
            success=ok,
            error=err,
            commit=False,
        )
        return ok
