from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend import models


@dataclass
class AlertCandidate:
    alert_type: str
    severity: str
    description: str
    ip: Optional[str]
    source: str


def recent_alert_exists(
    db: Session,
    alert_type: str,
    ip: Optional[str],
    window_minutes: int,
) -> bool:
    window_start = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    stmt = select(func.count()).select_from(models.Alert).where(
        models.Alert.alert_type == alert_type,
        models.Alert.timestamp >= window_start,
    )
    if ip:
        stmt = stmt.where(models.Alert.ip == ip)
    return (db.scalar(stmt) or 0) > 0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return r * c


def auth_detections(db: Session, log: models.AuthLog, settings) -> List[AlertCandidate]:
    alerts: List[AlertCandidate] = []
    now = log.timestamp

    brute_window = now - timedelta(minutes=settings.BRUTE_FORCE_WINDOW_MINUTES)
    fail_count = db.scalar(
        select(func.count()).select_from(models.AuthLog).where(
            models.AuthLog.ip == log.ip,
            models.AuthLog.success.is_(False),
            models.AuthLog.timestamp >= brute_window,
        )
    ) or 0

    if fail_count >= settings.BRUTE_FORCE_THRESHOLD and not recent_alert_exists(
        db, "Brute Force", log.ip, settings.ALERT_DEDUP_WINDOW_MINUTES
    ):
        alerts.append(
            AlertCandidate(
                alert_type="Brute Force",
                severity="high",
                description=(
                    f"{fail_count} failed logins from {log.ip} within "
                    f"{settings.BRUTE_FORCE_WINDOW_MINUTES} minutes."
                ),
                ip=log.ip,
                source="auth",
            )
        )

    anomaly_window = now - timedelta(minutes=settings.ANOMALY_AUTH_WINDOW_MINUTES)
    total_auth = db.scalar(
        select(func.count()).select_from(models.AuthLog).where(
            models.AuthLog.ip == log.ip,
            models.AuthLog.timestamp >= anomaly_window,
        )
    ) or 0
    anomaly_fail_count = db.scalar(
        select(func.count()).select_from(models.AuthLog).where(
            models.AuthLog.ip == log.ip,
            models.AuthLog.success.is_(False),
            models.AuthLog.timestamp >= anomaly_window,
        )
    ) or 0

    if total_auth >= settings.ANOMALY_AUTH_MIN_EVENTS:
        fail_ratio = anomaly_fail_count / max(total_auth, 1)
        if (
            fail_ratio >= settings.ANOMALY_AUTH_FAIL_RATIO
            and not recent_alert_exists(db, "Auth Failure Spike", log.ip, settings.ALERT_DEDUP_WINDOW_MINUTES)
        ):
            alerts.append(
                AlertCandidate(
                    alert_type="Auth Failure Spike",
                    severity="medium",
                    description=(
                        f"Failure ratio {fail_ratio:.0%} for {log.ip} over "
                        f"{settings.ANOMALY_AUTH_WINDOW_MINUTES} minutes."
                    ),
                    ip=log.ip,
                    source="auth",
                )
            )

    if log.success and log.location_lat is not None and log.location_lon is not None:
        previous = db.execute(
            select(models.AuthLog)
            .where(
                models.AuthLog.username == log.username,
                models.AuthLog.success.is_(True),
                models.AuthLog.id != log.id,
            )
            .order_by(models.AuthLog.timestamp.desc())
            .limit(1)
        ).scalar_one_or_none()

        if previous and previous.location_lat is not None and previous.location_lon is not None:
            time_delta = abs((log.timestamp - previous.timestamp).total_seconds())
            if time_delta <= settings.IMPOSSIBLE_TRAVEL_WINDOW_MINUTES * 60:
                distance = haversine_km(
                    previous.location_lat,
                    previous.location_lon,
                    log.location_lat,
                    log.location_lon,
                )
                if distance >= settings.IMPOSSIBLE_TRAVEL_DISTANCE_KM and not recent_alert_exists(
                    db, "Impossible Travel", log.ip, settings.ALERT_DEDUP_WINDOW_MINUTES
                ):
                    alerts.append(
                        AlertCandidate(
                            alert_type="Impossible Travel",
                            severity="high",
                            description=(
                                f"Login from {log.location_label or 'Unknown Location'} after {distance:.0f}km "
                                f"in {time_delta/60:.0f} minutes for {log.username}."
                            ),
                            ip=log.ip,
                            source="auth",
                        )
                    )

    return alerts


def web_detections(db: Session, log: models.WebLog, settings) -> List[AlertCandidate]:
    alerts: List[AlertCandidate] = []
    now = log.timestamp

    ip_window = now - timedelta(seconds=settings.SUSPICIOUS_WEB_WINDOW_SECONDS)
    ip_count = db.scalar(
        select(func.count()).select_from(models.WebLog).where(
            models.WebLog.ip == log.ip,
            models.WebLog.timestamp >= ip_window,
        )
    ) or 0

    if ip_count >= settings.SUSPICIOUS_WEB_THRESHOLD and not recent_alert_exists(
        db, "High Request Rate", log.ip, settings.ALERT_DEDUP_WINDOW_MINUTES
    ):
        alerts.append(
            AlertCandidate(
                alert_type="High Request Rate",
                severity="medium",
                description=(
                    f"{ip_count} requests from {log.ip} in "
                    f"{settings.SUSPICIOUS_WEB_WINDOW_SECONDS} seconds."
                ),
                ip=log.ip,
                source="web",
            )
        )

    traffic_window = now - timedelta(seconds=settings.ANOMALY_TRAFFIC_WINDOW_SECONDS)
    total_web = db.scalar(
        select(func.count()).select_from(models.WebLog).where(
            models.WebLog.timestamp >= traffic_window,
        )
    ) or 0

    if total_web >= settings.ANOMALY_TRAFFIC_THRESHOLD and not recent_alert_exists(
        db, "Traffic Spike", None, settings.ALERT_DEDUP_WINDOW_MINUTES
    ):
        alerts.append(
            AlertCandidate(
                alert_type="Traffic Spike",
                severity="low",
                description=(
                    f"{total_web} web events in {settings.ANOMALY_TRAFFIC_WINDOW_SECONDS} seconds."
                ),
                ip=None,
                source="web",
            )
        )

    error_window = now - timedelta(seconds=settings.ERROR_SPIKE_WINDOW_SECONDS)
    error_count = db.scalar(
        select(func.count()).select_from(models.WebLog).where(
            models.WebLog.timestamp >= error_window,
            models.WebLog.status_code >= 500,
        )
    ) or 0

    if error_count >= settings.ERROR_SPIKE_THRESHOLD and not recent_alert_exists(
        db, "Error Spike", None, settings.ALERT_DEDUP_WINDOW_MINUTES
    ):
        alerts.append(
            AlertCandidate(
                alert_type="Error Spike",
                severity="medium",
                description=(
                    f"{error_count} server errors in {settings.ERROR_SPIKE_WINDOW_SECONDS} seconds."
                ),
                ip=None,
                source="web",
            )
        )

    return alerts
