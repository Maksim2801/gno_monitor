#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
python - <<'PY'
import os, time
import psycopg2

url = os.environ.get("DATABASE_URL", "")
# postgresql+psycopg2://user:pass@host:port/db
dsn = url.replace("postgresql+psycopg2://", "postgresql://")
for i in range(60):
    try:
        conn = psycopg2.connect(dsn)
        conn.close()
        print("PostgreSQL is ready")
        break
    except Exception as e:
        print(f"Waiting ({i+1}/60): {e}")
        time.sleep(2)
else:
    raise SystemExit("PostgreSQL not available")
PY

echo "Running migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
