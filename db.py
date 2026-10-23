import os

import pymysql
from pymysql.cursors import DictCursor
from werkzeug.security import generate_password_hash

from config import Config

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS accounts (
        account_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
        account_username VARCHAR(100) NOT NULL,
        account_password VARCHAR(255) NOT NULL,
        account_role VARCHAR(20) NOT NULL DEFAULT 'client',
        account_email VARCHAR(255) DEFAULT NULL,
        full_name VARCHAR(150) DEFAULT NULL,
        phone VARCHAR(30) DEFAULT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (account_id),
        UNIQUE KEY uq_accounts_username (account_username),
        UNIQUE KEY uq_accounts_email (account_email)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS services (
        service_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
        service_name VARCHAR(150) NOT NULL,
        service_description TEXT,
        price DECIMAL(10, 2) NOT NULL,
        duration_minutes INT UNSIGNED NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (service_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS bookings (
        booking_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
        client_id INT UNSIGNED NOT NULL,
        service_id INT UNSIGNED NOT NULL,
        customer_name VARCHAR(150) NOT NULL,
        customer_phone VARCHAR(30) DEFAULT NULL,
        vehicle_type VARCHAR(100) NOT NULL,
        booking_date DATE NOT NULL,
        booking_time TIME NOT NULL,
        notes TEXT,
        payment_method VARCHAR(30) NOT NULL DEFAULT 'cash',
        payment_status VARCHAR(20) NOT NULL DEFAULT 'unpaid',
        payment_reference VARCHAR(100) DEFAULT NULL,
        paid_at TIMESTAMP NULL DEFAULT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (booking_id),
        KEY idx_bookings_client_id (client_id),
        KEY idx_bookings_service_id (service_id),
        KEY idx_bookings_status (status),
        KEY idx_bookings_date (booking_date),
        CONSTRAINT fk_bookings_client
            FOREIGN KEY (client_id) REFERENCES accounts (account_id)
            ON DELETE CASCADE ON UPDATE CASCADE,
        CONSTRAINT fk_bookings_service
            FOREIGN KEY (service_id) REFERENCES services (service_id)
            ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]

PAYMENT_METHODS = [
    ("cash", "Cash"),
    ("gcash", "GCash"),
    ("maya", "Maya"),
    ("bank_transfer", "Bank Transfer"),
]

ONLINE_PAYMENT_METHODS = {"gcash", "maya", "bank_transfer"}

BOOKING_PAYMENT_COLUMNS = [
    ("payment_method", "VARCHAR(30) NOT NULL DEFAULT 'cash' AFTER notes"),
    ("payment_status", "VARCHAR(20) NOT NULL DEFAULT 'unpaid' AFTER payment_method"),
    ("payment_reference", "VARCHAR(100) DEFAULT NULL AFTER payment_status"),
    ("paid_at", "TIMESTAMP NULL DEFAULT NULL AFTER payment_reference"),
]

SEED_SERVICES = [
    ("Basic Wash", "Exterior wash, tire cleaning, interior vacuum and windows.", 150, 30),
    ("Premium Wash", "Full exterior wash and wax with deep interior cleaning.", 300, 60),
    ("Deluxe Detail", "Premium wash, ceramic coating, leather care and paint protection.", 500, 120),
    ("Express Service", "A quick exterior rinse and vacuum for busy days.", 100, 15),
    ("SUV/Truck Special", "Heavy-duty cleaning for larger vehicles, inside and out.", 400, 90),
    ("Eco-Friendly Wash", "Water-saving wash using biodegradable products.", 250, 45),
]

DEFAULT_ADMIN = {
    "username": "admin",
    "password": os.environ.get("DEFAULT_ADMIN_PASSWORD"),
    "email": "admin@nicedaycarwash.local",
}


def _connect(database=None):
    connect_kwargs = dict(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
        connect_timeout=10,
    )
    if Config.MYSQL_SSL:
        ssl_config = {}
        if Config.MYSQL_SSL_CA:
            ssl_config["ca"] = Config.MYSQL_SSL_CA
        connect_kwargs["ssl"] = ssl_config
    return pymysql.connect(**connect_kwargs)


def _ensure_database():
    database = Config.MYSQL_DATABASE.replace("`", "``")
    connection = _connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        connection.commit()
    finally:
        connection.close()


def _initialize(connection):
    with connection.cursor() as cursor:
        for statement in SCHEMA:
            cursor.execute(statement)

        for column, definition in BOOKING_PAYMENT_COLUMNS:
            cursor.execute(
                "SELECT COUNT(*) AS column_count FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'bookings' "
                "AND COLUMN_NAME = %s",
                (Config.MYSQL_DATABASE, column),
            )
            if cursor.fetchone()["column_count"] == 0:
                cursor.execute(
                    f"ALTER TABLE bookings ADD COLUMN `{column}` {definition}"
                )

        cursor.execute("SELECT COUNT(*) AS service_count FROM services")
        if cursor.fetchone()["service_count"] == 0:
            cursor.executemany(
                "INSERT INTO services (service_name, service_description, price, duration_minutes) "
                "VALUES (%s, %s, %s, %s)",
                SEED_SERVICES,
            )

        cursor.execute(
            "SELECT COUNT(*) AS account_count FROM accounts WHERE account_username = %s",
            (DEFAULT_ADMIN["username"],),
        )
        if cursor.fetchone()["account_count"] == 0:
            if not DEFAULT_ADMIN["password"]:
                raise RuntimeError(
                    "Set DEFAULT_ADMIN_PASSWORD before initializing a new database."
                )
            cursor.execute(
                "INSERT INTO accounts (account_username, account_password, account_role, account_email, full_name) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    DEFAULT_ADMIN["username"],
                    generate_password_hash(DEFAULT_ADMIN["password"]),
                    "admin",
                    DEFAULT_ADMIN["email"],
                    "Administrator",
                ),
            )

    connection.commit()


def get_db_connection():
    return _connect(Config.MYSQL_DATABASE)


def init_db():
    _ensure_database()
    connection = get_db_connection()
    try:
        _initialize(connection)
    finally:
        connection.close()
