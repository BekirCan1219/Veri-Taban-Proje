from datetime import datetime, timedelta
from flask_jwt_extended import get_jwt_identity
from app.repositories.book_repo import BookRepo
from app.repositories.borrow_repo import BorrowRepo
from app.models.borrow import Borrow

class BorrowService:
    @staticmethod
    def borrow_book(book_id: int, days: int = 14):
        user_id = int(get_jwt_identity())
        book = BookRepo.get(book_id)
        if not book:
            raise ValueError("Kitap bulunamadı")
        if book.available_copies < 1:
            raise ValueError("Bu kitap şu anda mevcut değil")

        book.available_copies -= 1

        borrow = Borrow(
            user_id=user_id,
            book_id=book_id,
            due_date=datetime.utcnow() + timedelta(days=days),
            status="active"
        )
        BorrowRepo.create(borrow)
        BookRepo.update()
        return borrow

    @staticmethod
    def return_book(borrow_id: int):
        user_id = int(get_jwt_identity())
        borrow = BorrowRepo.get(borrow_id)
        if not borrow:
            raise ValueError("Ödünç kaydı bulunamadı")
        if borrow.user_id != user_id:
            raise ValueError("Bu kayıt sana ait değil")
        if borrow.returned_at is not None:
            raise ValueError("Bu kitap zaten iade edilmiş")

        borrow.returned_at = datetime.utcnow()
        borrow.status = "returned"

        # stok iade
        book = BookRepo.get(borrow.book_id)
        if book:
            book.available_copies = min(book.total_copies, book.available_copies + 1)

        BorrowRepo.commit()
        BookRepo.update()
        return borrow
