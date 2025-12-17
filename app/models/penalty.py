from datetime import datetime
from app.extensions import db

class Penalty(db.Model):
    __tablename__ = "penalties"

    id = db.Column(db.Integer, primary_key=True)

    borrow_id = db.Column(db.Integer, db.ForeignKey("borrows.id"), unique=True, nullable=False, index=True)

    days_overdue = db.Column(db.Integer, nullable=False, default=0)
    daily_fee = db.Column(db.Numeric(10, 2), nullable=False, default=5)
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    is_paid = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    borrow = db.relationship("Borrow", backref=db.backref("penalty", uselist=False))
