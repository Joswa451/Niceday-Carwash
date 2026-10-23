from pymysql.err import IntegrityError

from flask import Blueprint, render_template, request, url_for, redirect, session, flash
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db_connection

auth_bp = Blueprint("authentication", __name__)


def _safe_next(target, fallback):
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return fallback


@auth_bp.route("/login")
def login_page():
    return render_template("login.html")


@auth_bp.route("/register")
def register_page():
    return render_template("register.html")


@auth_bp.route("/admin/login")
def admin_login():
    return render_template("admin_login.html")


@auth_bp.route("/login_process", methods=["POST"])
def login_process():
    user = request.form.get("user_inp", "").strip()
    password = request.form.get("pass_inp", "").strip()
    next_page = _safe_next(
        request.form.get("next"), url_for("main_pages.landing_page")
    )

    if not user or not password:
        flash("Username and password are required.", "error")
        return redirect(next_page)

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT * FROM accounts WHERE account_username = %s", (user,)
        )
        account = cursor.fetchone()

        if not account:
            flash("Invalid username or password. Please try again.", "error")
            return redirect(next_page)

        stored_password = account["account_password"]
        password_ok = False
        if stored_password.startswith(("scrypt:", "pbkdf2:", "argon2")):
            password_ok = check_password_hash(stored_password, password)
        else:
            password_ok = stored_password == password
            if password_ok:
                cursor.execute(
                    "UPDATE accounts SET account_password = %s WHERE account_id = %s",
                    (generate_password_hash(password), account["account_id"]),
                )
                connection.commit()

        if not password_ok:
            flash("Invalid username or password. Please try again.", "error")
            return redirect(next_page)

        account.pop("account_password", None)
        session.clear()
        session["account_logged_in"] = account

        if account["account_role"] == "admin":
            return redirect(url_for("admin_panel.admin_dashboard"))
        return redirect(url_for("main_pages.landing_page"))
    except Exception as error:
        flash(f"Login error: {error}", "error")
        return redirect(next_page)
    finally:
        if connection:
            connection.close()


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main_pages.landing_page"))


@auth_bp.route("/register_process", methods=["POST"])
def register_process():
    full_name = request.form.get("full_name", "").strip()
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    password = request.form.get("password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if not all([full_name, username, email, password, confirm_password]):
        flash("All fields except phone are required.", "error")
        return redirect(url_for("authentication.register_page"))

    if password != confirm_password:
        flash("Passwords do not match. Please try again.", "error")
        return redirect(url_for("authentication.register_page"))

    if len(username) < 3:
        flash("Username must be at least 3 characters long.", "error")
        return redirect(url_for("authentication.register_page"))

    if len(password) < 6:
        flash("Password must be at least 6 characters long.", "error")
        return redirect(url_for("authentication.register_page"))

    if "@" not in email or "." not in email.split("@")[-1]:
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("authentication.register_page"))

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT account_username FROM accounts WHERE account_username = %s",
            (username,),
        )
        if cursor.fetchone():
            flash(f"Username '{username}' already exists. Please choose another.", "error")
            return redirect(url_for("authentication.register_page"))

        cursor.execute(
            "SELECT account_email FROM accounts WHERE account_email = %s", (email,)
        )
        if cursor.fetchone():
            flash(f"Email '{email}' is already registered.", "error")
            return redirect(url_for("authentication.register_page"))

        cursor.execute(
            "INSERT INTO accounts "
            "(account_username, account_password, account_role, account_email, full_name, phone) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                username,
                generate_password_hash(password),
                "client",
                email,
                full_name,
                phone,
            ),
        )
        connection.commit()

        flash("Account created successfully. You can now log in.", "success")
        return redirect(url_for("authentication.login_page"))
    except IntegrityError:
        flash("That username or email is already in use.", "error")
        return redirect(url_for("authentication.register_page"))
    except Exception as error:
        flash(f"An error occurred: {error}", "error")
        return redirect(url_for("authentication.register_page"))
    finally:
        if connection:
            connection.close()
