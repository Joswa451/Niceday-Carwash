# Nice Day Carwash

Full-stack carwash booking application with a **React + Vite** frontend and a
**Flask JSON API** backend. It uses **PostgreSQL (Supabase)** for storage, and the
two halves are deployed separately (frontend on Vercel, API on Render).

## Features

- Client registration, login, and password changes
- Service catalog with online booking
- Cash, GCash, Maya, and bank transfer payment options
- Client booking history, cancellation, and payment status
- Admin dashboard for bookings, services, accounts, and reports
- Bearer-token API authentication, CORS, and server-side validation
- Legacy Jinja pages are still available from the Flask app

## Architecture

```text
frontend/    React + Vite SPA (Vercel)
backend/     Flask app, JSON API, routes, configuration, and database layer
app.py       WSGI entry point used by Render/gunicorn
```

The React app talks to the backend through `VITE_API_URL`. All API routes live
under `/api` and return JSON.

## 1. Create the Supabase database

1. Create a project at [supabase.com](https://supabase.com).
2. Open **SQL Editor > New query**.
3. Paste the contents of [`backend/supabase_schema.sql`](backend/supabase_schema.sql) and click **Run**.

The SQL creates the tables, indexes, `updated_at` trigger, and six default services.
No password is stored in the SQL file. On the first Flask startup, set
`DEFAULT_ADMIN_PASSWORD` in the environment so the app can create the administrator
account. Change that password after your first login (**user menu > Change password**).

## 2. Configure the environment

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
| --- | --- | --- |
| `SECRET_KEY` | Yes | Long random string used to sign session cookies. |
| `DATABASE_URL` | Yes | Supabase PostgreSQL connection string. Prefer the **Connection Pooling** URI (port `6543`). |
| `DEFAULT_ADMIN_PASSWORD` | First deploy | Creates an admin automatically only when no admin exists. Required for a fresh database. |
| `APP_TIMEZONE` | No | Defaults to `Asia/Manila`. |
| `SESSION_COOKIE_SECURE` | No | Defaults to `true` on Vercel. |
| `CORS_ORIGINS` | No | Comma-separated frontend origins allowed to call `/api`. Defaults to `*`. |

Generate a secret key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

In Supabase, copy the connection string from **Project Settings > Database >
Connection string > URI**. If your password contains special characters, URL-encode
them. The app automatically adds `sslmode=require` for hosted databases.

## 3. Run locally

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run
```

The API runs at `http://localhost:5000/api` by default. The schema is initialized
automatically on the first request, so the SQL import is optional but recommended.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The React app runs at `http://localhost:5173`. Set `VITE_API_URL` in
`frontend/.env` to the backend URL, for example
`VITE_API_URL=http://localhost:5000/api`.

## 4. Deploy

### Backend on Render

1. Create a **Web Service** from this repository.
2. Leave the root directory at the repository root.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add environment variables:
   - `SECRET_KEY`
   - `DATABASE_URL`
   - `CORS_ORIGINS` (your deployed Vercel URL, e.g. `https://your-app.vercel.app`)
   - `DEFAULT_ADMIN_PASSWORD` (fresh databases only)
   - Optional: `DEFAULT_ADMIN_USERNAME`, `DEFAULT_ADMIN_EMAIL`, `APP_TIMEZONE`
6. Deploy and confirm `https://your-api.onrender.com/api/health` returns OK.

### Frontend on Vercel

1. Import the same repository as a new Vercel project.
2. Set **Root Directory** to `frontend`.
3. Framework preset: **Vite**.
4. Build command: `npm run build`; output directory: `dist`.
5. Add `VITE_API_URL=https://your-api.onrender.com/api`.
6. Deploy.

`frontend/vercel.json` rewrites client-side routes to `index.html` so routing works
on refresh. API calls use the absolute `VITE_API_URL` and therefore go directly to
Render instead of that same-origin rewrite. Do not deploy this project with the
repository root as the Vercel root directory: that serves only static files and
causes the `NOT_FOUND` page.

If you already created a Vercel project for the old Flask deployment, either change
its Root Directory to `frontend` and redeploy, or create a new Vercel project from
the same repository. A Vercel static deployment cannot run Flask, so the backend
must be hosted on Render or another Python host.

The legacy Flask templates remain available for local reference. User uploads
should be stored in object storage such as Supabase Storage because serverless and
Render filesystems are temporary.

## Troubleshooting

- **`DATABASE_URL is not configured`** – add the variable locally or in Vercel and
  redeploy.
- **Connection timeout** – use the Supabase connection pooler host and port `6543`
  instead of the direct database host.
- **`prepared statement already exists`** – the app disables prepared statements
  (`prepare_threshold=None`) so it works with the transaction pooler.
- **`Your session expired`** – the CSRF token expired or the `SECRET_KEY` changed.
  Reload the page and try again.
- **Services show a non-JSON response error, or registration returns `405`** – the
  frontend is calling `/api` on Vercel instead of the Render backend. Set
  `VITE_API_URL=https://your-api.onrender.com/api` in the Vercel project and
  redeploy; Vite environment variables are applied at build time.
- **CORS errors in the browser** – add the exact Vercel origin (no trailing slash)
  to `CORS_ORIGINS` on Render, then redeploy the backend.

## Project layout

```text
app.py                  WSGI deployment entry point
backend/                Flask app, JSON API, routes, configuration, and SQL schema
backend/api_bp.py       React-facing JSON API
frontend/src/           React pages, components, contexts, and API client
frontend/public/static/ Shared CSS and image assets
frontend/templates/     Legacy Jinja templates (kept for reference)
frontend/vercel.json    SPA rewrite for Vercel
requirements.txt        Python dependencies
```
