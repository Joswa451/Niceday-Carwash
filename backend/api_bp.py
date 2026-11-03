"""JSON API used by the standalone React frontend."""
import secrets
from datetime import date, datetime, time
from decimal import Decimal
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from .config import LOCAL_TZ
from .db import (
    INTEGRITY_ERRORS,
    ONLINE_PAYMENT_METHODS,
    PAYMENT_METHODS,
    get_db_connection,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")

TOKEN_SALT = "niceday-carwash-api-auth"
TOKEN_MAX_AGE = 12 * 60 * 60
VALID_STATUSES = ["pending", "confirmed", "in_progress", "completed", "cancelled"]


def _serializer():
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"], salt=TOKEN_SALT
    )


def _jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def ok(data=None, status=200, **extra):
    payload = dict(extra)
    if data is not None:
        payload["data"] = data
    return jsonify(_jsonable(payload)), status


def fail(message, status=400, **extra):
    return jsonify({"error": message, **_jsonable(extra)}), status


def payload():
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    return request.form.to_dict()


def field(data, *names, default=""):
    for name in names:
        if name in data and data[name] is not None:
            return str(data[name]).strip()
    return default


def password_version(password_hash):
    return (password_hash or "")[-16:]


def issue_token(account):
    return _serializer().dumps(
        {
            "account_id": account["account_id"],
            "pv": password_version(account["account_password"]),
        }
    )


def user_payload(account):
    return {
        "account_id": account["account_id"],
        "account_username": account["account_username"],
        "account_role": account["account_role"],
        "account_email": account["account_email"],
        "full_name": account["full_name"],
        "phone": account["phone"],
    }


def current_account():
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    token = header[7:].strip()
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT * FROM accounts WHERE account_id = %s",
            (data.get("account_id"),),
        )
        account = cursor.fetchone()
        if not account:
            return None
        if data.get("pv") != password_version(account["account_password"]):
            return None
        return account
    except Exception:
        current_app.logger.exception("Could not validate API token")
        return None
    finally:
        if connection:
            connection.close()


def token_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            account = current_account()
            if not account:
                return fail("Please log in to continue.", 401)
            if role and account["account_role"] != role:
                return fail("Access denied.", 403)
            g.current_account = account
            return view(*args, **kwargs)

        return wrapper

    return decorator


def _fetch_one(sql, params=()):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        return cursor.fetchone()
    finally:
        connection.close()


def _fetch_all(sql, params=()):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        connection.close()


@api_bp.get("/health")
def health():
    return ok({"status": "healthy"})


@api_bp.post("/auth/register")
def register():
    data = payload()
    full_name = field(data, "fullName", "full_name")
    username = field(data, "username")
    email = field(data, "email").lower()
    phone = field(data, "phone")
    password = field(data, "password")
    confirm_password = field(data, "confirmPassword", "confirm_password")

    if not all([full_name, username, email, password]):
        return fail("Full name, username, email and password are required.")

    if confirm_password and password != confirm_password:
        return fail("Passwords do not match.")

    if len(username) < 3:
        return fail("Username must be at least 3 characters long.")

    if len(password) < 6:
        return fail("Password must be at least 6 characters long.")

    if "@" not in email or "." not in email.split("@")[-1]:
        return fail("Please enter a valid email address.")

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT account_id FROM accounts WHERE account_username = %s",
            (username,),
        )
        if cursor.fetchone():
            return fail(f"Username '{username}' already exists.", 409)

        cursor.execute(
            "SELECT account_id FROM accounts WHERE account_email = %s", (email,)
        )
        if cursor.fetchone():
            return fail(f"Email '{email}' is already registered.", 409)

        cursor.execute(
            "INSERT INTO accounts "
            "(account_username, account_password, account_role, account_email, "
            "full_name, phone) VALUES (%s, %s, %s, %s, %s, %s) RETURNING account_id",
            (
                username,
                generate_password_hash(password),
                "client",
                email,
                full_name,
                phone or None,
            ),
        )
        account_id = cursor.fetchone()["account_id"]
        connection.commit()
        cursor.execute(
            "SELECT * FROM accounts WHERE account_id = %s", (account_id,)
        )
        account = cursor.fetchone()
        return ok(
            {
                "account_id": account_id,
                "token": issue_token(account),
                "user": user_payload(account),
            },
            status=201,
            message="Account created successfully.",
        )
    except INTEGRITY_ERRORS:
        if connection:
            connection.rollback()
        return fail("That username or email is already in use.", 409)
    except Exception:
        current_app.logger.exception("API registration failed for %r", username)
        return fail("Could not create your account. Please try again.", 500)
    finally:
        if connection:
            connection.close()


