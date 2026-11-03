import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import TestCase, mock
from urllib.parse import parse_qs, unquote, urlparse

from backend import config

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class DatabaseUrlTests(TestCase):
    def build_url(self, url="", **environment):
        values = {"RENDER": "", "VERCEL": "", "FLASK_ENV": ""}
        if url:
            values["DATABASE_URL"] = url
        values.update(environment)
        with mock.patch.dict(os.environ, values, clear=True):
            return config._build_database_url()

    def test_supabase_session_pooler_hostname(self):
        result = self.build_url(
            "postgresql://postgres.project:secret@"
            "aws-0-eu-west-1.pooler.supabase.com:6543/postgres"
        )
        parsed = urlparse(result)

        self.assertEqual(parsed.hostname, "aws-0-eu-west-1.pooler.supabase.com")
        self.assertEqual(parsed.port, 6543)
        self.assertEqual(parsed.username, "postgres.project")
        self.assertEqual(parsed.password, "secret")
        self.assertEqual(parsed.path, "/postgres")
        self.assertEqual(parse_qs(parsed.query)["sslmode"], ["require"])

    def test_flask_app_import_uses_corrected_config_for_render_hostname(self):
        database_url = (
            "postgresql://postgres.project:secret@"
            "aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require"
        )
        environment = os.environ.copy()
        environment.update(
            {
                "DATABASE_URL": database_url,
                "SECRET_KEY": "test-secret",
                "RENDER": "true",
                "PYTHONPATH": str(PROJECT_ROOT),
            }
        )
        script = """
import json
import backend.config as config
from backend.app import app

print(json.dumps({
    "config_file": config.__file__,
    "configured_url": config.Config.DATABASE_URL,
    "app_url": app.config["DATABASE_URL"],
}))
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout)

        self.assertTrue(payload["config_file"].endswith("backend/config.py"))
        self.assertEqual(payload["configured_url"], payload["app_url"])
        self.assertIn(
            "aws-0-eu-west-1.pooler.supabase.com:6543", payload["app_url"]
        )
        self.assertIn("sslmode=require", payload["app_url"])

    def test_dns_hostname_does_not_use_ip_validation(self):
        with (
            mock.patch.object(
                config.ipaddress,
                "IPv4Address",
                side_effect=AssertionError("IPv4 parser must not run for DNS"),
            ),
            mock.patch.object(
                config.ipaddress,
                "IPv6Address",
                side_effect=AssertionError("IPv6 parser must not run for DNS"),
            ),
        ):
            result = self.build_url(
                "postgresql://postgres.project:secret@"
                "aws-0-eu-west-1.pooler.supabase.com:6543/postgres"
            )

        self.assertIn("aws-0-eu-west-1.pooler.supabase.com", result)

    def test_ipv4_hostname(self):
        result = self.build_url(
            "postgresql://user:pass@192.0.2.10:5432/carwash"
        )
        parsed = urlparse(result)

        self.assertEqual(parsed.hostname, "192.0.2.10")
        self.assertEqual(parsed.port, 5432)
        self.assertEqual(parsed.path, "/carwash")
        self.assertEqual(parse_qs(parsed.query)["sslmode"], ["require"])

    def test_ipv6_hostname(self):
        result = self.build_url(
            "postgresql://user:pass@[2001:db8::1]:5432/carwash"
        )
        parsed = urlparse(result)

        self.assertEqual(parsed.hostname, "2001:db8::1")
        self.assertIn("[2001:db8::1]:5432", result)
        self.assertEqual(parsed.port, 5432)
        self.assertEqual(parsed.path, "/carwash")

    def test_url_encoded_password_and_query_parameters(self):
        result = self.build_url(
            "postgresql://postgres.ref:p%40ss%2Fword%3A%21@"
            "aws-0-eu-west-1.pooler.supabase.com:6543/postgres"
            "?application_name=carwash%20api&sslmode=require"
        )
        parsed = urlparse(result)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.password, "p%40ss%2Fword%3A%21")
        self.assertEqual(unquote(parsed.password), "p@ss/word:!")
        self.assertEqual(query["application_name"], ["carwash api"])
        self.assertEqual(query["sslmode"], ["require"])

    def test_existing_sslmode_and_pgbouncer_parameters(self):
        result = self.build_url(
            "postgresql://user:pass@db.example.com:5432/carwash"
            "?pgbouncer=true&sslmode=verify-full"
        )
        query = parse_qs(urlparse(result).query)

        self.assertNotIn("pgbouncer", query)
        self.assertEqual(query["sslmode"], ["verify-full"])

    def test_local_host_does_not_require_ssl(self):
        result = self.build_url(
            "postgresql://user:pass@localhost:5432/carwash"
        )
        query = parse_qs(urlparse(result).query)

        self.assertNotIn("sslmode", query)

    def test_sqlite_url_is_preserved(self):
        result = self.build_url("sqlite:////tmp/carwash-test.db")

        self.assertEqual(result, "sqlite:////tmp/carwash-test.db")

    def test_invalid_database_urls_raise_clear_errors(self):
        cases = [
            (
                "postgresql://user:pass@/postgres",
                "missing a hostname",
            ),
            (
                "postgresql://user:pass@bad_host:5432/postgres",
                "invalid DNS label",
            ),
            (
                "postgresql://user:pass@999.1.1.1:5432/postgres",
                "not a valid IPv4 address",
            ),
            (
                "postgresql://user:pass@db.example.com:99999/postgres",
                "invalid port",
            ),
            (
                "postgresql://user:pass@db.example.com:notaport/postgres",
                "invalid port",
            ),
            (
                "mysql://user:pass@db.example.com/carwash",
                "unsupported database scheme",
            ),
        ]

        for url, message in cases:
            with self.subTest(url=url):
                with self.assertRaisesRegex(RuntimeError, message):
                    self.build_url(url)

    def test_missing_database_url_in_production_raises_clear_error(self):
        with self.assertRaisesRegex(
            RuntimeError, "DATABASE_URL is not configured"
        ):
            self.build_url(RENDER="true")

    def test_missing_database_url_uses_sqlite_for_local_development(self):
        result = self.build_url()

        self.assertTrue(result.startswith("sqlite:///"))
