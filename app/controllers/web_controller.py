from flask import Blueprint, render_template, request, redirect, url_for, session, flash

web_bp = Blueprint("web", __name__)

def _is_logged_in() -> bool:
    return bool(session.get("access_token") and session.get("user_id"))

def _is_admin() -> bool:
    return session.get("role") == "admin"


@web_bp.get("/")
def root():
    # giriş yoksa login, varsa books-page
    if not _is_logged_in():
        return redirect(url_for("web.login_page"))
    return redirect(url_for("web.books_page"))


@web_bp.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        if _is_logged_in():
            return redirect(url_for("web.books_page"))
        return render_template("login.html")

    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()

    if not username or not password:
        flash("Kullanıcı adı ve şifre zorunlu.", "danger")
        return redirect(url_for("web.login_page"))

    from app.services.auth_service import AuthService

    try:
        token, user = AuthService.login(username, password)

        session["access_token"] = token
        session["user_id"] = user.id
        session["username"] = user.username
        session["role"] = user.role

        return redirect(url_for("web.books_page"))

    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("web.login_page"))


@web_bp.route("/register", methods=["GET", "POST"])
def register_page():
    # zaten girişliyse kitaplara gönder
    if _is_logged_in():
        return redirect(url_for("web.books_page"))

    if request.method == "GET":
        return render_template("register.html")

    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip()
    password = (request.form.get("password") or "").strip()

    if not username or not email or not password:
        flash("Username, email ve şifre zorunlu.", "danger")
        return redirect(url_for("web.register_page"))

    from app.services.auth_service import AuthService
    try:
        # role sabit: user
        AuthService.register(username=username, email=email, password=password, role="user")
        flash("Kayıt başarılı! Şimdi giriş yapabilirsin.", "success")
        return redirect(url_for("web.login_page"))
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("web.register_page"))


@web_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.login_page"))


@web_bp.get("/books-page")
def books_page():
    if not _is_logged_in():
        return redirect(url_for("web.login_page"))
    return render_template("books.html", username=session.get("username"), role=session.get("role"))


@web_bp.get("/borrow-page")
def borrow_page():
    if not _is_logged_in():
        return redirect(url_for("web.login_page"))
    return render_template("borrow.html", username=session.get("username"), role=session.get("role"))


@web_bp.get("/admin")
def admin_page():
    if not _is_logged_in():
        return redirect(url_for("web.login_page"))
    if not _is_admin():
        flash("Bu sayfa sadece admin içindir.", "danger")
        return redirect(url_for("web.books_page"))
    return render_template("admin.html", username=session.get("username"), role=session.get("role"))


# Eski/yanlış linkler gelirse yakala
@web_bp.get("/books")
def books_redirect():
    return redirect(url_for("web.books_page"))

@web_bp.get("/borrow")
def borrow_redirect():
    return redirect(url_for("web.borrow_page"))

