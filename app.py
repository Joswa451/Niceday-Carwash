import os
from datetime import datetime, time, timedelta

from flask import Flask

from config import Config
from db import PAYMENT_METHODS, init_db
from main_bp import main_bp
from auth_bp import auth_bp
from admin_bp import admin_bp
from client_bp import client_bp


def create_app():
    static_folder = os.path.join(os.path.dirname(__file__), "public", "static")
    app = Flask(
        __name__,
        static_folder=static_folder,
        static_url_path="/static",
    )
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(client_bp)

    @app.template_filter("datefmt")
    def datefmt(value, fmt="%b %d, %Y"):
        if not value:
            return "N/A"
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return value
        return value.strftime(fmt)

    @app.template_filter("timefmt")
    def timefmt(value):
        if not value:
            return "N/A"
        if isinstance(value, timedelta):
            total_minutes = int(value.total_seconds() // 60)
            hours, minutes = divmod(total_minutes, 60)
            value = time(hour=hours % 24, minute=minutes)
        if isinstance(value, datetime):
            return value.strftime("%I:%M %p").lstrip("0")
        if isinstance(value, time):
            return value.strftime("%I:%M %p").lstrip("0")
        try:
            return datetime.strptime(str(value)[:5], "%H:%M").strftime("%I:%M %p").lstrip("0")
        except ValueError:
            return value

    @app.template_filter("money")
    def money(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return value
        if number.is_integer():
            return f"{number:,.0f}"
        return f"{number:,.2f}"

    @app.context_processor
    def inject_globals():
        return {
            "current_year": datetime.now().year,
            "payment_methods": PAYMENT_METHODS,
            "payment_labels": dict(PAYMENT_METHODS),
        }

    init_db()
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
