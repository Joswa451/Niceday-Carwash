# Nice Day Carwash

Flask application for managing carwash services, bookings, accounts, and payments.
It uses **PostgreSQL (Supabase)** for storage and is ready to deploy on Vercel.

## Features

- Client registration, login, and password changes
- Service catalog with online booking
- Cash, GCash, Maya, and bank transfer payment options
- Client booking history, cancellation, and payment status
- Admin dashboard for bookings, services, accounts, and reports
- CSRF protection, secure session cookies, and server-side validation

## 1. Create the Supabase database

1. Create a project at [supabase.com](https://supabase.com).
2. Open **SQL Editor > New query**.
3. Paste the contents of [`backend/supabase_schema.sql`](backend/supabase_schema.sql) and click **Run**.

The SQL creates the tables, indexes, `updated_at` trigger, six default services,
and a default administrator:

| Username | Password |
| --- | --- |
| `admin` | `Admin@12345` |

Change that password immediately after your first login (**user menu > Change password**).

## 2. Configure the environment

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
| --- | --- | --- |
| `SECRET_KEY` | Yes | Long random string used to sign session cookies. |
| `DATABASE_URL` | Yes | Supabase PostgreSQL connection string. Prefer the **Connection Pooling** URI (port `6543`). |
| `DEFAULT_ADMIN_PASSWORD` | No | Creates an admin automatically only when no admin exists. The SQL file already handles this. |
| `APP_TIMEZONE` | No | Defaults to `Asia/Manila`. |
| `SESSION_COOKIE_SECURE` | No | Defaults to `true` on Vercel. |

Generate a secret key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

In Supabase, copy the connection string from **Project Settings > Database >
Connection string > URI**. If your password contains special characters, URL-encode
them. The app automatically adds `sslmode=require` for hosted databases.

## 3. Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run
```

The schema is initialized automatically on the first request, so the SQL import is
optional but recommended.

## 4. Deploy to Vercel

1. Push the repository to GitHub.
2. Import it in Vercel. Vercel detects the Flask app in `app.py`.
3. Add the environment variables under **Project Settings > Environment Variables**:
   - `SECRET_KEY`
   - `DATABASE_URL`
4. Deploy.

You can also use the helper script after linking the project:

```bash
export DATABASE_URL='postgresql://...'
./setup-vercel-env.sh
npx vercel --prod
```

The Flask app serves templates and assets from `frontend/`. The function filesystem
is temporary, so user uploads should be stored in object storage such as Supabase
Storage.

## Troubleshooting

- **`DATABASE_URL is not configured`** – add the variable locally or in Vercel and
  redeploy.
- **Connection timeout** – use the Supabase connection pooler host and port `6543`
  instead of the direct database host.
- **`prepared statement already exists`** – the app disables prepared statements
  (`prepare_threshold=None`) so it works with the transaction pooler.
- **`Your session expired`** – the CSRF token expired or the `SECRET_KEY` changed.
  Reload the page and try again.

## Project layout

```text
app.py                 Deployment entry point
backend/                Flask app, routes, configuration, database, and SQL schema
frontend/templates/     Jinja templates
frontend/public/static/ CSS and image assets
requirements.txt        Python dependencies
```
