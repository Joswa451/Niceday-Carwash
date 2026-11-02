
import os
import psycopg
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# Load environment variables from backend.env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, "backend.env")

if not os.path.exists(ENV_PATH):
    ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")

# Admin account settings
ADMIN_USERNAME = "admin"
NEW_PASSWORD = os.getenv("NEW_ADMIN_PASSWORD")

def reset_admin_password():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing.")

    if not NEW_PASSWORD:
        raise RuntimeError("NEW_ADMIN_PASSWORD is missing.")

    password_hash = generate_password_hash(NEW_PASSWORD)

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE public.accounts
                    SET account_password = %s,
                        account_role = 'admin'
                    WHERE account_username = %s
                    RETURNING account_id, account_username, account_role
                    """,
                    (password_hash, ADMIN_USERNAME)
                )

                admin = cursor.fetchone()

                if not admin:
                    print("Admin account not found.")
                    return

        print("Admin password successfully updated!")
        print(f"Account ID: {admin[0]}")
        print(f"Username: {admin[1]}")
        print(f"Role: {admin[2]}")

    except Exception as error:
        print("Password reset failed:", error)

if __name__ == "__main__":
    reset_admin_password()
