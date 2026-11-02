#!/usr/bin/env bash
set -euo pipefail

# Adds the Nice Day Carwash environment variables to the linked Vercel project.
#
# Usage:
#   export DATABASE_URL='postgresql://postgres.<ref>:<password>@<pooler-host>:6543/postgres'
#   ./setup-vercel-env.sh
#
# Optional overrides:
#   export SECRET_KEY='...'
#   export DEFAULT_ADMIN_PASSWORD='...'
#   export VERCEL_ENVIRONMENTS='production,preview,development'
#   export VERCEL_PROJECT='your-vercel-project-name'

ENVIRONMENTS="${VERCEL_ENVIRONMENTS:-production,preview,development}"

if ! command -v npx >/dev/null 2>&1; then
    echo "npx is required. Install Node.js first." >&2
    exit 1
fi

if ! npx --yes vercel whoami >/dev/null 2>&1; then
    echo "You are not logged in to Vercel." >&2
    echo "Run: npx vercel login" >&2
    exit 1
fi

if [ ! -f .vercel/project.json ]; then
    echo "This directory is not linked to a Vercel project." >&2
    if [ -n "${VERCEL_PROJECT:-}" ]; then
        npx --yes vercel link --yes --project "$VERCEL_PROJECT"
    else
        echo "Run: npx vercel link" >&2
        exit 1
    fi
fi

if [ -z "${DATABASE_URL:-}" ]; then
    read -r -p "Supabase DATABASE_URL (use the pooler URI): " DATABASE_URL
fi

if [ -z "${SECRET_KEY:-}" ]; then
    SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
fi

add_env() {
    local name="$1"
    local value="$2"
    printf '%s' "$value" | npx --yes vercel env add "$name" \
        --environment "$ENVIRONMENTS" \
        --force --sensitive --yes
    echo "Added $name"
}

add_env SECRET_KEY "$SECRET_KEY"
add_env DATABASE_URL "$DATABASE_URL"

if [ -n "${DEFAULT_ADMIN_PASSWORD:-}" ]; then
    add_env DEFAULT_ADMIN_PASSWORD "$DEFAULT_ADMIN_PASSWORD"
fi

echo
echo "Environment variables added."
echo "Redeploy with: npx --yes vercel --prod"