@api_bp.post("/auth/login")
def login():
    data = payload()
    username = field(data, "username", "user_inp")
    password = field(data, "password", "pass_inp")
    admin_only = str(
        field(data, "adminOnly", "admin_only", default="false")
    ).lower() in ("1", "true", "yes", "on")

    if not username or not password:
        return fail("Username and password are required.")

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT * FROM accounts WHERE account_username = %s", (username,)
        )
        account = cursor.fetchone()

        if not account:
            return fail("Invalid username or password.", 401)

        stored_password = account["account_password"]
        password_ok = False
        if stored_password.startswith(("scrypt:", "pbkdf2:", "argon2")):
            password_ok = check_password_hash(stored_password, password)
        else:
            password_ok = stored_password == password
            if password_ok:
                new_hash = generate_password_hash(password)
                cursor.execute(
                    "UPDATE accounts SET account_password = %s "
                    "WHERE account_id = %s",
                    (new_hash, account["account_id"]),
                )
                connection.commit()
                account = dict(account)
                account["account_password"] = new_hash

        if not password_ok:
            return fail("Invalid username or password.", 401)

        if admin_only and account["account_role"] != "admin":
            return fail("This login is for administrators only.", 403)

        return ok(
            {
                "token": issue_token(account),
                "user": user_payload(account),
            },
            message="Signed in successfully.",
        )
    except Exception:
        current_app.logger.exception("API login failed for user %r", username)
        return fail("Login is temporarily unavailable. Please try again.", 500)
    finally:
        if connection:
            connection.close()


@api_bp.get("/auth/me")
@token_required()
def me():
    return ok({"user": user_payload(g.current_account)})


@api_bp.post("/auth/change-password")
@token_required()
def change_password():
    data = payload()
    current_password = field(data, "currentPassword", "current_password")
    new_password = field(data, "newPassword", "new_password")

    if not current_password or not new_password:
        return fail("Current and new passwords are required.")

    if len(new_password) < 8:
        return fail("New password must be at least 8 characters long.")

    if new_password == current_password:
        return fail("Choose a password different from your current one.")

    account = g.current_account
    if not check_password_hash(account["account_password"], current_password):
        return fail("Your current password is incorrect.", 400)

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        new_hash = generate_password_hash(new_password)
        cursor.execute(
            "UPDATE accounts SET account_password = %s WHERE account_id = %s",
            (new_hash, account["account_id"]),
        )
        connection.commit()
        account = dict(account)
        account["account_password"] = new_hash
        return ok(
            {"token": issue_token(account)},
            message="Password updated successfully.",
        )
    except Exception:
        current_app.logger.exception(
            "API password change failed for account %s", account["account_id"]
        )
        return fail("Could not update your password. Please try again.", 500)
    finally:
        if connection:
            connection.close()


@api_bp.get("/services")
def list_services():
    services = _fetch_all("SELECT * FROM services ORDER BY service_id")
    return ok({"services": services})


@api_bp.get("/bookings")
@token_required()
def list_bookings():
    account = g.current_account
    if account["account_role"] == "admin":
        bookings = _fetch_all(
            """
            SELECT b.*, s.service_name, s.price,
                   a.account_username AS client_name
            FROM bookings b
            JOIN services s ON b.service_id = s.service_id
            JOIN accounts a ON b.client_id = a.account_id
            ORDER BY b.created_at DESC, b.booking_id DESC
            """
        )
    else:
        bookings = _fetch_all(
            """
            SELECT b.*, s.service_name, s.price
            FROM bookings b
            JOIN services s ON b.service_id = s.service_id
            WHERE b.client_id = %s
            ORDER BY b.created_at DESC, b.booking_id DESC
            """,
            (account["account_id"],),
        )
    return ok({"bookings": bookings})


