"""Standalone database connectivity check for the backend configuration."""
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_CANDIDATES = [
    BASE_DIR / ".env",
    BASE_DIR / "backend.env",
    BASE_DIR.parent / ".env",
]

for env_path in ENV_CANDIDATES:
    if env_path.exists():
        load_dotenv(env_path)
        break

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Check backend/.env, backend/backend.env, "
        "or the project root .env."
    )

try:
    with psycopg.connect(DATABASE_URL, connect_timeout=10):
        pass
    print("DB connection successful")
except Exception as exc:
    raise RuntimeError(f"Database connection failed: {exc}") from exc
