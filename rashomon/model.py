"""Plain data classes shared by the whole pipeline.

Adapted from sparql-kata's model.py. Nothing here knows about HTTP or RDF
libraries: client.py turns SPARQL JSON results into these classes, and
everything after that works on plain Python data.

Pipeline overview:

    client.run_query()            -> RawResult   (rows of Term objects)
    normalize.normalize_result()  -> ResultSet   (rows of plain strings)
    compare.compare_engines()     -> QueryComparison
    report.render_*()             -> text / markdown / JSON
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Term:
    """One RDF term from a query result.

    kind is one of: "iri", "bnode", "literal", "unbound".
    For literals, `datatype` and `lang` may be set.
    """

    kind: str
    value: str = ""
    datatype: str | None = None
    lang: str | None = None


UNBOUND = Term(kind="unbound")


@dataclass
class RawResult:
    """A query result as returned by an endpoint, before normalization."""

    query_type: str  # "SELECT" or "ASK"
    variables: list[str] = field(default_factory=list)  # SELECT only, in projection order
    rows: list[tuple[Term, ...]] = field(default_factory=list)
    ask_answer: bool | None = None  # ASK only


# A normalized row: one readable string per column, e.g. ("<http://ex/ana>", '"Ana"', "UNBOUND")
Row = tuple[str, ...]


@dataclass
class ResultSet:
    """A normalized query result. This is what gets compared."""

    query_type: str
    variables: list[str] = field(default_factory=list)
    rows: list[Row] = field(default_factory=list)
    ask_answer: bool | None = None


# Outcome of running one query on one endpoint.
STATUS_OK = "ok"
STATUS_ERROR = "error"      # HTTP error, parse error, unsupported result...
STATUS_TIMEOUT = "timeout"  # client-side timeout reached


@dataclass
class EngineRun:
    endpoint: str
    status: str
    raw: RawResult | None = None
    error: str | None = None
    seconds: float | None = None  # wall-clock, including HTTP: indicative only
    warning: str | None = None  # the engine flagged the answer as partial (see client.py)