@api_bp.get("/bookings/<int:booking_id>")
@token_required()
def get_booking(booking_id):
    account = g.current_account
    if account["account_role"] == "admin":
        booking = _fetch_one(
            """
            SELECT b.*, s.service_name, s.price,
                   a.account_username AS client_name
            FROM bookings b
            JOIN services s ON b.service_id = s.service_id
            JOIN accounts a ON b.client_id = a.account_id
            WHERE b.booking_id = %s
            """,
            (booking_id,),
        )
    else:
        booking = _fetch_one(
            """
            SELECT b.*, s.service_name, s.price
            FROM bookings b
            JOIN services s ON b.service_id = s.service_id
            WHERE b.booking_id = %s AND b.client_id = %s
            """,
            (booking_id, account["account_id"]),
        )
    if not booking:
        return fail("Booking not found or access denied.", 404)
    return ok({"booking": booking})


@api_bp.post("/bookings")
@token_required(role="client")
def create_booking():
    data = payload()
    service_id = field(data, "serviceId", "service_id")
    customer_name = field(data, "customerName", "customer_name")
    customer_phone = field(data, "customerPhone", "customer_phone")
    vehicle_type = field(data, "vehicleType", "vehicle_type")
    booking_date = field(data, "bookingDate", "booking_date")
    booking_time = field(data, "bookingTime", "booking_time")
    notes = field(data, "notes")
    payment_method = field(data, "paymentMethod", "payment_method", default="cash")

    if not all([service_id, customer_name, vehicle_type, booking_date, booking_time]):
        return fail("Service, name, vehicle type, date and time are required.")

    if payment_method not in dict(PAYMENT_METHODS):
        return fail("Please choose a valid payment method.")

    try:
        service_id = int(service_id)
    except (TypeError, ValueError):
        return fail("Invalid service selection.")

    try:
        chosen_date = datetime.strptime(booking_date, "%Y-%m-%d").date()
        chosen_time = datetime.strptime(booking_time, "%H:%M").time()
    except ValueError:
        return fail("Invalid date or time format.")

    if chosen_date < datetime.now(LOCAL_TZ).date():
        return fail("Please choose a date from today onward.")

    if chosen_time < time(6, 0) or chosen_time > time(18, 0):
        return fail("Bookings are available between 6:00 AM and 6:00 PM.")

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT service_id FROM services WHERE service_id = %s", (service_id,)
        )
        if not cursor.fetchone():
            return fail("The selected service no longer exists.", 404)

        cursor.execute(
            "INSERT INTO bookings "
            "(client_id, service_id, customer_name, customer_phone, vehicle_type, "
            "booking_date, booking_time, notes, payment_method) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING booking_id",
            (
                g.current_account["account_id"],
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

        booking = _fetch_one(
            """
            SELECT b.*, s.service_name, s.price
            FROM bookings b
            JOIN services s ON b.service_id = s.service_id
            WHERE b.booking_id = %s
            """,
            (booking_id,),
        )
        return ok(
            {
                "booking": booking,
                "requiresPayment": payment_method in ONLINE_PAYMENT_METHODS,
            },
            status=201,
            message="Booking created successfully.",
        )
    except Exception:
        current_app.logger.exception("API could not create booking")
        return fail("Could not create the booking. Please try again.", 500)
    finally:
        if connection:
            connection.close()


@api_bp.post("/bookings/<int:booking_id>/cancel")
@token_required()
def cancel_booking(booking_id):
    account = g.current_account
    is_admin = account["account_role"] == "admin"
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        if is_admin:
            cursor.execute(
                "SELECT booking_id, status FROM bookings WHERE booking_id = %s",
                (booking_id,),
            )
        else:
            cursor.execute(
                "SELECT booking_id, status FROM bookings "
                "WHERE booking_id = %s AND client_id = %s",
                (booking_id, account["account_id"]),
            )
        booking = cursor.fetchone()
        if not booking:
            return fail("Booking not found or access denied.", 404)
        if booking["status"] == "cancelled":
            return fail("This booking is already cancelled.", 409)
        if not is_admin and booking["status"] not in ("pending", "confirmed"):
            return fail("This booking can no longer be cancelled.", 409)

        cursor.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE booking_id = %s",
            (booking_id,),
        )
        connection.commit()
        return ok(message="Booking cancelled.")
    except Exception:
        current_app.logger.exception("API could not cancel booking %s", booking_id)
        return fail("Could not cancel the booking. Please try again.", 500)
    finally:
        if connection:
            connection.close()


@api_bp.patch("/bookings/<int:booking_id>/status")
@token_required(role="admin")
def update_booking_status(booking_id):
    data = payload()
    new_status = field(data, "status")
    if new_status not in VALID_STATUSES:
        return fail("Invalid booking status.")

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE bookings SET status = %s WHERE booking_id = %s",
            (new_status, booking_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return fail("Booking not found.", 404)
        return ok(message="Booking status updated.")
    except Exception:
        current_app.logger.exception(
            "API could not update booking %s", booking_id
        )
        return fail("Could not update the booking. Please try again.", 500)
    finally:
        if connection:
            connection.close()


@api_bp.post("/bookings/<int:booking_id>/pay")
@token_required(role="client")
def pay_booking(booking_id):
    account = g.current_account
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT * FROM bookings WHERE booking_id = %s AND client_id = %s",
            (booking_id, account["account_id"]),
        )
        booking = cursor.fetchone()
        if not booking:
            return fail("Booking not found or access denied.", 404)
        if booking["payment_status"] == "paid":
            return fail("This booking is already paid.", 409)
        if booking["status"] == "cancelled":
            return fail("Cancelled bookings cannot be paid.", 409)
        if booking["payment_method"] not in ONLINE_PAYMENT_METHODS:
            return fail("This booking is set to pay with cash at the counter.", 400)

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
            (reference, booking_id, account["account_id"]),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return fail("Payment could not be processed. Please refresh.", 409)
        return ok({"reference": reference}, message="Payment successful.")
    except Exception:
        current_app.logger.exception("API could not pay booking %s", booking_id)
        return fail("Could not process the payment. Please try again.", 500)
    finally:
        if connection:
            connection.close()


@api_bp.post("/bookings/<int:booking_id>/mark-paid")
@token_required(role="admin")
def mark_booking_paid(booking_id):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT status, payment_status, payment_reference "
            "FROM bookings WHERE booking_id = %s",
            (booking_id,),
        )
        booking = cursor.fetchone()
        if not booking:
            return fail("Booking not found.", 404)
        if booking["status"] == "cancelled":
            return fail("Cancelled bookings cannot be marked as paid.", 409)
        if booking["payment_status"] == "paid":
            return fail("This booking is already paid.", 409)

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
        if cursor.rowcount == 0:
            return fail("Payment could not be recorded. Please refresh.", 409)
        return ok({"reference": reference}, message="Payment recorded.")
    except Exception:
        current_app.logger.exception(
            "API could not mark booking %s paid", booking_id
        )
        return fail("Could not record the payment. Please try again.", 500)
    finally:
        if connection:
            connection.close()


