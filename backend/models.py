from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from .database import Base


class AuthLog(Base):
    __tablename__ = "auth_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    ip = Column(String(64), index=True, nullable=False)
    username = Column(String(128), index=True, nullable=False)
    success = Column(Boolean, nullable=False)
    user_agent = Column(String(256), nullable=True)
    location_lat = Column(Float, nullable=True)
    location_lon = Column(Float, nullable=True)
    location_label = Column(String(128), nullable=True)


class WebLog(Base):
    __tablename__ = "web_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    ip = Column(String(64), index=True, nullable=False)
    endpoint = Column(String(256), nullable=False)
    method = Column(String(12), nullable=False)
    status_code = Column(Integer, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    ip = Column(String(64), index=True, nullable=True)
    alert_type = Column(String(128), index=True, nullable=False)
    severity = Column(String(16), index=True, nullable=False)
    description = Column(String(512), nullable=False)
    source = Column(String(32), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
