from __future__ import annotations

import argparse
import random
import time
from datetime import datetime, timezone

import requests

AUTH_ENDPOINT = "/api/ingest/auth"
WEB_ENDPOINT = "/api/ingest/web"

USERS = ["alex", "morgan", "sasha", "taylor", "jordan"]
ENDPOINTS = ["/login", "/admin", "/api/orders", "/api/users", "/checkout"]
METHODS = ["GET", "POST", "PUT", "DELETE"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def send_auth(api_base: str, ip: str, username: str, success: bool) -> None:
    payload = {
        "timestamp": now_iso(),
        "ip": ip,
        "username": username,
        "success": success,
        "user_agent": "SOC-Tracker/1.0",
    }
    requests.post(f"{api_base}{AUTH_ENDPOINT}", json=payload, timeout=2)


def send_web(api_base: str, ip: str, endpoint: str, status_code: int, method: str) -> None:
    payload = {
        "timestamp": now_iso(),
        "ip": ip,
        "endpoint": endpoint,
        "status_code": status_code,
        "method": method,
    }
    requests.post(f"{api_base}{WEB_ENDPOINT}", json=payload, timeout=2)


def random_ip() -> str:
    return f"203.0.113.{random.randint(1, 254)}"


def normal_traffic(api_base: str, duration: int, rate: float) -> None:
    end = time.time() + duration
    interval = max(0.05, 1 / rate)
    while time.time() < end:
        if random.random() < 0.4:
            send_auth(api_base, random_ip(), random.choice(USERS), random.random() > 0.2)
        else:
            send_web(
                api_base,
                random_ip(),
                random.choice(ENDPOINTS),
                random.choice([200, 200, 200, 401, 404, 500]),
                random.choice(METHODS),
            )
        time.sleep(interval)


def brute_force(api_base: str, ip: str, username: str, attempts: int, delay: float) -> None:
    for _ in range(attempts):
        send_auth(api_base, ip, username, False)
        time.sleep(delay)


def traffic_spike(api_base: str, ip: str, events: int) -> None:
    for _ in range(events):
        send_web(
            api_base,
            ip,
            random.choice(ENDPOINTS),
            random.choice([200, 200, 200, 500, 503]),
            random.choice(METHODS),
        )


def impossible_travel(api_base: str, username: str) -> None:
    send_auth(api_base, ip="8.8.8.8", username=username, success=True)
    time.sleep(1)
    send_auth(api_base, ip="1.1.1.1", username=username, success=True)


def mixed_scenario(api_base: str, duration: int) -> None:
    end = time.time() + duration
    while time.time() < end:
        normal_traffic(api_base, duration=5, rate=6)
        if random.random() < 0.4:
            brute_force(api_base, ip="198.51.100.42", username="alex", attempts=8, delay=0.2)
        if random.random() < 0.3:
            traffic_spike(api_base, ip="198.51.100.99", events=120)
        if random.random() < 0.3:
            impossible_travel(api_base, username=random.choice(USERS))


def main() -> None:
    parser = argparse.ArgumentParser(description="SOC Tracker log generator")
    parser.add_argument("--api", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--mode", choices=["normal", "bruteforce", "spike", "mixed"], default="mixed")
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--rate", type=float, default=5)
    args = parser.parse_args()

    if args.mode == "normal":
        normal_traffic(args.api, args.duration, args.rate)
    elif args.mode == "bruteforce":
        brute_force(args.api, ip="203.0.113.9", username="morgan", attempts=12, delay=0.2)
    elif args.mode == "spike":
        traffic_spike(args.api, ip="198.51.100.77", events=200)
    else:
        mixed_scenario(args.api, args.duration)


if __name__ == "__main__":
    main()
