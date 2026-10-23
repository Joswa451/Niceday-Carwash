from pymysql.err import IntegrityError

from flask import Blueprint, render_template, request, url_for, redirect, session, flash
from werkzeug.security import generate_password_hash

from db import get_db_connection

admin_bp = Blueprint("admin_panel", __name__, url_prefix="/admin")


def admin_required():
    account = session.get("account_logged_in")
    if not account:
        flash("Please log in to access the admin dashboard.", "error")
        return redirect(url_for("authentication.admin_login"))
    if account["account_role"] != "admin":
        flash("Access denied. Admin privileges are required.", "error")
        return redirect(url_for("main_pages.landing_page"))
    return None


@admin_bp.route("/dashboard")
def admin_dashboard():
    auth_check = admin_required()
    if auth_check:
        return auth_check

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT b.*, s.service_name, s.price, a.account_username AS client_name
            FROM bookings b
            JOIN services s ON b.service_id = s.service_id
            JOIN accounts a ON b.client_id = a.account_id
            ORDER BY b.created_at DESC, b.booking_id DESC
            """
        )
        bookings = cursor.fetchall()

        cursor.execute("SELECT * FROM services ORDER BY service_name")
        services = cursor.fetchall()

        cursor.execute(
            "SELECT account_id, account_username, account_role, account_email, created_at "
            "FROM accounts ORDER BY created_at DESC"
        )
        accounts = cursor.fetchall()

        return render_template(
            "admin_dashboard.html",
            bookings=bookings,
            services=services,
            accounts=accounts,
            logged_in_user=session["account_logged_in"],
        )
    except Exception as error:
        flash(f"Could not load the dashboard: {error}", "error")
        return redirect(url_for("main_pages.landing_page"))
    finally:
        if connection:
            connection.close()


@admin_bp.route("/add_service", methods=["POST"])
def add_service():
    auth_check = admin_required()
    if auth_check:
        return auth_check

    service_name = request.form.get("service_name", "").strip()
    service_description = request.form.get("service_description", "").strip()
    price = request.form.get("price", "").strip()
    duration_minutes = request.form.get("duration_minutes", "").strip()

    if not all([service_name, price, duration_minutes]):
        flash("Service name, price and duration are required.", "error")
        return redirect(url_for("admin_panel.admin_dashboard"))

    try:
        price = float(price)
        duration_minutes = int(duration_minutes)
        if price <= 0 or duration_minutes <= 0:
            raise ValueError
    except ValueError:
        flash("Price and duration must be positive numbers.", "error")
        return redirect(url_for("admin_panel.admin_dashboard"))

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO services (service_name, service_description, price, duration_minutes) "
            "VALUES (%s, %s, %s, %s)",
            (service_name, service_description, price, duration_minutes),
        )
        connection.commit()
        flash(f"Service '{service_name}' added.", "success")
    except Exception as error:
        flash(f"Could not add the service: {error}", "error")
    finally:
        if connection:
            connection.close()

    return redirect(url_for("admin_panel.admin_dashboard"))


@admin_bp.route("/create_account", methods=["POST"])
def create_account():
    auth_check = admin_required()
    if auth_check:
        return auth_check

    username = request.form.get("username_inp", "").strip()
    password = request.form.get("password_inp", "").strip()
    role = request.form.get("role_inp", "").strip()
    email = request.form.get("email_inp", "").strip().lower()

    if not all([username, password, role, email]):
        flash("All account fields are required.", "error")
        return redirect(url_for("admin_panel.admin_dashboard"))

    if role not in ["admin", "client"]:
        flash("Role must be either admin or client.", "error")
        return redirect(url_for("admin_panel.admin_dashboard"))

    if len(username) < 3:
        flash("Username must be at least 3 characters long.", "error")
        return redirect(url_for("admin_panel.admin_dashboard"))

    if len(password) < 6:
        flash("Password must be at least 6 characters long.", "error")
        return redirect(url_for("admin_panel.admin_dashboard"))

    if "@" not in email or "." not in email.split("@")[-1]:
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("admin_panel.admin_dashboard"))

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO accounts (account_username, account_password, account_role, account_email) "
            "VALUES (%s, %s, %s, %s)",
            (username, generate_password_hash(password), role, email),
        )
        connection.commit()
        flash(f"Account '{username}' created.", "success")
    except IntegrityError:
        flash("That username or email is already in use.", "error")
    except Exception as error:
        flash(f"Could not create the account: {error}", "error")
    finally:
        if connection:
            connection.close()

    return redirect(url_for("admin_panel.admin_dashboard"))


@admin_bp.route("/delete_service", methods=["POST"])
def delete_service():
    auth_check = admin_required()
    if auth_check:
        return auth_check

    try:
        service_id = int(request.form.get("service_id", ""))
    except ValueError:
        flash("Invalid service ID.", "error")
        return redirect(url_for("admin_panel.admin_dashboard"))

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) AS booking_count FROM bookings "
            "WHERE service_id = %s AND status IN ('pending', 'confirmed', 'in_progress')",
            (service_id,),
        )
        if cursor.fetchone()["booking_count"] > 0:
            flash(
                "Cannot delete a service with active bookings. Complete or cancel them first.",
                "error",
            )
            return redirect(url_for("admin_panel.admin_dashboard"))

        cursor.execute("DELETE FROM services WHERE service_id = %s", (service_id,))
        connection.commit()
        if cursor.rowcount > 0:
            flash("Service deleted.", "success")
        else:
            flash("Service not found.", "error")
    except Exception as error:
        flash(f"Could not delete the service: {error}", "error")
    finally:
        if connection:
            connection.close()

    return redirect(url_for("admin_panel.admin_dashboard"))


@admin_bp.route("/delete_booking", methods=["POST"])
def delete_booking():
    auth_check = admin_required()
    if auth_check:
        return auth_check

    try:
        booking_id = int(request.form.get("booking_id", ""))
    except ValueError:
        flash("Invalid booking ID.", "error")
        return redirect(url_for("admin_panel.admin_dashboard"))

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM bookings WHERE booking_id = %s", (booking_id,))
        connection.commit()
        if cursor.rowcount > 0:
            flash("Booking deleted.", "success")
        else:
            flash("Booking not found.", "error")
    except Exception as error:
        flash(f"Could not delete the booking: {error}", "error")
    finally:
        if connection:
            connection.close()

    return redirect(url_for("admin_panel.admin_dashboard"))


@admin_bp.route("/delete_account", methods=["POST"])
def delete_account():
    auth_check = admin_required()
    if auth_check:
        return auth_check

    try:
        account_id = int(request.form.get("account_id", ""))
    except ValueError:
        flash("Invalid account ID.", "error")
        return redirect(url_for("admin_panel.admin_dashboard"))

    if account_id == session["account_logged_in"]["account_id"]:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("admin_panel.admin_dashboard"))

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) AS booking_count FROM bookings "
            "WHERE client_id = %s AND status IN ('pending', 'confirmed', 'in_progress')",
            (account_id,),
        )
        if cursor.fetchone()["booking_count"] > 0:
            flash(
                "Cannot delete an account with active bookings. Complete or cancel them first.",
                "error",
            )
            return redirect(url_for("admin_panel.admin_dashboard"))

        cursor.execute(
            "SELECT account_username FROM accounts WHERE account_id = %s", (account_id,)
        )
        account = cursor.fetchone()
        if not account:
            flash("Account not found.", "error")
            return redirect(url_for("admin_panel.admin_dashboard"))

        cursor.execute("DELETE FROM accounts WHERE account_id = %s", (account_id,))
        connection.commit()
        flash(f"Account '{account['account_username']}' deleted.", "success")
    except Exception as error:
        flash(f"Could not delete the account: {error}", "error")
    finally:
        if connection:
            connection.close()

    return redirect(url_for("admin_panel.admin_dashboard"))
