# Nice Day Carwash

Flask application for managing carwash services, bookings, accounts, and payments.

## Setup

1. Create and activate a virtual environment, then install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configure MySQL and the initial administrator credentials in your environment:

   ```bash
   export SECRET_KEY="replace-with-a-long-random-value"
   export MYSQL_HOST="127.0.0.1"
   export MYSQL_PORT="3306"
   export MYSQL_USER="root"
   export MYSQL_PASSWORD=""
   export MYSQL_DATABASE="niceday_carwash"
   export DEFAULT_ADMIN_PASSWORD="choose-a-strong-password"
   ```

   `DEFAULT_ADMIN_PASSWORD` is only needed when the database does not already
   contain the initial `admin` account. Do not commit environment files or
   production credentials.

3. Start the application:

   ```bash
   flask --app app run
   ```

The database tables and default services are initialized automatically.

## Deploy to Vercel

Vercel detects the Flask application in `app.py`. Static files are kept in
`public/static/`, which Vercel serves from the CDN. User-uploaded files, if
added later, must use persistent object storage because Vercel's function
filesystem is temporary.

Before deploying, create a hosted MySQL database reachable from Vercel and add
these variables under **Project Settings > Environment Variables**:

- `SECRET_KEY`: a long, random secret value.
- `MYSQL_HOST`: the hosted database hostname (not `localhost`).
- `MYSQL_PORT`: the database port.
- `MYSQL_USER`: the database username.
- `MYSQL_PASSWORD`: the database password.
- `MYSQL_DATABASE`: the database name.
- `DEFAULT_ADMIN_PASSWORD`: required only if the database has no `admin`
  account yet.

Redeploy after saving the variables. The application initializes its database
when the Flask function starts, so it will return an error until the database
is reachable and all required environment variables are configured.
