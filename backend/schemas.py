from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class AuthLogIn(BaseModel):
    timestamp: Optional[datetime] = None
    ip: str = Field(..., examples=["203.0.113.10"])
    username: str = Field(..., examples=["jane.doe"])
    success: bool
    user_agent: Optional[str] = None


class WebLogIn(BaseModel):
    timestamp: Optional[datetime] = None
    ip: str = Field(..., examples=["198.51.100.23"])
    endpoint: str = Field(..., examples=["/login"])
    method: str = Field(..., examples=["POST"])
    status_code: int = Field(..., examples=[200])


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    ip: Optional[str]
    alert_type: str
    severity: str
    description: str
    source: str
    active: bool


class IngestResponse(BaseModel):
    status: str
    alerts_triggered: int
    alert_ids: List[int]


class MetricsSummary(BaseModel):
    total_logs: int
    total_auth_logs: int
    total_web_logs: int
    active_alerts: int
    alerts_by_severity: Dict[str, int]


class TimelinePoint(BaseModel):
    ts: datetime
    count: int


class TimelineOut(BaseModel):
    logs: List[TimelinePoint]
    alerts: List[TimelinePoint]


class AuthConfig(BaseModel):
    auth_enabled: bool
