from datetime import datetime
from flask import current_app
from app.extensions import db, mail
from flask_mail import Message

# ✅ DOĞRU: notification.py yok, notification_log.py var
from app.models.notification_log import NotificationLog


class MailService:
    @staticmethod
    def send_email(to_email: str, subject: str, body: str) -> bool:
        """
        Mail atmayı dener.
        Mail config yoksa (MAIL_SERVER vs), uygulama patlamasın diye False döndürür.
        """
        try:
            msg = Message(subject=subject, recipients=[to_email], body=body)
            mail.send(msg)
            return True
        except Exception as e:
            # Mail ayarı yoksa vs. uygulama crash olmasın
            current_app.logger.warning(f"[MailService] Mail gönderilemedi: {e}")
            return False

    @staticmethod
    def log_notification(
        borrow_id: int,
        notif_type: str,
        to_email: str | None,
        message: str,
        success: bool,
        error: str | None = None,
    ) -> NotificationLog:
        """
        Bildirim logu DB'ye yazar.
        """
        row = NotificationLog(
            borrow_id=borrow_id,
            type=notif_type,
            email=to_email,
            message=message,
            success=bool(success),
            error=error,
            sent_at=datetime.utcnow(),
        )
        db.session.add(row)
        db.session.commit()
        return row