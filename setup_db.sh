#!/bin/bash
set -e

DB_NAME="agent_db"
DB_USER="${PGUSER:-$(whoami)}"
DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"

echo "Creating database '$DB_NAME'..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;" 2>/dev/null \
  || echo "Database '$DB_NAME' already exists, skipping."

echo "Applying schema..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f schema.psql

echo "Seeding data..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f seed.sql

echo "Done. Database '$DB_NAME' is ready on port $DB_PORT."