@api_bp.delete("/bookings/<int:booking_id>")
@token_required(role="admin")
def delete_booking(booking_id):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT status FROM bookings WHERE booking_id = %s", (booking_id,)
        )
        booking = cursor.fetchone()
        if not booking:
            return fail("Booking not found.", 404)
        if booking["status"] == "completed":
            return fail(
                "Completed bookings cannot be deleted. Keep them for your records.",
                409,
            )

        cursor.execute("DELETE FROM bookings WHERE booking_id = %s", (booking_id,))
        connection.commit()
        return ok(message="Booking deleted.")
    except Exception:
        current_app.logger.exception("API could not delete booking %s", booking_id)
        return fail("Could not delete the booking. Please try again.", 500)
    finally:
        if connection:
            connection.close()


@api_bp.get("/admin/dashboard")
@token_required(role="admin")
def admin_dashboard():
    bookings = _fetch_all(
        """
        SELECT b.*, s.service_name, s.price,
               a.account_username AS client_name
        FROM bookings b
        JOIN services s ON b.service_id = s.service_id
        JOIN accounts a ON b.client_id = a.account_id
        ORDER BY b.created_at DESC, b.booking_id DESC
        """
    )
    services = _fetch_all("SELECT * FROM services ORDER BY service_name")
    accounts = _fetch_all(
        "SELECT account_id, account_username, account_role, account_email, "
        "full_name, phone, created_at FROM accounts ORDER BY created_at DESC"
    )
    return ok(
        {
            "bookings": bookings,
            "services": services,
            "accounts": accounts,
        }
    )


