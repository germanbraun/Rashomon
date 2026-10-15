from rashomon.model import UNBOUND, Term
from rashomon.normalize import STRICT, VALUE, XSD, normalize_term


def lit(value, datatype=None, lang=None):
    return Term(kind="literal", value=value, datatype=datatype, lang=lang)


def test_numbers_keep_datatype_in_strict_mode():
    assert normalize_term(lit("2.50", XSD + "decimal"), STRICT) == "2.5^^xsd:decimal"
    assert normalize_term(lit("2.5E0", XSD + "double"), STRICT) == "2.5^^xsd:double"


def test_numbers_compare_by_value_in_value_mode():
    values = {normalize_term(lit(v, XSD + dt), VALUE) for v, dt in
              [("5", "integer"), ("5.0", "decimal"), ("5.0E0", "double")]}
    assert values == {"5"}


def test_float_noise_is_rounded_away():
    a = normalize_term(lit("0.30000000000000004", XSD + "double"), STRICT, decimal_places=6)
    b = normalize_term(lit("0.3", XSD + "double"), STRICT, decimal_places=6)
    assert a == b == "0.3^^xsd:double"


def test_plain_literal_equals_xsd_string():
    assert normalize_term(lit("a")) == normalize_term(lit("a", XSD + "string")) == '"a"'


def test_language_tags_are_case_insensitive_but_kept():
    assert normalize_term(lit("chat", lang="en-GB")) == '"chat"@en-gb'
    assert normalize_term(lit("chat", lang="en")) != normalize_term(lit("chat"))


def test_other_terms():
    assert normalize_term(Term(kind="iri", value="http://ex/a")) == "<http://ex/a>"
    assert normalize_term(Term(kind="bnode", value="b0")) == "_:bnode"
    assert normalize_term(UNBOUND) == "UNBOUND"
    assert normalize_term(lit("abc", XSD + "integer")) == '"abc"^^<http://www.w3.org/2001/XMLSchema#integer>'
