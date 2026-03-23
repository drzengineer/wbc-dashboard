#!/bin/bash
set -e

echo "=== WBC Pipeline Container Starting ==="

# ── 1. Generate dbt profiles.yml from env vars ─────────────────────────────
# Keeps credentials out of the image and out of bind mounts.
mkdir -p /root/.dbt
cat > /root/.dbt/profiles.yml <<EOF
wbc_dbt:
  target: dev
  outputs:
    dev:
      type: postgres
      host: "${DB_HOST}"
      port: 5432
      user: "${DB_USER}"
      password: "${DB_PASSWORD}"
      dbname: "${DB_NAME}"
      schema: analytics
      sslmode: require
      threads: 4
EOF
echo "profiles.yml written to /root/.dbt/profiles.yml"

# ── 2. Compile dbt to generate manifest.json ───────────────────────────────
# dagster-dbt reads manifest.json at import time to build the asset graph.
# Without this, the container crashes on startup with a FileNotFoundError.
echo "Running dbt compile..."
cd /app/dbt/wbc_dbt
dbt compile
cd /app
echo "dbt compile complete."

# ── 2b. Copy dagster.yaml into DAGSTER_HOME ────────────────────────────────
cp /app/dagster/dagster.yaml /app/.dagster_home/dagster.yaml
echo "dagster.yaml copied to /app/.dagster_home/"

# ── 3. Start dagster-daemon (background) ───────────────────────────────────
# The daemon handles schedule ticking. Without it, scheduled runs never fire.
echo "Starting dagster-daemon..."
DAGSTER_HOME=/app/.dagster_home dagster-daemon run \
  --workspace /app/dagster/workspace.yaml &
DAEMON_PID=$!
echo "dagster-daemon started (PID $DAEMON_PID)"

# ── 4. Start dagster-webserver (foreground) ────────────────────────────────
# The webserver is the UI. Runs in foreground so the container stays alive.
# Daemon will be killed when the webserver exits (container stops).
echo "Starting dagster-webserver on port 3000..."
DAGSTER_HOME=/app/.dagster_home dagster-webserver \
  --workspace /app/dagster/workspace.yaml \
  --host 0.0.0.0 \
  --port 3000