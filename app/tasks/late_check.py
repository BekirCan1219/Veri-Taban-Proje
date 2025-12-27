# app/tasks/late_check.py
from datetime import datetime, timedelta
from flask import current_app

from app.extensions import db
from app.models.borrow import Borrow
from app.models.penalty import Penalty
from app.services.mail_service import MailService


DAILY_FEE = 5  # istersen config'e al


def _calc_days_overdue(due_date, now_utc: datetime) -> int:
    if not due_date:
        return 0
    # due_date datetime ise sadece date bazında fark alalım
    return max(0, (now_utc.date() - due_date.date()).days)


def _upsert_penalty_for_borrow(b: Borrow, now_utc: datetime) -> bool:
    """
    Returns: True if created/updated, False if no action
    - Eğer gecikme yoksa hiç dokunmaz
    - Eğer ceza var ve is_paid=True ise dokunmaz
    - Eğer ceza yoksa oluşturur
    - Eğer ceza var ve ödenmemişse günceller
    """
    if not b or not b.due_date:
        return False

    days_overdue = _calc_days_overdue(b.due_date, now_utc)
    if days_overdue <= 0:
        return False

    amount = days_overdue * DAILY_FEE

    p = Penalty.query.filter_by(borrow_id=b.id).first()
    if not p:
        p = Penalty(
            borrow_id=b.id,
            days_overdue=days_overdue,
            daily_fee=DAILY_FEE,
            amount=amount,
            is_paid=False
        )
        db.session.add(p)
        return True

    # varsa ve ödendiyse elleme
    if getattr(p, "is_paid", False):
        return False

    # ödenmemişse güncelle
    p.days_overdue = days_overdue
    p.daily_fee = DAILY_FEE
    p.amount = amount
    if hasattr(p, "updated_at"):
        p.updated_at = now_utc
    return True


def run_late_check_job(app):
    """
    Geciken / yaklaşan due_date kayıtlarını kontrol eder.
    - overdue: due_date geçmiş ve returned_at None
    - due_soon: due_date 1 gün içinde
    Ek: overdue borrows için Penalty upsert yapar (ödenmemişse günceller).
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

            penalty_changed = 0
            mail_overdue_sent = 0
            mail_due_soon_sent = 0

            # Overdue: penalty upsert + mail + log + status
            for b in overdue_rows:
                # ✅ penalty oluştur/güncelle
                if _upsert_penalty_for_borrow(b, now):
                    penalty_changed += 1

                # (opsiyonel) status güncelle
                try:
                    b.status = "overdue"
                except Exception:
                    pass

                # mail + log
                user_email = b.user.email if b.user else None
                subject = "Kütüphane: Geciken ödünç hatırlatması"
                body = (
                    "Merhaba,\n\n"
                    f"'{b.book.title if b.book else 'Kitap'}' adlı kitabın teslim tarihi geçti.\n"
                    f"Teslim tarihi: {b.due_date}\n\n"
                    "Lütfen en kısa sürede iade ediniz."
                )

                ok = False
                err = None
                if user_email:
                    ok = MailService.send_email(user_email, subject, body)
                    if ok:
                        mail_overdue_sent += 1
                    else:
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

            # Due soon: mail + log (ceza yok)
            for b in due_soon_rows:
                user_email = b.user.email if b.user else None
                subject = "Kütüphane: Teslim tarihi yaklaşıyor"
                body = (
                    "Merhaba,\n\n"
                    f"'{b.book.title if b.book else 'Kitap'}' adlı kitabın teslim tarihi yaklaşıyor.\n"
                    f"Teslim tarihi: {b.due_date}\n\n"
                    "İade etmeyi unutma."
                )

                ok = False
                err = None
                if user_email:
                    ok = MailService.send_email(user_email, subject, body)
                    if ok:
                        mail_due_soon_sent += 1
                    else:
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

            # ✅ tek commit
            db.session.commit()

            current_app.logger.info(
                f"[late_check] overdue={len(overdue_rows)} due_soon={len(due_soon_rows)} "
                f"penalty_changed={penalty_changed} mail_overdue_sent={mail_overdue_sent} "
                f"mail_due_soon_sent={mail_due_soon_sent}"
            )

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(f"[late_check] Hata: {e}")
