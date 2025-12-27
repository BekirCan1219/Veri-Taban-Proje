# app/services/scheduler.py
from __future__ import annotations

def start_scheduler(app):
    """
    Scheduler opsiyonel: APScheduler yoksa uygulama yine çalışır.
    - App context ile job çalıştırır (DB erişimleri patlamasın diye).
    - Debug reloader'da çift çalışmayı engeller.
    - Uygulama kapanırken scheduler'ı kapatır.
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        # ✅ Debug reloader çift process çalıştırır; sadece "asıl" process'te başlat
        # Werkzeug reloader varsa WERKZEUG_RUN_MAIN=true olan process gerçek process'tir.
        if app.debug:
            import os
            if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
                app.logger.info("[scheduler] Debug reloader secondary process: scheduler skipped.")
                return

        # ✅ Job fonksiyonunu burada import etmek circular import riskini azaltır
        from app.tasks.late_check import run_late_check_job

        scheduler = BackgroundScheduler(timezone="UTC")

        def _job_wrapper():
            # ✅ Flask app context ile çalıştır
            with app.app_context():
                try:
                    run_late_check_job(app)
                except Exception as ex:
                    app.logger.exception(f"[scheduler] late_check_job error: {ex}")

        # ✅ 10 dakikada bir (test için iyi). İstersen dakikayı artır/azalt.
        scheduler.add_job(
            func=_job_wrapper,
            trigger=IntervalTrigger(minutes=10),
            id="late_check_job",
            replace_existing=True,
            max_instances=1,        # aynı job üst üste binmesin
            coalesce=True,          # kaçırılanları tek seferde toparla
            misfire_grace_time=120  # 2 dk tolerans
        )

        scheduler.start()
        app.logger.info("[scheduler] Late check job started (every 10 minutes).")

        # ✅ app içine referans koy (gerekirse başka yerden erişirsin)
        app.extensions = getattr(app, "extensions", {})
        app.extensions["apscheduler"] = scheduler

        # ✅ Uygulama kapanınca scheduler dursun
        @app.teardown_appcontext
        def _shutdown_scheduler(exc=None):
            sch = app.extensions.get("apscheduler")
            if sch and getattr(sch, "running", False):
                try:
                    sch.shutdown(wait=False)
                    app.logger.info("[scheduler] Scheduler shutdown.")
                except Exception:
                    pass

    except Exception as e:
        # APScheduler yüklü değilse bile app açılsın
        app.logger.warning(f"[scheduler] Scheduler başlatılamadı (opsiyonel): {e}")
