"""Deployment entry point; the application lives in :mod:`backend`."""

from backend.app import app, create_app

__all__ = ["app", "create_app"]


if __name__ == "__main__":
    app.run(debug=True)
