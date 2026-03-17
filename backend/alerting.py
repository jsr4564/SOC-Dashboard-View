from __future__ import annotations

import json
import logging
from typing import Any, Dict

import httpx

from .settings import settings

logger = logging.getLogger("soctracker.alerting")


async def handle_high_alert(alert_payload: Dict[str, Any]) -> None:
    logger.warning("HIGH severity alert: %s", json.dumps(alert_payload, default=str))

    if not settings.ALERT_WEBHOOK_URL:
        return

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(settings.ALERT_WEBHOOK_URL, json=alert_payload)
    except Exception as exc:
        logger.error("Webhook send failed: %s", exc)
