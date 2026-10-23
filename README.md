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
