"""Compliant collection entry for Ctrip Chongqing main-city 3-diamond hotels.

This module intentionally avoids unauthorised HTML scraping. It can export data
from an authorised API source or from an operator-provided JSON fixture, while
honouring configured robots.txt checks and rate limits before any HTTP request.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
from typing import Any, Iterable, Mapping, Protocol
from urllib import request, robotparser

from .export import export_records
from .models import HotelRecord

DEFAULT_CONFIG_PATH = Path("config/ctrip_chongqing.yaml")
DEFAULT_OUTPUT_PATH = Path("data/chongqing_ctrip_3diamond_hotels.csv")


class HotelSource(Protocol):
    """Protocol for authorised hotel-data providers."""

    def fetch_hotels(self, config: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
        """Return raw hotel payloads from an authorised source."""


class RateLimiter:
    """Small fixed-delay limiter for polite authorised API access."""

    def __init__(self, seconds: float) -> None:
        self.seconds = max(0.0, seconds)
        self._last_request_at = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        remaining = self.seconds - (now - self._last_request_at)
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_at = time.monotonic()


class RobotsPolicy:
    """robots.txt policy checker for outbound requests."""

    def __init__(self, robots_url: str, user_agent: str) -> None:
        self.user_agent = user_agent
        self.parser = robotparser.RobotFileParser()
        self.parser.set_url(robots_url)
        self.parser.read()

    def assert_allowed(self, url: str) -> None:
        if not self.parser.can_fetch(self.user_agent, url):
            raise PermissionError(f"robots.txt disallows fetching {url!r} for {self.user_agent!r}")


class JsonFileSource:
    """Load operator-provided authorised payloads from a JSON file."""

    def __init__(self, input_path: str | Path) -> None:
        self.input_path = Path(input_path)

    def fetch_hotels(self, config: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
        del config
        with self.input_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            payload = payload.get("hotels", [])
        if not isinstance(payload, list):
            raise ValueError("input JSON must be a list or an object with a 'hotels' list")
        return payload


class AuthorizedApiSource:
    """Generic authorised API client configured by environment variables.

    Required environment variables:
    - ``CTRIP_API_BASE_URL``: authorised endpoint URL supplied by Ctrip/partner.
    - ``CTRIP_API_TOKEN``: bearer token or partner credential for that endpoint.
    """

    def __init__(self, base_url: str, token: str, user_agent: str, delay_seconds: float) -> None:
        self.base_url = base_url
        self.token = token
        self.user_agent = user_agent
        self.rate_limiter = RateLimiter(delay_seconds)

    @classmethod
    def from_environment(cls, config: Mapping[str, Any]) -> "AuthorizedApiSource":
        base_url = os.environ.get("CTRIP_API_BASE_URL")
        token = os.environ.get("CTRIP_API_TOKEN")
        if not base_url or not token:
            raise RuntimeError(
                "Authorised API access requires CTRIP_API_BASE_URL and CTRIP_API_TOKEN; "
                "do not scrape Ctrip pages without permission."
            )
        compliance = config.get("compliance", {}) if isinstance(config.get("compliance", {}), dict) else {}
        rate_limit = config.get("rate_limit", {}) if isinstance(config.get("rate_limit", {}), dict) else {}
        user_agent = str(compliance.get("user_agent", "hotel-business-data/1.0"))
        delay_seconds = float(rate_limit.get("delay_seconds", 2.0))
        robots_url = str(compliance.get("robots_url", "https://www.ctrip.com/robots.txt"))
        if compliance.get("respect_robots_txt", True):
            RobotsPolicy(robots_url, user_agent).assert_allowed(base_url)
        return cls(base_url, token, user_agent, delay_seconds)

    def fetch_hotels(self, config: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
        pages = int(config.get("pages", 1))
        for page in range(1, pages + 1):
            self.rate_limiter.wait()
            body = json.dumps({**dict(config), "page": page}, ensure_ascii=False).encode("utf-8")
            http_request = request.Request(
                self.base_url,
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json; charset=utf-8",
                    "User-Agent": self.user_agent,
                },
            )
            with request.urlopen(http_request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            hotels = payload.get("hotels", payload if isinstance(payload, list) else [])
            if not isinstance(hotels, list):
                raise ValueError("authorised API response must contain a hotel list")
            yield from hotels


def load_config(path: str | Path) -> dict[str, Any]:
    """Load YAML config, falling back to a tiny key/value parser if PyYAML is absent."""
    config_path = Path(path)
    try:
        import yaml
    except ImportError:
        return _load_simple_yaml(config_path)
    with config_path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError("config must be a mapping")
    return payload


def _load_simple_yaml(path: Path) -> dict[str, Any]:
    """Minimal parser for this repository's simple YAML config shape."""
    result: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, result)]
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, _, raw_value = line.strip().partition(":")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        value = raw_value.strip()
        if not value:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        elif value.startswith("[") and value.endswith("]"):
            parent[key] = [item.strip().strip('"\'') for item in value[1:-1].split(",") if item.strip()]
        elif value.lower() in {"true", "false"}:
            parent[key] = value.lower() == "true"
        else:
            try:
                parent[key] = int(value)
            except ValueError:
                try:
                    parent[key] = float(value)
                except ValueError:
                    parent[key] = value.strip('"\'')
    return result


def normalize_records(raw_hotels: Iterable[Mapping[str, Any]], diamond_level: int = 3) -> list[HotelRecord]:
    """Clean raw records and keep only the configured diamond level."""
    records = [HotelRecord.from_mapping(raw) for raw in raw_hotels]
    return [record for record in records if record.diamond_level == diamond_level]


def collect(source: HotelSource, config: Mapping[str, Any]) -> list[HotelRecord]:
    """Fetch, clean, and filter records from an authorised source."""
    raw_hotels = source.fetch_hotels(config)
    return normalize_records(raw_hotels, diamond_level=int(config.get("diamond_level", 3)))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export authorised Ctrip Chongqing 3-diamond hotel data")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="YAML collection config path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="CSV or XLSX output path")
    parser.add_argument("--input-json", help="Authorised/offline JSON payload to normalize and export")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    config = load_config(args.config)
    source: HotelSource
    if args.input_json:
        source = JsonFileSource(args.input_json)
    else:
        source = AuthorizedApiSource.from_environment(config)
    records = collect(source, config)
    export_records(records, args.output)
    print(f"exported {len(records)} records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
