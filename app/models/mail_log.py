from datetime import datetime
from app.extensions import db

class MailLog(db.Model):
    __tablename__ = "mail_logs"

    id = db.Column(db.Integer, primary_key=True)
    borrow_id = db.Column(db.Integer, nullable=True)

    notif_type = db.Column(db.String(50), nullable=False)  # overdue / due_soon
    to_email = db.Column(db.String(255), nullable=True)
    message = db.Column(db.Text, nullable=True)

    success = db.Column(db.Boolean, nullable=False, default=False)
    error = db.Column(db.String(500), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
