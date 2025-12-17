# app/models/notification_log.py
from datetime import datetime
from app.extensions import db

class NotificationLog(db.Model):
    __tablename__ = "notification_logs"

    id = db.Column(db.Integer, primary_key=True)

    borrow_id = db.Column(db.Integer, db.ForeignKey("borrows.id"), nullable=False, index=True)

    # bildirimin tipi: overdue_mail, due_soon, late_return vs.
    type = db.Column(db.String(50), nullable=False, default="late_return")

    # KİLİT: rapor için gerekli alanlar
    email = db.Column(db.String(255), nullable=True)
    message = db.Column(db.String(1000), nullable=True)

    sent_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    success = db.Column(db.Boolean, nullable=False, default=True)

    # İstersen isim error_message kalsın:
    error_message = db.Column(db.String(500), nullable=True)

    borrow = db.relationship("Borrow", backref="notifications")
