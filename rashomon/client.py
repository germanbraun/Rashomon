"""Talk to SPARQL endpoints over HTTP (SPARQL 1.1 Protocol).

The only module that does network I/O. It sends a query, asks for SPARQL
JSON results, and converts them into model.RawResult / model.Term.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

from .model import (
    STATUS_ERROR,
    STATUS_OK,
    STATUS_TIMEOUT,
    UNBOUND,
    EngineRun,
    RawResult,
    Term,
)

ACCEPT = "application/sparql-results+json"
ERROR_BODY_CHARS = 300  # how much of an HTTP error body to keep in the report

# Response headers some engines use to flag partial results instead of failing.
# Virtuoso: "X-SQL-State: S1TAT" when an "anytime query" hit its time limit.
PARTIAL_RESULT_HEADERS = ("X-SQL-State", "X-SQL-Message")


class ResultFormatError(Exception):
    """The response is not a SPARQL JSON result we understand."""


def run_query(
    endpoint: str,
    url: str,
    query: str,
    timeout: float,
    headers: dict[str, str] | None = None,
) -> EngineRun:
    """Run one query on one endpoint. Never raises for engine-side problems."""
    data = urllib.parse.urlencode({"query": query}).encode()
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Accept": ACCEPT,
            "Content-Type": "application/x-www-form-urlencoded",
            **(headers or {}),
        },
    )

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            warning = _partial_result_warning(response.headers)
        seconds = time.perf_counter() - start
        raw = parse_json_results(json.loads(body))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace").strip()[:ERROR_BODY_CHARS]
        return _failed(endpoint, STATUS_ERROR, f"HTTP {exc.code}: {detail}", start)
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            return _failed(endpoint, STATUS_TIMEOUT, f"no answer after {timeout:g}s", start)
        return _failed(endpoint, STATUS_ERROR, f"connection failed: {exc.reason}", start)
    except (socket.timeout, TimeoutError):  # timeout while reading the body
        return _failed(endpoint, STATUS_TIMEOUT, f"no answer after {timeout:g}s", start)
    except OSError as exc:  # e.g. connection reset while reading
        return _failed(endpoint, STATUS_ERROR, f"connection failed: {exc}", start)
    except (ValueError, ResultFormatError) as exc:  # json.JSONDecodeError is a ValueError
        return _failed(endpoint, STATUS_ERROR, f"unreadable result: {exc}", start)

    return EngineRun(endpoint=endpoint, status=STATUS_OK, raw=raw, seconds=seconds, warning=warning)


def _failed(endpoint: str, status: str, error: str, start: float) -> EngineRun:
    return EngineRun(
        endpoint=endpoint, status=status, error=error, seconds=time.perf_counter() - start
    )


def _partial_result_warning(headers) -> str | None:
    found = [f"{name}: {headers[name]}" for name in PARTIAL_RESULT_HEADERS if headers.get(name)]
    return "; ".join(found) or None


def parse_json_results(doc: dict) -> RawResult:
    """Convert a SPARQL 1.1 Query Results JSON document into a RawResult."""
    if not isinstance(doc, dict):
        raise ResultFormatError("expected a JSON object")
    if "boolean" in doc:
        return RawResult(query_type="ASK", ask_answer=bool(doc["boolean"]))
    try:
        variables = list(doc["head"]["vars"])
        bindings = doc["results"]["bindings"]
    except (KeyError, TypeError) as exc:
        raise ResultFormatError(f"missing {exc}") from exc

    rows = [
        tuple(to_term(binding[var]) if var in binding else UNBOUND for var in variables)
        for binding in bindings
    ]
    return RawResult(query_type="SELECT", variables=variables, rows=rows)


def to_term(value: dict) -> Term:
    """Convert one JSON binding ({"type": ..., "value": ...}) into a Term."""
    kind = value.get("type")
    if kind == "uri":
        return Term(kind="iri", value=value["value"])
    if kind == "bnode":
        return Term(kind="bnode", value=value["value"])
    # "typed-literal" is the pre-standard spelling some engines (Virtuoso) still send.
    if kind in ("literal", "typed-literal"):
        return Term(
            kind="literal",
            value=value["value"],
            datatype=value.get("datatype"),
            lang=value.get("xml:lang"),
        )
    raise ResultFormatError(f"unknown binding type {kind!r}")
