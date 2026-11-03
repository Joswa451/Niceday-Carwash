import logging
import os
import secrets
from datetime import date, datetime, time, timedelta

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from .admin_bp import admin_bp
from .api_bp import api_bp
from .auth_bp import auth_bp
from .client_bp import client_bp
from .config import LOCAL_TZ, Config
from .db import (
    ONLINE_PAYMENT_METHODS,
    PAYMENT_METHODS,
    ensure_db_initialized,
)
from .main_bp import main_bp

csrf = CSRFProtect()


def _to_local(value):
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.astimezone(LOCAL_TZ)
    return value


def create_app():
    project_root = os.path.dirname(os.path.dirname(__file__))
    frontend_root = os.path.join(project_root, "frontend")
    app = Flask(
        __name__,
        template_folder=os.path.join(frontend_root, "templates"),
        static_folder=os.path.join(frontend_root, "public", "static"),
        static_url_path="/static",
    )
    app.config.from_object(Config)

    app.logger.setLevel(logging.INFO)
    if not app.config.get("SECRET_KEY"):
        if os.environ.get("RENDER") or os.environ.get("VERCEL"):
            raise RuntimeError(
                "SECRET_KEY must be set as an environment variable in production."
            )
        app.config["SECRET_KEY"] = secrets.token_hex(32)
        app.logger.warning(
            "SECRET_KEY is not set. Using a random development key; "
            "sessions and API tokens will reset when the process restarts."
        )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    csrf.init_app(app)

    try:
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    except OSError:
        app.logger.warning("Could not create the upload folder.", exc_info=True)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(api_bp)
    csrf.exempt(api_bp)

    @app.before_request
    def _prepare_database():
        if request.endpoint == "static":
            return
        try:
            ensure_db_initialized()
        except RuntimeError as error:
            app.logger.warning("Database is not ready: %s", error)
        except Exception:
            app.logger.exception("Database initialization failed")

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )

        if request.path.startswith("/api"):
            configured = os.environ.get("CORS_ORIGINS", "*")
            origins = [
                item.strip().rstrip("/")
                for item in configured.split(",")
                if item.strip()
            ]
            origin = (request.headers.get("Origin") or "").rstrip("/")
            if "*" in origins or not origins:
                response.headers["Access-Control-Allow-Origin"] = "*"
            elif origin in origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization"
            )
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, PATCH, DELETE, OPTIONS"
            )
            response.headers["Access-Control-Max-Age"] = "86400"
        return response

    @app.template_filter("datefmt")
    def datefmt(value, fmt="%b %d, %Y"):
        if not value:
            return "N/A"
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return value
        value = _to_local(value)
        if isinstance(value, (datetime, date)):
            return value.strftime(fmt)
        return value

    @app.template_filter("timefmt")
    def timefmt(value):
        if not value:
            return "N/A"
        if isinstance(value, timedelta):
            total_minutes = int(value.total_seconds() // 60)
            hours, minutes = divmod(total_minutes, 60)
            value = time(hour=hours % 24, minute=minutes)
        if isinstance(value, datetime):
            value = _to_local(value)
            return value.strftime("%I:%M %p").lstrip("0")
        if isinstance(value, time):
            return value.strftime("%I:%M %p").lstrip("0")
        try:
            return (
                datetime.strptime(str(value)[:5], "%H:%M")
                .strftime("%I:%M %p")
                .lstrip("0")
            )
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
            "current_year": datetime.now(LOCAL_TZ).year,
            "payment_methods": PAYMENT_METHODS,
            "payment_labels": dict(PAYMENT_METHODS),
            "online_payment_methods": ONLINE_PAYMENT_METHODS,
        }

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        app.logger.warning("CSRF validation failed: %s", error.description)
        if request.path.startswith("/api"):
            return jsonify({"error": "Invalid or expired request token."}), 400
        flash("Your session expired. Please try again.", "error")
        return redirect(url_for("main_pages.landing_page"))

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api"):
            return jsonify({"error": "Not found."}), 404
        return (
            render_template(
                "error.html",
                code=404,
                title="Page not found",
                message="The page you are looking for does not exist.",
            ),
            404,
        )

    @app.errorhandler(405)
    def method_not_allowed(error):
        if request.path.startswith("/api"):
            return jsonify({"error": "Method not allowed."}), 405
        return error

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception("Unhandled server error")
        if request.path.startswith("/api"):
            return jsonify({"error": "Something went wrong."}), 500
        return (
            render_template(
                "error.html",
                code=500,
                title="Something went wrong",
                message="We could not complete your request. Please try again.",
            ),
            500,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
