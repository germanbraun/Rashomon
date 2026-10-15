"""Compare the answers several engines gave to the same query.

SELECT results are compared as multisets (bags) of rows, as in sparql-kata:
row order is ignored unless the query sets order_sensitive, but duplicates
DO count. Columns are matched by variable name, because engines may order
the columns of `SELECT *` differently.

Engines are grouped by identical answers. The biggest group becomes the
*baseline* (ties: the endpoint listed first in the config) and every other
group is diffed against it. The baseline is just the most common answer,
NOT the correct one: deciding who follows the spec is left to the reader.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .model import STATUS_OK, EngineRun, ResultSet, Row
from .normalize import STRICT, VALUE, normalize_result

# Verdicts, one per query.
AGREE = "agree"            # all engines that answered gave the same answer
SAME_VALUES = "same-values"  # same rows when numbers are compared by value; datatypes differ
DISAGREE = "disagree"      # different rows, columns or booleans
INCOMPLETE = "incomplete"  # fewer than two engines answered, nothing to compare

# Why a group differs from the baseline.
PROBLEM_QUERY_TYPE = "query_type"
PROBLEM_ASK_ANSWER = "ask_answer"
PROBLEM_COLUMNS = "columns"  # different variable names
PROBLEM_ROWS = "rows"        # some rows missing and/or extra
PROBLEM_ORDER = "order"      # same rows, different order (order_sensitive only)


@dataclass
class AnswerGroup:
    endpoints: list[str]
    result: ResultSet  # normalized at the STRICT level


@dataclass
class GroupDiff:
    """How one non-baseline group differs from the baseline."""

    endpoints: list[str]
    problem: str
    missing_rows: list[Row] = field(default_factory=list)  # in baseline, not in this group
    extra_rows: list[Row] = field(default_factory=list)    # in this group, not in baseline
    # True when this group equals the baseline once numbers are compared by value.
    same_values: bool = False

    @property
    def is_subset(self) -> bool:
        """Only rows missing, none extra: typical of truncation or a result limit."""
        return self.problem == PROBLEM_ROWS and bool(self.missing_rows) and not self.extra_rows


@dataclass
class QueryComparison:
    query_id: str
    verdict: str
    runs: list[EngineRun]
    groups: list[AnswerGroup] = field(default_factory=list)  # baseline first
    diffs: list[GroupDiff] = field(default_factory=list)     # one per group after the baseline

    @property
    def failed(self) -> list[EngineRun]:
        return [run for run in self.runs if run.status != STATUS_OK]


def compare_engines(
    query_id: str,
    runs: list[EngineRun],
    order_sensitive: bool = False,
    decimal_places: int = 6,
) -> QueryComparison:
    answered = [run for run in runs if run.status == STATUS_OK]
    if len(answered) < 2:
        return QueryComparison(query_id=query_id, verdict=INCOMPLETE, runs=runs)

    strict = {run.endpoint: normalize_result(run.raw, STRICT, decimal_places) for run in answered}
    value = {run.endpoint: normalize_result(run.raw, VALUE, decimal_places) for run in answered}

    groups = _group(strict, order_sensitive)
    value_group_count = len(_group(value, order_sensitive))

    if len(groups) == 1:
        verdict = AGREE
    elif value_group_count == 1:
        verdict = SAME_VALUES
    else:
        verdict = DISAGREE

    baseline = groups[0].result
    baseline_by_value = fingerprint(value[groups[0].endpoints[0]], order_sensitive)
    diffs = [
        GroupDiff(
            endpoints=group.endpoints,
            same_values=fingerprint(value[group.endpoints[0]], order_sensitive) == baseline_by_value,
            **_diff(baseline, group.result, order_sensitive),
        )
        for group in groups[1:]
    ]
    return QueryComparison(query_id=query_id, verdict=verdict, runs=runs, groups=groups, diffs=diffs)


def _group(results: dict[str, ResultSet], order_sensitive: bool) -> list[AnswerGroup]:
    """Group endpoints with identical answers; biggest group first, stable on ties."""
    by_key: dict[tuple, AnswerGroup] = {}
    for endpoint, result in results.items():  # dicts keep config order
        key = fingerprint(result, order_sensitive)
        if key in by_key:
            by_key[key].endpoints.append(endpoint)
        else:
            by_key[key] = AnswerGroup(endpoints=[endpoint], result=result)
    return sorted(by_key.values(), key=lambda group: -len(group.endpoints))


def fingerprint(result: ResultSet, order_sensitive: bool) -> tuple:
    """A hashable key that is equal for two results iff they count as the same answer."""
    if result.query_type == "ASK":
        return ("ASK", result.ask_answer)
    names = tuple(sorted(result.variables))
    rows = _rows_by_name(result, list(names))
    return ("SELECT", names, tuple(rows if order_sensitive else sorted(rows)))


def _rows_by_name(result: ResultSet, names: list[str]) -> list[Row]:
    """Rows with columns reordered to follow `names`."""
    positions = [result.variables.index(name) for name in names]
    return [tuple(row[i] for i in positions) for row in result.rows]


def _diff(baseline: ResultSet, other: ResultSet, order_sensitive: bool) -> dict:
    if baseline.query_type != other.query_type:
        return {"problem": PROBLEM_QUERY_TYPE}
    if baseline.query_type == "ASK":
        return {"problem": PROBLEM_ASK_ANSWER}
    if set(baseline.variables) != set(other.variables):
        return {"problem": PROBLEM_COLUMNS}

    # Show rows in the baseline's column order, which is what readers expect.
    other_rows = _rows_by_name(other, baseline.variables)
    baseline_bag = Counter(baseline.rows)
    other_bag = Counter(other_rows)
    # Counter subtraction keeps only positive counts: a row the baseline has
    # twice and the other group once appears once in `missing`.
    missing = sorted((baseline_bag - other_bag).elements())
    extra = sorted((other_bag - baseline_bag).elements())
    if missing or extra:
        return {"problem": PROBLEM_ROWS, "missing_rows": missing, "extra_rows": extra}

    assert order_sensitive, "groups with equal bags of rows can only differ in order"
    return {"problem": PROBLEM_ORDER}
