from flask import current_app

def start_scheduler(app):
    """
    Proje patlamasın diye: scheduler yoksa bile uygulama çalışsın.
    Eğer APScheduler kuruluysa, burayı gerçek scheduler ile çalıştırırsın.
    """
    try:
        # Eğer APScheduler kullanıyorsan:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler(timezone="UTC")

        # Her 10 dakikada bir kontrol (istersen değiştir)
        from app.tasks.late_check import run_late_check_job

        scheduler.add_job(
            func=lambda: run_late_check_job(app),
            trigger="interval",
            minutes=10,
            id="late_check_job",
            replace_existing=True,
        )
        scheduler.start()
        app.logger.info("[scheduler] Late check job started (every 10 minutes).")

    except Exception as e:
        # APScheduler yüklü değilse bile app açılsın
        app.logger.warning(f"[scheduler] Scheduler başlatılamadı (opsiyonel): {e}")