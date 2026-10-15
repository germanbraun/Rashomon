from rashomon.compare import (
    AGREE,
    DISAGREE,
    INCOMPLETE,
    PROBLEM_ORDER,
    PROBLEM_ROWS,
    SAME_VALUES,
    compare_engines,
)
from rashomon.model import STATUS_ERROR, STATUS_OK, EngineRun, RawResult, Term
from rashomon.normalize import XSD

ALICE = Term(kind="iri", value="http://ex/alice")
BOB = Term(kind="iri", value="http://ex/bob")


def num(value, datatype="integer"):
    return Term(kind="literal", value=value, datatype=XSD + datatype)


def ok(name, variables, rows):
    return EngineRun(endpoint=name, status=STATUS_OK, seconds=0.01,
                     raw=RawResult(query_type="SELECT", variables=variables, rows=rows))


def test_agree_ignores_row_and_column_order():
    a = ok("a", ["s", "n"], [(ALICE, num("1")), (BOB, num("2"))])
    b = ok("b", ["n", "s"], [(num("2"), BOB), (num("1"), ALICE)])
    assert compare_engines("q", [a, b]).verdict == AGREE


def test_datatype_only_difference():
    a = ok("a", ["avg"], [(num("2.5", "decimal"),)])
    b = ok("b", ["avg"], [(num("2.5E0", "double"),)])
    result = compare_engines("q", [a, b])
    assert result.verdict == SAME_VALUES
    assert result.diffs[0].missing_rows == [("2.5^^xsd:decimal",)]
    assert result.diffs[0].extra_rows == [("2.5^^xsd:double",)]
    assert result.diffs[0].same_values


def test_same_values_is_per_group():
    a = ok("a", ["n"], [(num("3"),)])
    b = ok("b", ["n"], [(num("3", "int"),)])
    c = ok("c", ["n"], [(num("4"),)])
    d = ok("d", ["n"], [(num("3"),)])
    result = compare_engines("q", [a, b, c, d])
    assert result.verdict == DISAGREE
    assert [(diff.endpoints, diff.same_values) for diff in result.diffs] == [(["b"], True), (["c"], False)]


def test_majority_is_baseline_and_duplicates_count():
    a = ok("a", ["s"], [(ALICE,)])
    b = ok("b", ["s"], [(ALICE,), (ALICE,)])
    c = ok("c", ["s"], [(ALICE,), (ALICE,)])
    result = compare_engines("q", [a, b, c])
    assert result.verdict == DISAGREE
    assert result.groups[0].endpoints == ["b", "c"]
    diff = result.diffs[0]
    assert diff.endpoints == ["a"]
    assert diff.problem == PROBLEM_ROWS
    assert diff.missing_rows == [("<http://ex/alice>",)]
    assert diff.is_subset


def test_order_sensitive():
    a = ok("a", ["s"], [(ALICE,), (BOB,)])
    b = ok("b", ["s"], [(BOB,), (ALICE,)])
    assert compare_engines("q", [a, b]).verdict == AGREE
    result = compare_engines("q", [a, b], order_sensitive=True)
    assert result.verdict == DISAGREE
    assert result.diffs[0].problem == PROBLEM_ORDER


def test_failures_are_kept_aside():
    a = ok("a", ["s"], [(ALICE,)])
    b = ok("b", ["s"], [(ALICE,)])
    c = EngineRun(endpoint="c", status=STATUS_ERROR, error="HTTP 400")
    result = compare_engines("q", [a, b, c])
    assert result.verdict == AGREE
    assert [run.endpoint for run in result.failed] == ["c"]
    assert compare_engines("q", [a, c]).verdict == INCOMPLETE
