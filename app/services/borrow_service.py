from datetime import datetime, timedelta, date
from decimal import Decimal

from flask_jwt_extended import get_jwt_identity, get_jwt

from app.extensions import db
from app.repositories.book_repo import BookRepo
from app.repositories.borrow_repo import BorrowRepo
from app.models.borrow import Borrow
from app.models.penalty import Penalty


class BorrowService:
    @staticmethod
    def _current_user():
        """
        JWT identity + role bilgisini servis içinde çekiyoruz.
        Controller'dan parametre geçirmek daha temiz ama mevcut yapını bozmamak için böyle bıraktım.
        """
        user_id = int(get_jwt_identity())
        role = (get_jwt() or {}).get("role")
        return user_id, role

    @staticmethod
    def _compute_overdue_days(due_date) -> int:
        if not due_date:
            return 0
        # due_date DateTime ise .date() ile normalize et
        dd = due_date.date() if hasattr(due_date, "date") else due_date
        today = date.today()
        if dd >= today:
            return 0
        return (today - dd).days

    @staticmethod
    def _upsert_penalty_for_borrow(borrow: Borrow):

        overdue_days = BorrowService._compute_overdue_days(borrow.due_date)

        p = Penalty.query.filter_by(borrow_id=borrow.id).first()

        if overdue_days <= 0:
            # gecikme yoksa: varsa sıfırla (istersen dokunmayabiliriz)
            if p and not p.is_paid:
                p.days_overdue = 0
                p.amount = Decimal("0.00")
            return

        if not p:
            # yeni penalty oluştur
            daily_fee = Decimal("5.00")  # model default 5, istersen config'e alırız
            amount = (daily_fee * Decimal(overdue_days)).quantize(Decimal("0.01"))
            p = Penalty(
                borrow_id=borrow.id,
                days_overdue=overdue_days,
                daily_fee=daily_fee,
                amount=amount,
                is_paid=False,
            )
            db.session.add(p)
        else:
            # mevcut penalty güncelle (ödenmişse de güncellemek isteyebilirsin; burada amount güncelliyorum ama is_paid'ı bozma)
            daily_fee = Decimal(str(p.daily_fee))
            amount = (daily_fee * Decimal(overdue_days)).quantize(Decimal("0.01"))
            p.days_overdue = overdue_days
            p.amount = amount
            # p.is_paid aynen kalır

    @staticmethod
    def borrow_book(book_id: int, days: int = 14):
        user_id, _role = BorrowService._current_user()

        book = BookRepo.get(book_id)
        if not book:
            raise ValueError("Kitap bulunamadı")

        # tutarlılık: tekrar kontrol
        if book.available_copies is None or book.available_copies < 1:
            raise ValueError("Bu kitap şu anda mevcut değil")

        if days <= 0:
            raise ValueError("days pozitif olmalı")

        # stok düş
        book.available_copies -= 1
        if book.available_copies < 0:
            # emniyet
            book.available_copies = 0
            raise ValueError("Bu kitap şu anda mevcut değil")

        borrow = Borrow(
            user_id=user_id,
            book_id=book_id,
            due_date=datetime.utcnow() + timedelta(days=days),
            status="active"
        )

        # transaction gibi davranması için tek commit noktası
        BorrowRepo.create(borrow)
        BookRepo.update()
        BorrowRepo.commit()  # commit yoksa borrows kaydı db’ye yazılmayabilir

        return borrow

    @staticmethod
    def return_book(borrow_id: int):
        user_id, role = BorrowService._current_user()

        borrow = BorrowRepo.get(borrow_id)
        if not borrow:
            raise ValueError("Ödünç kaydı bulunamadı")

        # admin değilse kendi kaydı olmalı
        if role != "admin" and borrow.user_id != user_id:
            raise ValueError("Bu kayıt sana ait değil")

        if borrow.returned_at is not None:
            raise ValueError("Bu kitap zaten iade edilmiş")

        borrow.returned_at = datetime.utcnow()
        borrow.status = "returned"

        # stok iade
        book = BookRepo.get(borrow.book_id)
        if book:
            # min(total, available+1)
            if book.total_copies is not None and book.available_copies is not None:
                book.available_copies = min(book.total_copies, book.available_copies + 1)
            elif book.available_copies is not None:
                book.available_copies += 1

        # penalty create/update (senin modeline göre)
        BorrowService._upsert_penalty_for_borrow(borrow)

        # tek commit
        BorrowRepo.commit()
        BookRepo.update()
        db.session.commit()  # penalty db.session ile eklendiği için garanti olsun

        return borrow
