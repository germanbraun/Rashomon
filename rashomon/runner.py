"""Run every query on every endpoint and compare the answers."""

from __future__ import annotations

from typing import Callable

from .client import run_query
from .compare import QueryComparison, compare_engines
from .config import Config, Endpoint, Query
from .model import EngineRun


def run_all(
    config: Config,
    endpoints: list[Endpoint],
    queries: list[Query],
    on_run: Callable[[Query, EngineRun], None] | None = None,
) -> list[QueryComparison]:
    """Queries run one at a time, never in parallel, so timings don't interfere."""
    comparisons = []
    for query in queries:
        runs = []
        for endpoint in endpoints:
            run = run_query(endpoint.name, endpoint.url, query.text, config.timeout, endpoint.headers)
            runs.append(run)
            if on_run:
                on_run(query, run)
        comparisons.append(
            compare_engines(query.id, runs, query.order_sensitive, config.decimal_places)
        )
    return comparisons
