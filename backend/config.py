import ipaddress
import os
import re
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


_IPV4_CANDIDATE_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
_DNS_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def _clean_env_value(value):
    cleaned = str(value or "").strip()
    if (
        len(cleaned) >= 2
        and cleaned[0] == cleaned[-1]
        and cleaned[0] in ("'", '"')
    ):
        cleaned = cleaned[1:-1].strip()
    return cleaned


def _is_production_runtime():
    return (
        _as_bool(os.environ.get("RENDER"))
        or _as_bool(os.environ.get("VERCEL"))
        or os.environ.get("FLASK_ENV", "").strip().lower() == "production"
    )


def _is_local_host(host):
    candidate = (host or "").strip().lower()
    if candidate.startswith("[") and candidate.endswith("]"):
        candidate = candidate[1:-1]
    candidate = candidate.rstrip(".")
    return candidate in ("localhost", "127.0.0.1", "::1") or candidate.startswith("/")


def _validate_port(port):
    if port in (None, ""):
        return
    try:
        number = int(port)
    except (TypeError, ValueError) as exc:
        raise ValueError("port must be a number") from exc
    if not 1 <= number <= 65535:
        raise ValueError("port must be between 1 and 65535")


def _validate_dns_hostname(hostname):
    candidate = hostname[:-1] if hostname.endswith(".") else hostname
    if not candidate:
        raise ValueError("hostname is empty")

    try:
        ascii_hostname = candidate.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("hostname is not valid DNS") from exc

    if len(ascii_hostname) > 253:
        raise ValueError("hostname is longer than 253 characters")

    labels = ascii_hostname.split(".")
    if any(not label for label in labels):
        raise ValueError("hostname contains an empty DNS label")
    for label in labels:
        if len(label) > 63 or not _DNS_LABEL_RE.fullmatch(label):
            raise ValueError("hostname contains an invalid DNS label")


def _validate_database_host(hostname):
    if hostname is None:
        raise ValueError("hostname is missing")

    candidate = hostname.strip()
    if candidate.startswith("[") and candidate.endswith("]"):
        candidate = candidate[1:-1]
    if not candidate:
        raise ValueError("hostname is empty")

    # Only call the IP parser when the syntax actually looks like an IP address.
    if _IPV4_CANDIDATE_RE.fullmatch(candidate):
        try:
            ipaddress.IPv4Address(candidate)
        except ipaddress.AddressValueError as exc:
            raise ValueError("hostname is not a valid IPv4 address") from exc
        return "ipv4"

    if ":" in candidate:
        try:
            ipaddress.IPv6Address(candidate)
        except ipaddress.AddressValueError as exc:
            raise ValueError("hostname is not a valid IPv6 address") from exc
        return "ipv6"

    if candidate.startswith("/"):
        return "unix"

    _validate_dns_hostname(candidate)
    return "dns"


def _normalize_database_url(url):
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise ValueError(f"could not be parsed ({exc})") from exc

    if parsed.scheme.lower() == "sqlite":
        if not parsed.path:
            raise ValueError("SQLite URL is missing a database path")
        return url

    if parsed.scheme.lower() not in ("postgres", "postgresql"):
        raise ValueError(
            "unsupported database scheme; expected postgresql:// or sqlite://"
        )

    try:
        hostname = parsed.hostname
    except ValueError as exc:
        raise ValueError(f"invalid hostname ({exc})") from exc

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"invalid port ({exc})") from exc

    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() != "pgbouncer"
    ]

    if hostname is None:
        has_socket_host = any(key.lower() == "host" for key, _ in query)
        if parsed.netloc or (not parsed.path.strip("/") and not has_socket_host):
            raise ValueError("PostgreSQL URL is missing a hostname")
    else:
        try:
            _validate_database_host(hostname)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    try:
        _validate_port(port)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    has_sslmode = any(key.lower() == "sslmode" for key, _ in query)
    is_socket = hostname is None or hostname.startswith("/")
    if not has_sslmode and not is_socket and not _is_local_host(hostname):
        query.append(("sslmode", "require"))

    return urlunparse(parsed._replace(query=urlencode(query)))


def _build_database_url():
    """Return a PostgreSQL connection URL, preferring DATABASE_URL.

    Supabase's connection pooler URL works out of the box. When it is missing we
    fall back to the SUPABASE_DB_* / PG* variables so the app can still run in
    environments that only expose individual settings.
    """
    url = _clean_env_value(os.environ.get("DATABASE_URL"))
    if url:
        try:
            return _normalize_database_url(url)
        except ValueError as exc:
            raise RuntimeError(f"Invalid DATABASE_URL: {exc}") from exc

    host = _clean_env_value(
        os.environ.get("SUPABASE_DB_HOST") or os.environ.get("PGHOST")
    )
    if not host:
        if _is_production_runtime():
            raise RuntimeError(
                "DATABASE_URL is not configured. Set DATABASE_URL to the "
                "Supabase PostgreSQL connection string."
            )
        # Fall back to local SQLite for development if nothing is configured.
        sqlite_path = os.path.join(BASE_DIR, "instance", "carwash.db")
        return f"sqlite:///{sqlite_path}"

    try:
        _validate_database_host(host)
    except ValueError as exc:
        raise RuntimeError(f"Invalid database host configuration: {exc}") from exc

    user = quote(
        os.environ.get("SUPABASE_DB_USER") or os.environ.get("PGUSER", "postgres"),
        safe="",
    )
    password = quote(
        os.environ.get("SUPABASE_DB_PASSWORD") or os.environ.get("PGPASSWORD", ""),
        safe="",
    )
    port = _clean_env_value(
        os.environ.get("SUPABASE_DB_PORT") or os.environ.get("PGPORT", "5432")
    )
    try:
        _validate_port(port)
    except ValueError as exc:
        raise RuntimeError(f"Invalid database port configuration: {exc}") from exc

    database = _clean_env_value(
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
    SECRET_KEY = os.environ.get("SECRET_KEY")
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
