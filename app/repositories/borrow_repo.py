from datetime import datetime
from app.models.borrow import Borrow
from app.extensions import db

class BorrowRepo:
    @staticmethod
    def get(borrow_id: int):
        return Borrow.query.get(borrow_id)

    @staticmethod
    def list_by_user(user_id: int):
        return Borrow.query.filter_by(user_id=user_id).order_by(Borrow.id.desc()).all()

    @staticmethod
    def list_all():
        return Borrow.query.order_by(Borrow.id.desc()).all()

    @staticmethod
    def create(borrow: Borrow):
        db.session.add(borrow)
        db.session.commit()
        return borrow

    @staticmethod
    def commit():
        db.session.commit()

    @staticmethod
    def find_overdue(now: datetime):
        return Borrow.query.filter(
            Borrow.returned_at.is_(None),
            Borrow.due_date < now
        ).all()
