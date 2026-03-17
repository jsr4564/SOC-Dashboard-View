from __future__ import annotations

import os


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings:
    BRUTE_FORCE_WINDOW_MINUTES = _get_int("BRUTE_FORCE_WINDOW_MINUTES", 5)
    BRUTE_FORCE_THRESHOLD = _get_int("BRUTE_FORCE_THRESHOLD", 5)

    SUSPICIOUS_WEB_WINDOW_SECONDS = _get_int("SUSPICIOUS_WEB_WINDOW_SECONDS", 60)
    SUSPICIOUS_WEB_THRESHOLD = _get_int("SUSPICIOUS_WEB_THRESHOLD", 80)

    IMPOSSIBLE_TRAVEL_WINDOW_MINUTES = _get_int("IMPOSSIBLE_TRAVEL_WINDOW_MINUTES", 60)
    IMPOSSIBLE_TRAVEL_DISTANCE_KM = _get_int("IMPOSSIBLE_TRAVEL_DISTANCE_KM", 800)

    ANOMALY_AUTH_WINDOW_MINUTES = _get_int("ANOMALY_AUTH_WINDOW_MINUTES", 10)
    ANOMALY_AUTH_MIN_EVENTS = _get_int("ANOMALY_AUTH_MIN_EVENTS", 6)
    ANOMALY_AUTH_FAIL_RATIO = _get_float("ANOMALY_AUTH_FAIL_RATIO", 0.7)

    ANOMALY_TRAFFIC_WINDOW_SECONDS = _get_int("ANOMALY_TRAFFIC_WINDOW_SECONDS", 60)
    ANOMALY_TRAFFIC_THRESHOLD = _get_int("ANOMALY_TRAFFIC_THRESHOLD", 120)

    ERROR_SPIKE_WINDOW_SECONDS = _get_int("ERROR_SPIKE_WINDOW_SECONDS", 120)
    ERROR_SPIKE_THRESHOLD = _get_int("ERROR_SPIKE_THRESHOLD", 12)

    ALERT_DEDUP_WINDOW_MINUTES = _get_int("ALERT_DEDUP_WINDOW_MINUTES", 15)

    ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"
    JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = _get_int("JWT_EXPIRE_MINUTES", 120)
    DASHBOARD_USER = os.getenv("DASHBOARD_USER", "soc")
    DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "soc123")

    ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL")


settings = Settings()
