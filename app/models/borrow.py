from datetime import datetime
from app.extensions import db

class Borrow(db.Model):
    __tablename__ = "borrows"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False, index=True)

    borrowed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False)
    returned_at = db.Column(db.DateTime, nullable=True)

    status = db.Column(db.String(20), nullable=False, default="active")  # active/returned/late

    user = db.relationship("User", backref="borrows")
    book = db.relationship("Book", backref="borrows")
