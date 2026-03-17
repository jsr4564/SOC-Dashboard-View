from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from detectors.geoip import lookup

from . import alerting, auth, detection, models, schemas
from .database import Base, SessionLocal, engine
from .settings import settings

app = FastAPI(title="SOC Tracker", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


class AlertBroadcaster:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, payload: Dict[str, object]) -> None:
        stale: List[WebSocket] = []
        for ws in self.connections:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.connections.discard(ws)


broadcaster = AlertBroadcaster()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/health")
def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/auth/config", response_model=schemas.AuthConfig)
def auth_config() -> schemas.AuthConfig:
    return schemas.AuthConfig(auth_enabled=settings.ENABLE_AUTH)


@app.post("/api/auth/login")
def login(payload: Dict[str, str]) -> Dict[str, str]:
    if not settings.ENABLE_AUTH:
        raise HTTPException(status_code=400, detail="Auth disabled")

    username = payload.get("username")
    password = payload.get("password")
    if username != settings.DASHBOARD_USER or password != settings.DASHBOARD_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth.create_access_token(subject=username)
    return {"access_token": token}


@app.post("/api/ingest/auth", response_model=schemas.IngestResponse)
async def ingest_auth_log(payload: schemas.AuthLogIn, db: Session = Depends(get_db)) -> schemas.IngestResponse:
    timestamp = payload.timestamp or datetime.now(timezone.utc)
    geo = lookup(payload.ip)

    log = models.AuthLog(
        timestamp=timestamp,
        ip=payload.ip,
        username=payload.username,
        success=payload.success,
        user_agent=payload.user_agent,
        location_lat=geo.lat if geo else None,
        location_lon=geo.lon if geo else None,
        location_label=geo.label if geo else None,
    )
    db.add(log)
    db.flush()

    alerts = detection.evaluate_auth_log(db, log)
    for alert in alerts:
        db.add(alert)
    db.flush()
    db.commit()

    alert_ids = [alert.id for alert in alerts]
    for alert in alerts:
        payload_out = schemas.AlertOut.model_validate(alert).model_dump()
        await broadcaster.broadcast(payload_out)
        if alert.severity == "high":
            await alerting.handle_high_alert(payload_out)

    return schemas.IngestResponse(status="ok", alerts_triggered=len(alerts), alert_ids=alert_ids)


@app.post("/api/ingest/web", response_model=schemas.IngestResponse)
async def ingest_web_log(payload: schemas.WebLogIn, db: Session = Depends(get_db)) -> schemas.IngestResponse:
    timestamp = payload.timestamp or datetime.now(timezone.utc)

    log = models.WebLog(
        timestamp=timestamp,
        ip=payload.ip,
        endpoint=payload.endpoint,
        method=payload.method,
        status_code=payload.status_code,
    )
    db.add(log)
    db.flush()

    alerts = detection.evaluate_web_log(db, log)
    for alert in alerts:
        db.add(alert)
    db.flush()
    db.commit()

    alert_ids = [alert.id for alert in alerts]
    for alert in alerts:
        payload_out = schemas.AlertOut.model_validate(alert).model_dump()
        await broadcaster.broadcast(payload_out)
        if alert.severity == "high":
            await alerting.handle_high_alert(payload_out)

    return schemas.IngestResponse(status="ok", alerts_triggered=len(alerts), alert_ids=alert_ids)


@app.get("/api/alerts", response_model=List[schemas.AlertOut])
def list_alerts(
    active: Optional[bool] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    _: str = Depends(auth.require_user),
) -> List[schemas.AlertOut]:
    stmt = select(models.Alert).order_by(models.Alert.timestamp.desc()).limit(limit)
    if active is not None:
        stmt = stmt.where(models.Alert.active.is_(active))
    results = db.execute(stmt).scalars().all()
    return [schemas.AlertOut.model_validate(alert) for alert in results]


@app.post("/api/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(auth.require_user),
) -> Dict[str, str]:
    alert = db.get(models.Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.active = False
    db.commit()
    return {"status": "resolved"}


@app.get("/api/metrics/summary", response_model=schemas.MetricsSummary)
def metrics_summary(
    db: Session = Depends(get_db),
    _: str = Depends(auth.require_user),
) -> schemas.MetricsSummary:
    total_auth = db.scalar(select(func.count()).select_from(models.AuthLog)) or 0
    total_web = db.scalar(select(func.count()).select_from(models.WebLog)) or 0
    active_alerts = db.scalar(
        select(func.count()).select_from(models.Alert).where(models.Alert.active.is_(True))
    ) or 0

    severity_counts = defaultdict(int)
    rows = db.execute(
        select(models.Alert.severity, func.count()).group_by(models.Alert.severity)
    ).all()
    for severity, count in rows:
        severity_counts[severity] = count

    return schemas.MetricsSummary(
        total_logs=total_auth + total_web,
        total_auth_logs=total_auth,
        total_web_logs=total_web,
        active_alerts=active_alerts,
        alerts_by_severity=dict(severity_counts),
    )


@app.get("/api/metrics/timeline", response_model=schemas.TimelineOut)
def metrics_timeline(
    minutes: int = Query(default=60, ge=5, le=1440),
    db: Session = Depends(get_db),
    _: str = Depends(auth.require_user),
) -> schemas.TimelineOut:
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=minutes)

    auth_rows = db.execute(
        select(models.AuthLog.timestamp).where(models.AuthLog.timestamp >= start)
    ).scalars().all()
    web_rows = db.execute(
        select(models.WebLog.timestamp).where(models.WebLog.timestamp >= start)
    ).scalars().all()
    alert_rows = db.execute(
        select(models.Alert.timestamp).where(models.Alert.timestamp >= start)
    ).scalars().all()

    def bucket(ts_list: List[datetime]) -> List[schemas.TimelinePoint]:
        buckets: Dict[datetime, int] = defaultdict(int)
        for ts in ts_list:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            key = ts.replace(second=0, microsecond=0)
            buckets[key] += 1
        points: List[schemas.TimelinePoint] = []
        cursor = start.replace(second=0, microsecond=0)
        while cursor <= now:
            points.append(schemas.TimelinePoint(ts=cursor, count=buckets.get(cursor, 0)))
            cursor += timedelta(minutes=1)
        return points

    log_points = bucket(auth_rows + web_rows)
    alert_points = bucket(alert_rows)
    return schemas.TimelineOut(logs=log_points, alerts=alert_points)


@app.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket):
    await broadcaster.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)


project_root = Path(__file__).resolve().parent.parent
frontend_dir = project_root / "frontend"
dist_dir = frontend_dir / "dist"
static_fallback = project_root / "frontend-static"
static_dir = dist_dir if dist_dir.exists() else static_fallback
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
