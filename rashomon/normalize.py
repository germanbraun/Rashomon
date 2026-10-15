"""Turn RDF terms into plain, comparable strings.

Adapted from sparql-kata's normalize.py. Two results are considered equal
when their normalized rows are equal, so this module decides what "the same
value" means. There are two levels:

    STRICT  numbers keep their datatype:  5^^xsd:integer vs 5^^xsd:decimal differ
    VALUE   numbers compare by value:     "5", "5.0"^^xsd:decimal, "5E0"^^xsd:double -> 5

Engines that agree under VALUE but not under STRICT usually differ in the
datatype an aggregate returns (AVG over integers: xsd:decimal or xsd:double?).
That is worth reporting, but it is a different kind of disagreement than
returning other rows.

Rules shared by both levels:

    IRI                      -> <http://example.org/x>
    blank node               -> _:bnode    (all blank nodes compare equal, see note)
    unbound variable         -> UNBOUND
    plain / xsd:string       -> "text"     (identical in RDF 1.1)
    language-tagged literal  -> "text"@en  (tag lowercased: tags are case-insensitive)
    other typed literal      -> "2024-01-01"^^<http://www.w3.org/2001/XMLSchema#date>
    numbers                  -> rounded to `decimal_places`, so float noise
                                (0.30000000000000004) doesn't count as a difference

Note on blank nodes: their labels are arbitrary and differ between engines,
so they all compare equal. Queries that project blank nodes can therefore
hide differences; COUNT them instead.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from .model import RawResult, ResultSet, Row, Term

STRICT = "strict"
VALUE = "value"
LEVELS = (STRICT, VALUE)

XSD = "http://www.w3.org/2001/XMLSchema#"
XSD_STRING = XSD + "string"

NUMERIC_DATATYPES = frozenset(
    XSD + name
    for name in (
        "integer", "decimal", "double", "float",
        "int", "long", "short", "byte",
        "nonNegativeInteger", "nonPositiveInteger",
        "positiveInteger", "negativeInteger",
        "unsignedInt", "unsignedLong", "unsignedShort", "unsignedByte",
    )
)


def normalize_result(raw: RawResult, level: str, decimal_places: int) -> ResultSet:
    """Normalize every row of a raw result."""
    rows = [normalize_row(row, level, decimal_places) for row in raw.rows]
    return ResultSet(
        query_type=raw.query_type,
        variables=list(raw.variables),
        rows=rows,
        ask_answer=raw.ask_answer,
    )


def normalize_row(row: tuple[Term, ...], level: str = STRICT, decimal_places: int = 6) -> Row:
    return tuple(normalize_term(term, level, decimal_places) for term in row)


def normalize_term(term: Term, level: str = STRICT, decimal_places: int = 6) -> str:
    if term.kind == "unbound":
        return "UNBOUND"
    if term.kind == "bnode":
        return "_:bnode"
    if term.kind == "iri":
        return f"<{term.value}>"
    if term.kind == "literal":
        return _normalize_literal(term, level, decimal_places)
    raise ValueError(f"Unknown term kind: {term.kind!r}")


def _normalize_literal(term: Term, level: str, decimal_places: int) -> str:
    # json.dumps adds quotes and escapes inner quotes/newlines; keeps accents readable.
    quoted = json.dumps(term.value, ensure_ascii=False)

    if term.lang:
        return f"{quoted}@{term.lang.lower()}"

    if term.datatype in NUMERIC_DATATYPES:
        number = _normalize_number(term.value, decimal_places)
        if number is not None:
            if level == VALUE:
                return number
            return f"{number}^^xsd:{term.datatype[len(XSD):]}"
        # Not a valid number (e.g. "abc"^^xsd:integer): fall through and keep it typed.

    if term.datatype is None or term.datatype == XSD_STRING:
        return quoted

    return f"{quoted}^^<{term.datatype}>"


def _normalize_number(lexical: str, decimal_places: int) -> str | None:
    """Return a canonical string for a number, or None if it can't be parsed.

    Examples (decimal_places=6): "5" -> "5", "5.000" -> "5", "1.0E1" -> "10",
    "3.14159265" -> "3.141593".
    """
    try:
        number = Decimal(lexical.strip())
        if not number.is_finite():  # NaN, INF
            return None
        step = Decimal(1).scaleb(-decimal_places)  # 0.000001 for 6 places
        rounded = number.quantize(step).normalize()
    except InvalidOperation:
        return None

    if rounded == 0:
        return "0"  # avoids "-0"
    return format(rounded, "f")  # "f" avoids scientific notation like "1E+1"
