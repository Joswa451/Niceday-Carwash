from flask import Blueprint, render_template, session, redirect, url_for

from db import get_db_connection

main_bp = Blueprint("main_pages", __name__)


@main_bp.route("/")
def landing_page():
    return render_template("index.html")


@main_bp.route("/about")
def about_page():
    return render_template("about.html")


@main_bp.route("/services")
def services_page():
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM services ORDER BY service_id")
        services = cursor.fetchall()
    finally:
        connection.close()
    return render_template("services.html", services=services)


@main_bp.route("/home")
def home_page():
    account = session.get("account_logged_in")
    if not account:
        return redirect(url_for("main_pages.landing_page"))
    if account["account_role"] == "admin":
        return redirect(url_for("admin_panel.admin_dashboard"))
    return redirect(url_for("main_pages.services_page"))
