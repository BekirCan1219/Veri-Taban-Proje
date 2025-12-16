from datetime import datetime
from flask_mail import Message
from app.extensions import mail
from app.repositories.borrow_repo import BorrowRepo
from app.repositories.notification_repo import NotificationRepo
from app.models.notification_log import NotificationLog

class NotificationService:
    @staticmethod
    def check_and_notify_late_returns():
        now = datetime.utcnow()
        overdue = BorrowRepo.find_overdue(now)

        for b in overdue:
            # status güncelle
            b.status = "late"

            # daha önce mail atıldı mı?
            if NotificationRepo.already_sent(b.id, "late_return"):
                continue

            try:
                # Mail config yoksa crash etmesin diye:
                if not b.user or not b.user.email:
                    raise RuntimeError("Kullanıcı e-postası yok")

                msg = Message(
                    subject="Kütüphane Bildirimi: Gecikmiş İade",
                    recipients=[b.user.email],
                    body=(
                        f"Merhaba {b.user.username},\n\n"
                        f"'{b.book.title}' kitabının iade tarihi geçti.\n"
                        f"Son iade tarihi: {b.due_date}\n\n"
                        f"Lütfen en kısa sürede iade ediniz."
                    ),
                )
                mail.send(msg)

                NotificationRepo.log(NotificationLog(borrow_id=b.id, success=True))
            except Exception as e:
                NotificationRepo.log(NotificationLog(borrow_id=b.id, success=False, error_message=str(e)))

        # status commit
        BorrowRepo.commit()
