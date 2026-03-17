from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from detectors.rules import AlertCandidate, auth_detections, web_detections

from . import models
from .settings import settings


def evaluate_auth_log(db: Session, log: models.AuthLog) -> List[models.Alert]:
    candidates = auth_detections(db, log, settings)
    return [_to_alert(candidate) for candidate in candidates]


def evaluate_web_log(db: Session, log: models.WebLog) -> List[models.Alert]:
    candidates = web_detections(db, log, settings)
    return [_to_alert(candidate) for candidate in candidates]


def _to_alert(candidate: AlertCandidate) -> models.Alert:
    return models.Alert(
        ip=candidate.ip,
        alert_type=candidate.alert_type,
        severity=candidate.severity,
        description=candidate.description,
        source=candidate.source,
        active=True,
    )
