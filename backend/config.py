import os
from datetime import timedelta, timezone
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

ENV_CANDIDATES = [
    os.path.join(BASE_DIR, ".env"),
    os.path.join(BASE_DIR, "backend.env"),
    os.path.join(PROJECT_ROOT, ".env"),
]
for env_path in ENV_CANDIDATES:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

try:
    from zoneinfo import ZoneInfo

    LOCAL_TZ = ZoneInfo(os.environ.get("APP_TIMEZONE", "Asia/Manila"))
except Exception:  # pragma: no cover - fallback when tzdata is unavailable
    LOCAL_TZ = timezone(timedelta(hours=8))


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _is_local_host(host):
    return host in ("localhost", "127.0.0.1", "::1") or host.startswith("/")


def _build_database_url():
    """Return a PostgreSQL connection URL, preferring DATABASE_URL.

    Supabase's connection pooler URL works out of the box. When it is missing we
    fall back to the SUPABASE_DB_* / PG* variables so the app can still run in
    environments that only expose individual settings.
    """
    url = os.environ.get("DATABASE_URL", "").strip().strip('"').strip("'")
    if url:
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        parsed = urlparse(url)
        query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() != "pgbouncer"
        ]
        has_sslmode = any(key.lower() == "sslmode" for key, _ in query)
        if not has_sslmode and not _is_local_host(parsed.hostname or ""):
            query.append(("sslmode", "require"))
        return urlunparse(parsed._replace(query=urlencode(query)))

    host = os.environ.get("SUPABASE_DB_HOST") or os.environ.get("PGHOST")
    if not host:
        # Fall back to local SQLite for development if nothing is configured
        sqlite_path = os.path.join(BASE_DIR, "instance", "carwash.db")
        return f"sqlite:///{sqlite_path}"

    user = quote(
        os.environ.get("SUPABASE_DB_USER") or os.environ.get("PGUSER", "postgres"),
        safe="",
    )
    password = quote(
        os.environ.get("SUPABASE_DB_PASSWORD") or os.environ.get("PGPASSWORD", ""),
        safe="",
    )
    port = os.environ.get("SUPABASE_DB_PORT") or os.environ.get("PGPORT", "5432")
    database = (
        os.environ.get("SUPABASE_DB_NAME")
        or os.environ.get("PGDATABASE", "postgres")
    )
    host_part = f"[{host}]" if ":" in host and not host.startswith("[") else host
    sslmode = os.environ.get(
        "SUPABASE_DB_SSLMODE", "disable" if _is_local_host(host) else "require"
    )
    return (
        f"postgresql://{user}:{password}@{host_part}:{port}/{database}"
        f"?sslmode={sslmode}"
    )


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "nice-day-carwash-dev-key-change-me"
    )
    DATABASE_URL = _build_database_url()

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _as_bool(
        os.environ.get("SESSION_COOKIE_SECURE"), default=bool(os.environ.get("VERCEL"))
    )
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024

    TIMEZONE = os.environ.get("APP_TIMEZONE", "Asia/Manila")

    DEFAULT_ADMIN_USERNAME = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD")
    DEFAULT_ADMIN_EMAIL = os.environ.get(
        "DEFAULT_ADMIN_EMAIL", "admin@nicedaycarwash.local"
    )

    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER",
        "/tmp/niceday-carwash-uploads"
        if os.environ.get("VERCEL")
        else os.path.join(
            PROJECT_ROOT, "frontend", "public", "static", "uploads"
        ),
    )
