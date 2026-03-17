from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class GeoInfo:
    lat: float
    lon: float
    label: str


def _pseudo_geo(ip: str) -> GeoInfo:
    try:
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback:
            return GeoInfo(lat=40.7128, lon=-74.0060, label="Local Network")
        ip_int = int(ip_obj)
    except ValueError:
        return GeoInfo(lat=0.0, lon=0.0, label="Unknown")

    lat = ((ip_int % 120000) / 1000.0) - 60.0
    lon = ((ip_int % 360000) / 1000.0) - 180.0
    return GeoInfo(lat=lat, lon=lon, label=f"Simulated {ip}")


def lookup(ip: str) -> Optional[GeoInfo]:
    db_path = os.getenv("GEOIP_DB_PATH")
    if db_path:
        try:
            import geoip2.database  # type: ignore

            with geoip2.database.Reader(db_path) as reader:
                response = reader.city(ip)
                lat = response.location.latitude or 0.0
                lon = response.location.longitude or 0.0
                city = response.city.name or "Unknown City"
                country = response.country.name or "Unknown Country"
                return GeoInfo(lat=lat, lon=lon, label=f"{city}, {country}")
        except Exception:
            return _pseudo_geo(ip)

    return _pseudo_geo(ip)
