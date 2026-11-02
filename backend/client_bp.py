import secrets
from datetime import datetime, time

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .config import LOCAL_TZ
from .db import ONLINE_PAYMENT_METHODS, PAYMENT_METHODS, get_db_connection

client_bp = Blueprint("client_services", __name__)


def client_required():
    account = session.get("account_logged_in")
    if not account:
        flash("Please log in to continue.", "error")
        return redirect(url_for("authentication.login_page"))
    if account["account_role"] != "client":
        flash("That page is for client accounts only.", "error")
        return redirect(url_for("admin_panel.admin_dashboard"))
    return None


@client_bp.route("/my-bookings")
def my_bookings_page():
    auth_check = client_required()
    if auth_check:
        return auth_check

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT b.*, s.service_name, s.price
            FROM bookings b
            JOIN services s ON b.service_id = s.service_id
            WHERE b.client_id = %s
            ORDER BY b.created_at DESC, b.booking_id DESC
            """,
            (session["account_logged_in"]["account_id"],),
        )
        bookings = cursor.fetchall()
    finally:
        connection.close()

    return render_template("my_bookings.html", bookings=bookings)


@client_bp.route("/book_service", methods=["POST"])
def book_service():
    auth_check = client_required()
    if auth_check:
        return auth_check

    service_id = request.form.get("service_id", "").strip()
    customer_name = request.form.get("customer_name", "").strip()
    customer_phone = request.form.get("customer_phone", "").strip()
    vehicle_type = request.form.get("vehicle_type", "").strip()
    booking_date = request.form.get("booking_date", "").strip()
    booking_time = request.form.get("booking_time", "").strip()
    notes = request.form.get("notes", "").strip()
    payment_method = request.form.get("payment_method", "").strip() or "cash"

    if not all([service_id, customer_name, vehicle_type, booking_date, booking_time]):
        flash("Service, name, vehicle type, date and time are required.", "error")
        return redirect(url_for("main_pages.services_page"))

    if payment_method not in dict(PAYMENT_METHODS):
        flash("Please choose a valid payment method.", "error")
        return redirect(url_for("main_pages.services_page"))

    try:
        service_id = int(service_id)
    except (TypeError, ValueError):
        flash("Invalid service selection.", "error")
        return redirect(url_for("main_pages.services_page"))

    try:
        chosen_date = datetime.strptime(booking_date, "%Y-%m-%d").date()
        chosen_time = datetime.strptime(booking_time, "%H:%M").time()
    except ValueError:
        flash("Invalid date or time format.", "error")
        return redirect(url_for("main_pages.services_page"))

    if chosen_date < datetime.now(LOCAL_TZ).date():
        flash("Please choose a date from today onward.", "error")
        return redirect(url_for("main_pages.services_page"))

    if chosen_time < time(6, 0) or chosen_time > time(18, 0):
        flash("Bookings are available between 6:00 AM and 6:00 PM.", "error")
        return redirect(url_for("main_pages.services_page"))

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT service_id FROM services WHERE service_id = %s", (service_id,)
        )
        if not cursor.fetchone():
            flash("The selected service no longer exists.", "error")
            return redirect(url_for("main_pages.services_page"))

        cursor.execute(
            "INSERT INTO bookings "
            "(client_id, service_id, customer_name, customer_phone, vehicle_type, "
            "booking_date, booking_time, notes, payment_method) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING booking_id",
            (
                session["account_logged_in"]["account_id"],
                service_id,
                customer_name,
                customer_phone or None,
                vehicle_type,
                chosen_date.isoformat(),
                chosen_time.strftime("%H:%M"),
                notes or None,
                payment_method,
            ),
        )
        booking_id = cursor.fetchone()["booking_id"]
        connection.commit()

        if payment_method in ONLINE_PAYMENT_METHODS:
            flash("Booking created. Please complete your online payment.", "info")
            return redirect(
                url_for("client_services.payment_page", booking_id=booking_id)
            )

        flash("Booking created successfully. We will see you soon!", "success")
    except Exception:
        current_app.logger.exception("Could not create booking")
        flash("Could not create the booking. Please try again.", "error")
    finally:
        if connection:
            connection.close()

    return redirect(url_for("main_pages.services_page"))


@client_bp.route("/payment/<int:booking_id>", methods=["GET", "POST"])
def payment_page(booking_id):
    auth_check = client_required()
    if auth_check:
        return auth_check

    account_id = session["account_logged_in"]["account_id"]
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT b.*, s.service_name, s.price
            FROM bookings b
            JOIN services s ON b.service_id = s.service_id
            WHERE b.booking_id = %s AND b.client_id = %s
            """,
            (booking_id, account_id),
        )
        booking = cursor.fetchone()

        if not booking:
            flash("Booking not found or access denied.", "error")
            return redirect(url_for("client_services.my_bookings_page"))

        if request.method == "POST":
            if booking["payment_status"] == "paid":
                flash("This booking is already paid.", "info")
            elif booking["status"] == "cancelled":
                flash("Cancelled bookings cannot be paid online.", "error")
            elif booking["payment_method"] not in ONLINE_PAYMENT_METHODS:
                flash("This booking is set to pay with cash at the counter.", "error")
            else:
                reference = (
                    f"PAY-{datetime.now(LOCAL_TZ):%Y%m%d}-"
                    f"{secrets.token_hex(3).upper()}"
                )
                cursor.execute(
                    "UPDATE bookings SET payment_status = 'paid', "
                    "payment_reference = %s, paid_at = CURRENT_TIMESTAMP "
                    "WHERE booking_id = %s AND client_id = %s "
                    "AND payment_status = 'unpaid' AND status <> 'cancelled' "
                    "AND payment_method IN ('gcash', 'maya', 'bank_transfer')",
                    (reference, booking_id, account_id),
                )
                connection.commit()
                if cursor.rowcount > 0:
                    flash(
                        f"Payment successful. Reference: {reference}",
                        "success",
                    )
                else:
                    flash("Payment could not be processed. Please refresh.", "error")
            return redirect(url_for("client_services.my_bookings_page"))

        return render_template(
            "payment.html",
            booking=booking,
            online_payment=booking["payment_method"] in ONLINE_PAYMENT_METHODS,
        )
    finally:
        connection.close()