@api_bp.post("/admin/services")
@token_required(role="admin")
def create_service():
    data = payload()
    service_name = field(data, "serviceName", "service_name")
    service_description = field(data, "serviceDescription", "service_description")
    price = field(data, "price")
    duration_minutes = field(data, "durationMinutes", "duration_minutes")

    if not all([service_name, price, duration_minutes]):
        return fail("Service name, price and duration are required.")

    try:
        price_value = float(price)
        duration_value = int(duration_minutes)
        if price_value <= 0 or duration_value <= 0:
            raise ValueError
    except ValueError:
        return fail("Price and duration must be positive numbers.")

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO services "
            "(service_name, service_description, price, duration_minutes) "
            "VALUES (%s, %s, %s, %s) RETURNING service_id",
            (
                service_name,
                service_description or None,
                price_value,
                duration_value,
            ),
        )
        service_id = cursor.fetchone()["service_id"]
        connection.commit()
        return ok(
            {"service_id": service_id},
            status=201,
            message=f"Service '{service_name}' added.",
        )
    except Exception:
        current_app.logger.exception("API could not add service %r", service_name)
        return fail("Could not add the service. Please try again.", 500)
    finally:
        if connection:
            connection.close()


@api_bp.delete("/admin/services/<int:service_id>")
@token_required(role="admin")
def delete_service(service_id):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS booking_count FROM bookings "
            "WHERE service_id = %s AND status IN "
            "('pending', 'confirmed', 'in_progress')",
            (service_id,),
        )
        if cursor.fetchone()["booking_count"] > 0:
            return fail(
                "Cannot delete a service with active bookings. "
                "Complete or cancel them first.",
                409,
            )

        cursor.execute(
            "DELETE FROM services WHERE service_id = %s", (service_id,)
        )
        connection.commit()
        if cursor.rowcount == 0:
            return fail("Service not found.", 404)
        return ok(message="Service deleted.")
    except Exception:
        current_app.logger.exception("API could not delete service %s", service_id)
        return fail("Could not delete the service. Please try again.", 500)
    finally:
        if connection:
            connection.close()


@api_bp.get("/admin/accounts")
@token_required(role="admin")
def list_accounts():
    accounts = _fetch_all(
        "SELECT account_id, account_username, account_role, account_email, "
        "full_name, phone, created_at FROM accounts ORDER BY created_at DESC"
    )
    return ok({"accounts": accounts})


@api_bp.post("/admin/accounts")
@token_required(role="admin")
def create_account():
    data = payload()
    username = field(data, "username", "username_inp")
    password = field(data, "password", "password_inp")
    role = field(data, "role", "role_inp")
    email = field(data, "email", "email_inp").lower()

    if not all([username, password, role, email]):
        return fail("All account fields are required.")

    if role not in ["admin", "client"]:
        return fail("Role must be either admin or client.")

    if len(username) < 3:
        return fail("Username must be at least 3 characters long.")

    if len(password) < 6:
        return fail("Password must be at least 6 characters long.")

    if "@" not in email or "." not in email.split("@")[-1]:
        return fail("Please enter a valid email address.")

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO accounts "
            "(account_username, account_password, account_role, account_email) "
            "VALUES (%s, %s, %s, %s) RETURNING account_id",
            (username, generate_password_hash(password), role, email),
        )
        account_id = cursor.fetchone()["account_id"]
        connection.commit()
        return ok(
            {"account_id": account_id},
            status=201,
            message=f"Account '{username}' created.",
        )
    except INTEGRITY_ERRORS:
        if connection:
            connection.rollback()
        return fail("That username or email is already in use.", 409)
    except Exception:
        current_app.logger.exception("API could not create account %r", username)
        return fail("Could not create the account. Please try again.", 500)
    finally:
        if connection:
            connection.close()


@api_bp.delete("/admin/accounts/<int:account_id>")
@token_required(role="admin")
def delete_account(account_id):
    if account_id == g.current_account["account_id"]:
        return fail("You cannot delete your own account.", 400)

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS booking_count FROM bookings "
            "WHERE client_id = %s AND status IN "
            "('pending', 'confirmed', 'in_progress')",
            (account_id,),
        )
        if cursor.fetchone()["booking_count"] > 0:
            return fail(
                "Cannot delete an account with active bookings. "
                "Complete or cancel them first.",
                409,
            )

        cursor.execute(
            "SELECT account_username FROM accounts WHERE account_id = %s",
            (account_id,),
        )
        account = cursor.fetchone()
        if not account:
            return fail("Account not found.", 404)

        cursor.execute(
            "DELETE FROM accounts WHERE account_id = %s", (account_id,)
        )
        connection.commit()
        return ok(
            message=f"Account '{account['account_username']}' deleted."
        )
    except Exception:
        current_app.logger.exception(
            "API could not delete account %s", account_id
        )
        return fail("Could not delete the account. Please try again.", 500)
    finally:
        if connection:
            connection.close()
