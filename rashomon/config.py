"""Read and validate a rashomon YAML config.

Example:

    settings:            # optional
      timeout: 30        # seconds per query and endpoint
      decimal_places: 6  # numbers are rounded to this before comparing

    endpoints:
      - name: fuseki
        url: http://localhost:3030/ds/query
      - name: oxigraph
        url: http://localhost:7878/query
        headers: {Authorization: "Basic ..."}  # optional

    queries:
      - id: avg-mixed
        file: queries/avg-mixed.rq   # relative to the config file
        description: AVG over integers, decimals and doubles   # optional
      - id: count-all
        query: SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }
        order_sensitive: false       # optional, compare row order too
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_TIMEOUT = 30.0
DEFAULT_DECIMAL_PLACES = 6


class ConfigError(Exception):
    """The config file is missing something or has a wrong value."""


@dataclass
class Endpoint:
    name: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class Query:
    id: str
    text: str
    description: str = ""
    order_sensitive: bool = False


@dataclass
class Config:
    endpoints: list[Endpoint]
    queries: list[Query]
    timeout: float = DEFAULT_TIMEOUT
    decimal_places: int = DEFAULT_DECIMAL_PLACES


def load_config(path: Path) -> Config:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Can't read {path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise ConfigError(f"{path}: expected a mapping with 'endpoints' and 'queries'")

    settings = doc.get("settings") or {}
    endpoints = [_endpoint(item, i) for i, item in enumerate(_list(doc, "endpoints"))]
    queries = [_query(item, i, path.parent) for i, item in enumerate(_list(doc, "queries"))]

    _no_duplicates("endpoint name", [e.name for e in endpoints])
    _no_duplicates("query id", [q.id for q in queries])
    if len(endpoints) < 2:
        raise ConfigError("List at least two endpoints: there is nothing to compare otherwise")

    return Config(
        endpoints=endpoints,
        queries=queries,
        timeout=float(settings.get("timeout", DEFAULT_TIMEOUT)),
        decimal_places=int(settings.get("decimal_places", DEFAULT_DECIMAL_PLACES)),
    )


def _list(doc: dict, key: str) -> list:
    value = doc.get(key)
    if not isinstance(value, list) or not value:
        raise ConfigError(f"'{key}' must be a non-empty list")
    return value


def _endpoint(item, index: int) -> Endpoint:
    where = f"endpoints[{index}]"
    if not isinstance(item, dict) or "name" not in item or "url" not in item:
        raise ConfigError(f"{where}: needs 'name' and 'url'")
    headers = item.get("headers") or {}
    if not isinstance(headers, dict):
        raise ConfigError(f"{where}: 'headers' must be a mapping")
    return Endpoint(
        name=str(item["name"]),
        url=str(item["url"]),
        headers={str(k): str(v) for k, v in headers.items()},
    )


def _query(item, index: int, base_dir: Path) -> Query:
    where = f"queries[{index}]"
    if not isinstance(item, dict) or "id" not in item:
        raise ConfigError(f"{where}: needs an 'id'")
    if ("file" in item) == ("query" in item):
        raise ConfigError(f"{where} ({item['id']}): give exactly one of 'file' or 'query'")

    if "file" in item:
        query_path = base_dir / item["file"]
        try:
            text = query_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigError(f"{where} ({item['id']}): can't read {query_path}: {exc}") from exc
    else:
        text = str(item["query"])

    return Query(
        id=str(item["id"]),
        text=text,
        description=str(item.get("description", "")),
        order_sensitive=bool(item.get("order_sensitive", False)),
    )


def _no_duplicates(what: str, values: list[str]) -> None:
    seen = set()
    for value in values:
        if value in seen:
            raise ConfigError(f"Duplicate {what}: {value!r}")
        seen.add(value)
