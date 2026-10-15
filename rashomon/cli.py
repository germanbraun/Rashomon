"""Command line interface.

    rashomon run CONFIG [--format text|markdown|json] [--output FILE]
                        [--endpoint NAME ...] [--query ID ...]

Exit codes: 0 all engines agree on every query, 1 some disagreement or
failure, 2 bad config or arguments.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compare import AGREE
from .config import ConfigError, load_config
from .report import render_json, render_markdown, render_text
from .runner import run_all

EXIT_AGREE = 0
EXIT_DIFFERENCES = 1
EXIT_USAGE = 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rashomon",
        description="Run the same SPARQL queries on several engines and report where the answers differ.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run all queries on all endpoints and compare")
    run.add_argument("config", type=Path, help="YAML file listing endpoints and queries")
    run.add_argument("--format", choices=("text", "markdown", "json"), default="text")
    run.add_argument("--output", "-o", type=Path, help="write the report to this file instead of stdout")
    run.add_argument("--endpoint", "-e", action="append", metavar="NAME",
                     help="only use this endpoint (repeatable)")
    run.add_argument("--query", "-q", action="append", metavar="ID",
                     help="only run this query (repeatable)")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        endpoints = _select(config.endpoints, args.endpoint, "name", "endpoint")
        queries = _select(config.queries, args.query, "id", "query")
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    def progress(query, run):
        print(f"  {query.id} @ {run.endpoint}: {run.status}", file=sys.stderr)

    comparisons = run_all(config, endpoints, queries, on_run=progress)

    names = [endpoint.name for endpoint in endpoints]
    if args.format == "json":
        report = render_json(comparisons)
    elif args.format == "markdown":
        report = render_markdown(comparisons, names, {q.id: q.description for q in queries})
    else:
        report = render_text(comparisons, names, {q.id: q.description for q in queries})

    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(report)

    all_agree = all(c.verdict == AGREE and not c.failed for c in comparisons)
    return EXIT_AGREE if all_agree else EXIT_DIFFERENCES


def _select(items: list, wanted: list[str] | None, key: str, what: str) -> list:
    if not wanted:
        return items
    known = {getattr(item, key) for item in items}
    unknown = [name for name in wanted if name not in known]
    if unknown:
        raise ConfigError(f"Unknown {what}: {', '.join(unknown)}")
    return [item for item in items if getattr(item, key) in wanted]
