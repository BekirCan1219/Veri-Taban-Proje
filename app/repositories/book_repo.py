from app.models.book import Book
from app.extensions import db

class BookRepo:
    @staticmethod
    def list_all():
        return Book.query.order_by(Book.id.desc()).all()

    @staticmethod
    def get(book_id: int):
        return Book.query.get(book_id)

    @staticmethod
    def create(book: Book):
        db.session.add(book)
        db.session.commit()
        return book

    @staticmethod
    def update():
        db.session.commit()

    @staticmethod
    def delete(book: Book):
        db.session.delete(book)
        db.session.commit()
