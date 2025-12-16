from datetime import datetime, timedelta
from flask import current_app

from app.models.borrow import Borrow
from app.services.mail_service import MailService
from app.extensions import db


def run_late_check_job(app):
    """
    Geciken / yaklaşan due_date kayıtlarını kontrol eder.
    - overdue: due_date geçmiş ve returned_at None
    - due_soon: due_date 1 gün içinde
    """
    with app.app_context():
        try:
            now = datetime.utcnow()
            due_soon_limit = now + timedelta(days=1)

            # Gecikenler
            overdue_rows = Borrow.query.filter(
                Borrow.returned_at.is_(None),
                Borrow.due_date < now
            ).all()

            # Yaklaşanlar
            due_soon_rows = Borrow.query.filter(
                Borrow.returned_at.is_(None),
                Borrow.due_date >= now,
                Borrow.due_date <= due_soon_limit
            ).all()

            # Overdue mail + log
            for b in overdue_rows:
                user_email = b.user.email if b.user else None
                subject = "Kütüphane: Geciken ödünç hatırlatması"
                body = f"Merhaba,\n\n'{b.book.title if b.book else 'Kitap'}' adlı kitabın teslim tarihi geçti.\nTeslim tarihi: {b.due_date}\n\nLütfen en kısa sürede iade ediniz."

                ok = False
                err = None
                if user_email:
                    ok = MailService.send_email(user_email, subject, body)
                    if not ok:
                        err = "Mail gönderilemedi (mail config eksik olabilir)."
                else:
                    err = "Kullanıcı email bulunamadı."

                MailService.log_notification(
                    borrow_id=b.id,
                    notif_type="overdue",
                    to_email=user_email,
                    message=body,
                    success=ok,
                    error=err
                )

                # İstersen status güncelle
                b.status = "overdue"
            db.session.commit()

            # Due soon mail + log
            for b in due_soon_rows:
                user_email = b.user.email if b.user else None
                subject = "Kütüphane: Teslim tarihi yaklaşıyor"
                body = f"Merhaba,\n\n'{b.book.title if b.book else 'Kitap'}' adlı kitabın teslim tarihi yaklaşıyor.\nTeslim tarihi: {b.due_date}\n\nİade etmeyi unutma."

                ok = False
                err = None
                if user_email:
                    ok = MailService.send_email(user_email, subject, body)
                    if not ok:
                        err = "Mail gönderilemedi (mail config eksik olabilir)."
                else:
                    err = "Kullanıcı email bulunamadı."

                MailService.log_notification(
                    borrow_id=b.id,
                    notif_type="due_soon",
                    to_email=user_email,
                    message=body,
                    success=ok,
                    error=err
                )

            current_app.logger.info(f"[late_check] overdue={len(overdue_rows)} due_soon={len(due_soon_rows)}")

        except Exception as e:
            current_app.logger.error(f"[late_check] Hata: {e}")