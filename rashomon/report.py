"""Render comparisons as a plain-text, Markdown or JSON report.

The summary table has one row per query and one column per endpoint. Each
cell holds a group letter: engines with the same letter gave the same
answer, and A is the most common answer (the baseline), not necessarily the
correct one. Details follow for every query where engines didn't all agree.
"""

from __future__ import annotations

import json
import string
from dataclasses import asdict

from .compare import (
    AGREE,
    DISAGREE,
    INCOMPLETE,
    PROBLEM_ASK_ANSWER,
    PROBLEM_COLUMNS,
    PROBLEM_ORDER,
    PROBLEM_QUERY_TYPE,
    SAME_VALUES,
    QueryComparison,
)
from .model import STATUS_TIMEOUT, ResultSet, Row

MAX_ROWS_SHOWN = 10  # per side of a diff

VERDICT_LABELS = {
    AGREE: "agree",
    SAME_VALUES: "datatypes differ",
    DISAGREE: "DISAGREE",
    INCOMPLETE: "incomplete",
}

TIMING_NOTE = (
    "Times are wall-clock seconds for a single run measured by this client, "
    "including HTTP and JSON parsing, with no warm-up. Indicative only, not a benchmark."
)
LEGEND = (
    "Same letter = same answer. A is the most common answer, not necessarily the correct one. "
    "ERR = error, T/O = timeout, ! = engine flagged a partial result."
)


def render_text(comparisons: list[QueryComparison], endpoints: list[str], descriptions: dict[str, str]) -> str:
    header, rows = _summary(comparisons, endpoints)
    widths = [max(len(line[i]) for line in [header, *rows]) for i in range(len(header))]
    table = [
        "  ".join(cell.ljust(width) for cell, width in zip(line, widths)).rstrip()
        for line in [header, *rows]
    ]
    out = [*table, "", LEGEND, TIMING_NOTE]
    for comparison in comparisons:
        if comparison.verdict != AGREE or comparison.failed:
            out += ["", _title(comparison, descriptions)]
            out += ["  " + line for line in _details(comparison)]
    return "\n".join(out) + "\n"


def render_markdown(comparisons: list[QueryComparison], endpoints: list[str], descriptions: dict[str, str]) -> str:
    header, rows = _summary(comparisons, endpoints)
    out = [
        "# SPARQL engine comparison",
        "",
        _md_row(header),
        _md_row(["---"] * len(header)),
        *(_md_row(row) for row in rows),
        "",
        LEGEND,
        "",
        f"_{TIMING_NOTE}_",
    ]
    for comparison in comparisons:
        if comparison.verdict != AGREE or comparison.failed:
            out += ["", f"## {_title(comparison, descriptions)}", "", "```", *_details(comparison), "```"]
    return "\n".join(out) + "\n"


def render_json(comparisons: list[QueryComparison]) -> str:
    def encode(comparison: QueryComparison) -> dict:
        doc = asdict(comparison)
        for run in doc["runs"]:
            run.pop("raw")  # the normalized rows in "groups" are what matters
        return doc

    return json.dumps({"queries": [encode(c) for c in comparisons]}, indent=2, ensure_ascii=False) + "\n"


def _summary(comparisons: list[QueryComparison], endpoints: list[str]) -> tuple[list[str], list[list[str]]]:
    header = ["query", "verdict", *endpoints]
    rows = []
    for comparison in comparisons:
        letters = _group_letters(comparison)
        runs = {run.endpoint: run for run in comparison.runs}
        cells = []
        for endpoint in endpoints:
            run = runs[endpoint]
            if endpoint in letters:
                mark = letters[endpoint] + ("!" if run.warning else "")
            else:
                mark = "T/O" if run.status == STATUS_TIMEOUT else "ERR"
            cells.append(f"{mark} {run.seconds:.3f}s")
        rows.append([comparison.query_id, VERDICT_LABELS[comparison.verdict], *cells])
    return header, rows


def _group_letters(comparison: QueryComparison) -> dict[str, str]:
    """endpoint -> group letter. An INCOMPLETE comparison has no groups; its lone answer gets A."""
    if not comparison.groups:
        return {run.endpoint: "A" for run in comparison.runs if run.raw is not None}
    return {
        endpoint: string.ascii_uppercase[i]
        for i, group in enumerate(comparison.groups)
        for endpoint in group.endpoints
    }


def _title(comparison: QueryComparison, descriptions: dict[str, str]) -> str:
    description = descriptions.get(comparison.query_id)
    suffix = f": {description}" if description else ""
    return f"{comparison.query_id} [{VERDICT_LABELS[comparison.verdict]}]{suffix}"


def _details(comparison: QueryComparison) -> list[str]:
    lines = []
    for i, group in enumerate(comparison.groups):
        letter = string.ascii_uppercase[i]
        role = " (baseline)" if i == 0 else ""
        lines.append(f"{letter}{role}: {', '.join(group.endpoints)} -> {_size(group.result)}")

    for i, diff in enumerate(comparison.diffs, start=1):
        letter = string.ascii_uppercase[i]
        lines.append("")
        lines.append(f"{letter} vs A:" + (" same values, only datatypes differ" if diff.same_values else ""))
        if diff.problem == PROBLEM_QUERY_TYPE:
            lines.append("  different query result types")
        elif diff.problem == PROBLEM_ASK_ANSWER:
            lines.append(f"  ASK answered {comparison.groups[i].result.ask_answer}, "
                         f"baseline {comparison.groups[0].result.ask_answer}")
        elif diff.problem == PROBLEM_COLUMNS:
            lines.append(f"  columns {comparison.groups[i].result.variables}, "
                         f"baseline {comparison.groups[0].result.variables}")
        elif diff.problem == PROBLEM_ORDER:
            lines.append("  same rows, different order")
        else:
            lines.append("  columns: " + " | ".join("?" + v for v in comparison.groups[0].result.variables))
            lines += _rows("-", f"only in A ({len(diff.missing_rows)})", diff.missing_rows)
            lines += _rows("+", f"only in {letter} ({len(diff.extra_rows)})", diff.extra_rows)
            if diff.is_subset:
                lines.append(f"  note: {letter} is a strict subset of A: "
                             "possible truncation or result-size limit")

    for run in comparison.runs:
        if run.warning:
            lines.append(f"warning from {run.endpoint}: {run.warning}")
    for run in comparison.failed:
        lines.append(f"{run.status} on {run.endpoint}: {run.error}")
    return lines


def _size(result: ResultSet) -> str:
    if result.query_type == "ASK":
        return f"ASK {result.ask_answer}"
    return f"{len(result.rows)} row{'s' if len(result.rows) != 1 else ''}"


def _rows(sign: str, label: str, rows: list[Row]) -> list[str]:
    if not rows:
        return []
    lines = [f"  {label}:"]
    lines += [f"  {sign} " + " | ".join(row) for row in rows[:MAX_ROWS_SHOWN]]
    if len(rows) > MAX_ROWS_SHOWN:
        lines.append(f"    ... and {len(rows) - MAX_ROWS_SHOWN} more")
    return lines


def _md_row(cells: list[str]) -> str:
    return "| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |"
