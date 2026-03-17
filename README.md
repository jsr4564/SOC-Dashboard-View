# SOC Tracker

**SOC Tracker** is a compact, production-oriented Security Information
and Event Management (SIEM) training environment. The system ingests
authentication and web logs, applies rule-based detection logic,
generates severity-based alerts, and visualizes Security Operations
Center (SOC) activity in real time through an interactive dashboard.

------------------------------------------------------------------------

## Project Overview

SOC Tracker is designed to simulate core SOC workflows in a realistic
and modular environment. Key capabilities include:

-   Ingestion of structured JSON logs via RESTful API endpoints\
-   Rule-based detection for common security scenarios, including:
    -   Brute-force authentication attempts
    -   High-frequency web requests
    -   Impossible travel events
    -   Threshold-based anomaly detection
-   Persistent storage of logs and alerts in a relational database
-   Real-time alert streaming via WebSocket connections
-   Interactive dashboard with visual analytics and alert monitoring

------------------------------------------------------------------------

## System Architecture

The project is organized into the following components:

-   **`backend/`** -- FastAPI service responsible for log ingestion,
    detection logic, alerting, and metrics
-   **`detectors/`** -- Rule engine implementation with optional GeoIP
    integration\
-   **`database/`** -- Default SQLite database for local storage
-   **`frontend/`** -- React (Vite) dashboard for real-time
    visualization\
-   **`frontend-static/`** -- Lightweight, no-build fallback dashboard\
-   **`scripts/`** -- Log generation utilities for testing and
    simulation

### Data Flow

1.  Logs are submitted via `POST /api/ingest/auth` or
    `POST /api/ingest/web`\
2.  The backend persists incoming logs and evaluates detection rules\
3.  Alerts are generated, stored in the database, and streamed via
    `/ws/alerts`\
4.  The dashboard retrieves metrics and subscribes to real-time alert
    updates

------------------------------------------------------------------------

## Setup Instructions

### 1. Install Backend Dependencies

``` bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the Backend Service

``` bash
uvicorn backend.main:app --reload
```

### 3. Run the Frontend (Development Mode)

``` bash
cd frontend
npm install
npm run dev
```

Access the dashboard at:\
http://localhost:5173/

------------------------------------------------------------------------

### 4. Build the Frontend (Production)

``` bash
cd frontend
npm install
npm run build
```

After building, the backend will serve the production frontend at:\
http://localhost:8000/

------------------------------------------------------------------------

### Optional: Static Dashboard Fallback

If the production build is unavailable, the backend automatically serves
the static dashboard located in `frontend-static/`.

------------------------------------------------------------------------

### Docker Deployment (Optional)

``` bash
docker compose up --build
```

This configuration launches the API alongside a PostgreSQL database.

------------------------------------------------------------------------

### Generate Sample Logs

``` bash
python scripts/log_generator.py --mode mixed --duration 120
```

------------------------------------------------------------------------

## Configuration

SOC Tracker supports environment variable configuration for tuning
detection behavior:

-   `DATABASE_URL` -- Database connection string (default: SQLite)\
-   `BRUTE_FORCE_THRESHOLD`, `BRUTE_FORCE_WINDOW_MINUTES`\
-   `SUSPICIOUS_WEB_THRESHOLD`, `SUSPICIOUS_WEB_WINDOW_SECONDS`\
-   `IMPOSSIBLE_TRAVEL_DISTANCE_KM`, `IMPOSSIBLE_TRAVEL_WINDOW_MINUTES`\
-   `ALERT_WEBHOOK_URL` -- Optional webhook for high-severity alerts

------------------------------------------------------------------------

## Authentication (Optional)

JWT-based authentication for the dashboard can be enabled with:

-   `ENABLE_AUTH=true`\
-   `DASHBOARD_USER`\
-   `DASHBOARD_PASSWORD`\
-   `JWT_SECRET`

When enabled, users must authenticate before accessing the dashboard,
and all API requests include a bearer token.

------------------------------------------------------------------------

## GeoIP Integration (Optional)

To enable real geographic location mapping:

1.  Install the `geoip2` library\
2.  Set the `GEOIP_DB_PATH` environment variable to a MaxMind database
    file

If not configured, the system uses deterministic simulated location data
for demonstration purposes.

------------------------------------------------------------------------

## API Reference

-   `POST /api/ingest/auth` -- Submit authentication logs\
-   `POST /api/ingest/web` -- Submit web logs\
-   `GET /api/alerts` -- Retrieve alerts\
-   `GET /api/metrics/summary` -- Summary metrics\
-   `GET /api/metrics/timeline` -- Time-series metrics\
-   `GET /api/health` -- Service health check\
-   `WS /ws/alerts` -- Real-time alert stream

------------------------------------------------------------------------

## Dashboard Features

When running locally, the dashboard provides:

-   High-level SOC metrics (total logs, active alerts, severity
    distribution)\
-   Time-series visualizations for logs and alerts\
-   Real-time alert feed with severity indicators

------------------------------------------------------------------------

## Production Considerations

For deployment in a production-like environment:

-   Replace SQLite with PostgreSQL via `DATABASE_URL`\
-   Secure ingestion endpoints using API keys or mutual TLS (mTLS)\
-   Integrate a real GeoIP database\
-   Implement alert routing (e.g., email, Slack, PagerDuty) for incident
    response

------------------------------------------------------------------------

## Author

Developed by **Jack Shetterly**.
