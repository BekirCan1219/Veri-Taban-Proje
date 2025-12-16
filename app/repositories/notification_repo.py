from app.models.notification_log import NotificationLog
from app.extensions import db

class NotificationRepo:
    @staticmethod
    def already_sent(borrow_id: int, notif_type: str = "late_return") -> bool:
        return NotificationLog.query.filter_by(borrow_id=borrow_id, type=notif_type).first() is not None

    @staticmethod
    def log(entry: NotificationLog):
        db.session.add(entry)
        db.session.commit()
        return entry
