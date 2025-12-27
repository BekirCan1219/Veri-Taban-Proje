from flask import Flask, jsonify
from app.config import Config
from app.extensions import db, migrate, jwt, mail

from app.controllers.web_controller import web_bp
from app.controllers.web_api_controller import web_api_bp
from app.db_objects_mssql import ensure_db_objects_mssql


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 1) Önce db init (db.engine / db.session için şart)
    db.init_app(app)

    # 2) MSSQL trigger/SP gibi DB objelerini oluştur/ensure et (db init sonrası)
    ensure_db_objects_mssql(app)

    # 3) Diğer extension’lar
    migrate.init_app(app, db)
    jwt.init_app(app)
    mail.init_app(app)

    # 4) Web/UI blueprintleri
    app.register_blueprint(web_bp)
    app.register_blueprint(web_api_bp)

    # 5) API blueprintleri (url_prefix veriyorsan blueprint içinde tekrar verme)
    from app.controllers.auth_controller import auth_bp
    from app.controllers.book_controller import book_bp
    from app.controllers.borrow_controller import borrow_bp
    from app.controllers.notification_controller import notif_bp
    from app.controllers.penalty_controller import penalty_bp
    app.register_blueprint(penalty_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(book_bp, url_prefix="/books")
    app.register_blueprint(borrow_bp, url_prefix="/borrow")
    app.register_blueprint(notif_bp, url_prefix="/notifications")

    @app.get("/health")
    def health():
        return jsonify({"ok": True})

    # Scheduler (gecikme kontrol)
    from app.tasks.scheduler import start_scheduler
    start_scheduler(app)

    return app
