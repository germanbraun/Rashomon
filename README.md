# Rashomon

*Same query, different witnesses, different stories.*

Rashomon runs the same SPARQL queries against several engines (Fuseki,
Oxigraph, Virtuoso, QLever, GraphDB, RDFox, ...) loaded with the same data,
and reports where their answers differ. Engines disagree more often than people
expect, typically on:

- numeric datatypes and precision in aggregates (`AVG`, `SUM`, division)
- `FILTER` scoping, inside `OPTIONAL` and in nested groups
- language tags, string functions, `xsd:string` vs plain literals
- blank nodes, duplicates, `DISTINCT` with aggregates
- what the default graph is (the union of all named graphs, or not)
- errors, timeouts and silently truncated results

This is useful when choosing an engine, when migrating from one to another, and
as teaching material: *same query, three answers. Which one does the spec allow?*

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cd examples
docker compose up -d          # Fuseki, Oxigraph, Virtuoso, QLever, GraphDB
rashomon run rashomon.yaml
```

The engines need up to a minute to load the data. Oxigraph keeps its data in
memory, so if it restarts, run `docker compose up -d` again to reload it. Fuseki has no official ARM
image, so on Apple Silicon it runs emulated and is slow on its first query.

## Config

```yaml
settings:              # optional
  timeout: 30          # seconds per query and endpoint
  decimal_places: 6    # numbers are rounded to this before comparing

endpoints:
  - name: fuseki
    url: http://localhost:3030/ds/query
  - name: oxigraph
    url: http://localhost:7878/query
    headers: {Authorization: "Basic ..."}   # optional

queries:
  - id: avg-mixed
    file: queries/sum-avg-mixed.rq          # relative to the config file
    description: SUM/AVG over integer, decimal and double
  - id: people
    query: SELECT (COUNT(*) AS ?n) WHERE { ?p a <http://example.org/Person> }
    order_sensitive: false                  # set true to compare row order too
```

Queries are sent with the SPARQL 1.1 Protocol (HTTP POST, form-encoded) asking
for `application/sparql-results+json`. SELECT and ASK are supported.

## Reading the report

```
query                verdict           fuseki    oxigraph  virtuoso  qlever    graphdb
integer-division     DISAGREE          A 0.163s  A 0.014s  B 0.014s  A 0.033s  A 0.037s
filter-scope         DISAGREE          A 0.102s  A 0.005s  B 0.005s  A 0.010s  C 0.042s
distinct-count       datatypes differ  A 0.078s  A 0.019s  A 0.007s  B 0.008s  A 0.012s
default-graph        DISAGREE          A 0.061s  A 0.005s  B 0.008s  C 0.007s  B 0.014s
```

See [examples/sample-report.md](examples/sample-report.md) for a full report.

- **Same letter = same answer.** `A` is the most common answer (the *baseline*),
  **not** necessarily the correct one. Each `.rq` file in `examples/queries`
  says what the spec expects.
- **Verdicts:** `agree`; `datatypes differ` (the same rows if numbers are
  compared by value, e.g. `xsd:int` vs `xsd:integer`); `DISAGREE`;
  `incomplete` (fewer than two engines answered).
- `ERR` and `T/O` mark errors and client-side timeouts; the details show the
  engine's error message. `!` means the engine flagged the result as partial
  (Virtuoso's `X-SQL-State` header for "anytime" queries).
- For each disagreement the details list the rows only in `A` (`-`) and only in
  the other group (`+`). A group that only *lacks* rows is flagged as a possible
  truncation or result-size limit.
- **Times are indicative only:** wall-clock seconds for a single run measured
  by the client, including HTTP and JSON parsing, with no warm-up. Do not
  read them as a benchmark.

`--format markdown` and `--format json` produce the same report for a wiki
page or further processing; `-o FILE` writes it to a file. `--endpoint NAME`
and `--query ID` (both repeatable) restrict the run. The exit code is 0 when all
engines agree on every query, 1 otherwise, and 2 for a bad config.

## What counts as "the same"

Results are compared as bags of rows: row order is ignored (unless
`order_sensitive`) but duplicates count. Columns are matched by variable name.
Terms are normalized before comparing:

| term | normalized | note |
|---|---|---|
| IRI | `<http://ex/a>` | |
| blank node | `_:bnode` | labels are arbitrary, so all blank nodes compare equal |
| `"a"` and `"a"^^xsd:string` | `"a"` | identical in RDF 1.1 |
| `"chat"@en-GB` | `"chat"@en-gb` | tags are case-insensitive |
| `"2.50"^^xsd:decimal` | `2.5^^xsd:decimal` | rounded to `decimal_places` |
| other typed literals | `"2024-01-01"^^<...#date>` | |

Numbers are compared twice: with their datatype, and by value only. That is how
the `datatypes differ` verdict is found.

## The example setup

`examples/` contains a small dataset (`data/data.nq`), eleven queries that
probe the known trouble spots, and a `docker-compose.yml` that loads the same
file into every engine. Every engine keeps its default settings, including what
its default graph means, except that GraphDB runs without inference. GraphDB 11
needs a license even for free use, so the compose file uses GraphDB 10.8, on
host port 7201 because 7200 is often taken by a local GraphDB. RDFox also needs
a license and isn't included; add it to `rashomon.yaml` if you have one. All
five engines together need about 2.5 GB of Docker memory.

To compare engines on your own data, replace `data/data.nq` (any N-Quads
file), run `docker compose down -v && docker compose up -d`, and write your
own queries.

## Relation to sparql-kata

The normalization and bag-diff code started as a copy of
[sparql-kata](../SPARQL_Kata)'s `normalize` and `compare` modules. sparql-kata
compares a student's answer against a reference on one engine (rdflib);
Rashomon compares engines against each other over HTTP.
