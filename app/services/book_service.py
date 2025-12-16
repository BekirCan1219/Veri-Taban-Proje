from app.models.book import Book
from app.repositories.book_repo import BookRepo

class BookService:
    @staticmethod
    def list_books():
        return BookRepo.list_all()

    @staticmethod
    def get_book(book_id: int):
        book = BookRepo.get(book_id)
        if not book:
            raise ValueError("Kitap bulunamadı")
        return book

    @staticmethod
    def create_book(data: dict):
        book = Book(
            title=data["title"],
            author=data["author"],
            isbn=data.get("isbn"),
            total_copies=int(data.get("total_copies", 1)),
            available_copies=int(data.get("available_copies", data.get("total_copies", 1))),
        )
        if book.available_copies > book.total_copies:
            book.available_copies = book.total_copies
        return BookRepo.create(book)

    @staticmethod
    def update_book(book_id: int, data: dict):
        book = BookService.get_book(book_id)
        for k in ["title", "author", "isbn"]:
            if k in data:
                setattr(book, k, data[k])

        if "total_copies" in data:
            book.total_copies = int(data["total_copies"])
        if "available_copies" in data:
            book.available_copies = int(data["available_copies"])

        if book.available_copies > book.total_copies:
            book.available_copies = book.total_copies

        BookRepo.update()
        return book

    @staticmethod
    def delete_book(book_id: int):
        book = BookService.get_book(book_id)
        BookRepo.delete(book)
