FROM python:3.11-slim

# Install system deps needed by psycopg2 and dbt-postgres
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install all Python deps from the single shared requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full pipeline directory contents into /app
COPY ingestion/      ./ingestion/
COPY dbt/            ./dbt/
COPY dagster/        ./dagster/

# Copy the entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Dagster state persists here — volume-mount this on EC2
ENV DAGSTER_HOME=/app/.dagster_home
RUN mkdir -p /app/.dagster_home

# Dagster webserver UI port
EXPOSE 3000

ENTRYPOINT ["/entrypoint.sh"]