@client_bp.route("/booking_process", methods=["POST"])
def booking_process():
    account = session.get("account_logged_in")
    if not account:
        flash("Please log in to continue.", "error")
        return redirect(url_for("authentication.login_page"))

    action = request.form.get("action", "").strip()
    booking_id = request.form.get("booking_id", "").strip()

    if not action or not booking_id:
        flash("Invalid booking action.", "error")
        return redirect(url_for("main_pages.landing_page"))

    try:
        booking_id = int(booking_id)
    except (TypeError, ValueError):
        flash("Invalid booking ID.", "error")
        return redirect(url_for("main_pages.landing_page"))

    is_admin = account["account_role"] == "admin"
    redirect_target = (
        url_for("admin_panel.admin_dashboard")
        if is_admin
        else url_for("client_services.my_bookings_page")
    )

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        if is_admin:
            cursor.execute(
                "SELECT booking_id, status, payment_method, payment_status, "
                "payment_reference FROM bookings WHERE booking_id = %s",
                (booking_id,),
            )
        else:
            cursor.execute(
                "SELECT booking_id, status, payment_method, payment_status, "
                "payment_reference FROM bookings "
                "WHERE booking_id = %s AND client_id = %s",
                (booking_id, account["account_id"]),
            )

        booking = cursor.fetchone()
        if not booking:
            flash("Booking not found or access denied.", "error")
            return redirect(redirect_target)

        if action == "cancel":
            if not is_admin and booking["status"] not in ("pending", "confirmed"):
                flash("This booking can no longer be cancelled.", "error")
                return redirect(redirect_target)
            if booking["status"] == "cancelled":
                flash("This booking is already cancelled.", "info")
                return redirect(redirect_target)
            cursor.execute(
                "UPDATE bookings SET status = 'cancelled' WHERE booking_id = %s",
                (booking_id,),
            )
            connection.commit()
            flash("Booking cancelled.", "success")
        elif action == "update_status" and is_admin:
            new_status = request.form.get("status", "").strip()
            valid_statuses = [
                "pending",
                "confirmed",
                "in_progress",
                "completed",
                "cancelled",
            ]
            if new_status not in valid_statuses:
                flash("Invalid booking status.", "error")
                return redirect(redirect_target)
            cursor.execute(
                "UPDATE bookings SET status = %s WHERE booking_id = %s",
                (new_status, booking_id),
            )
            connection.commit()
            flash("Booking status updated.", "success")
        elif action == "mark_paid" and is_admin:
            if booking["status"] == "cancelled":
                flash("Cancelled bookings cannot be marked as paid.", "error")
                return redirect(redirect_target)
            if booking["payment_status"] == "paid":
                flash("This booking is already paid.", "info")
                return redirect(redirect_target)
            reference = booking["payment_reference"] or (
                f"MANUAL-{datetime.now(LOCAL_TZ):%Y%m%d}-"
                f"{secrets.token_hex(3).upper()}"
            )
            cursor.execute(
                "UPDATE bookings SET payment_status = 'paid', "
                "payment_reference = %s, paid_at = CURRENT_TIMESTAMP "
                "WHERE booking_id = %s AND payment_status = 'unpaid' "
                "AND status <> 'cancelled'",
                (reference, booking_id),
            )
            connection.commit()
            if cursor.rowcount > 0:
                flash(f"Payment recorded. Reference: {reference}", "success")
            else:
                flash("Payment could not be recorded. Please refresh.", "error")
        else:
            flash("Invalid action for this account.", "error")
            return redirect(redirect_target)
    except Exception:
        current_app.logger.exception(
            "Could not process booking action %r for booking %s",
            action,
            booking_id,
        )
        flash("Could not process the booking. Please try again.", "error")
    finally:
        if connection:
            connection.close()

    return redirect(redirect_target)
