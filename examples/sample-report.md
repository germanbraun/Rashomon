# SPARQL engine comparison

| query | verdict | fuseki | oxigraph | virtuoso | qlever | graphdb |
| --- | --- | --- | --- | --- | --- | --- |
| sum-avg-mixed | datatypes differ | A 0.221s | A 0.009s | B 0.031s | B 0.039s | A 0.086s |
| avg-with-string | DISAGREE | A 0.088s | A 0.018s | B 0.043s | C 0.008s | A 0.026s |
| integer-division | DISAGREE | A 0.063s | A 0.007s | B 0.009s | A 0.017s | A 0.024s |
| filter-in-optional | DISAGREE | A 0.076s | A 0.004s | B 0.004s | C 0.005s | B 0.017s |
| filter-scope | DISAGREE | A 0.065s | A 0.004s | B 0.003s | A 0.005s | C 0.013s |
| plain-vs-xsd-string | DISAGREE | A 0.065s | A 0.003s | B 0.005s | A 0.007s | A 0.010s |
| language-tags | DISAGREE | A 0.059s | A 0.008s | B 0.009s | C 0.006s | A 0.010s |
| distinct-count | datatypes differ | A 0.056s | A 0.005s | A 0.004s | B 0.007s | A 0.013s |
| group-concat-order | DISAGREE | B 0.051s | C 0.002s | D 0.005s | A 0.006s | A 0.011s |
| default-graph | DISAGREE | A 0.049s | A 0.004s | B 0.003s | C 0.003s | B 0.012s |
| order-by-mixed | DISAGREE | A 0.056s | B 0.003s | A 0.004s | C 0.005s | B 0.012s |

Same letter = same answer. A is the most common answer, not necessarily the correct one. ERR = error, T/O = timeout, ! = engine flagged a partial result.

_Times are wall-clock seconds for a single run measured by this client, including HTTP and JSON parsing, with no warm-up. Indicative only, not a benchmark._

## sum-avg-mixed [datatypes differ]: SUM/AVG over integer, decimal and double

```
A (baseline): fuseki, oxigraph, graphdb -> 1 row
B: virtuoso, qlever -> 1 row

B vs A: same values, only datatypes differ
  columns: ?sum | ?avg
  only in A (1):
  - 14^^xsd:double | 4.666667^^xsd:double
  only in B (1):
  + 14^^xsd:decimal | 4.666667^^xsd:decimal
```

## avg-with-string [DISAGREE]: AVG when one value is a string

```
A (baseline): fuseki, oxigraph, graphdb -> 1 row
B: virtuoso -> 1 row
C: qlever -> 1 row

B vs A:
  columns: ?avg | ?n
  only in A (1):
  - UNBOUND | 4^^xsd:integer
  only in B (1):
  + 3.5^^xsd:decimal | 4^^xsd:integer

C vs A: same values, only datatypes differ
  columns: ?avg | ?n
  only in A (1):
  - UNBOUND | 4^^xsd:integer
  only in C (1):
  + UNBOUND | 4^^xsd:int
```

## integer-division [DISAGREE]: AVG and division over integers

```
A (baseline): fuseki, oxigraph, qlever, graphdb -> 1 row
B: virtuoso -> 1 row

B vs A:
  columns: ?avg | ?ratio | ?third
  only in A (1):
  - 23.5^^xsd:decimal | 23.5^^xsd:decimal | 0.333333^^xsd:decimal
  only in B (1):
  + 23.5^^xsd:decimal | 23^^xsd:integer | 0^^xsd:integer
```

## filter-in-optional [DISAGREE]: FILTER inside OPTIONAL

```
A (baseline): fuseki, oxigraph -> 3 rows
B: virtuoso, graphdb -> 4 rows
C: qlever -> 4 rows

B vs A:
  columns: ?person | ?age
  only in B (1):
  + <http://example.org/dave> | UNBOUND

C vs A:
  columns: ?person | ?age
  only in A (1):
  - <http://example.org/ana> | 30^^xsd:integer
  only in C (2):
  + <http://example.org/ana> | 30^^xsd:int
  + <http://example.org/dave> | UNBOUND
```

## filter-scope [DISAGREE]: FILTER in a nested group can't see outer variables

```
A (baseline): fuseki, oxigraph, qlever -> 0 rows
B: virtuoso -> 2 rows
C: graphdb -> 1 row

B vs A:
  columns: ?person | ?age
  only in B (2):
  + <http://example.org/ana> | 30^^xsd:integer
  + <http://example.org/bob> | 17^^xsd:integer

C vs A:
  columns: ?person | ?age
  only in C (1):
  + <http://example.org/ana> | 30^^xsd:integer
```

## plain-vs-xsd-string [DISAGREE]: "Bob" and "Bob"^^xsd:string are the same literal

```
A (baseline): fuseki, oxigraph, qlever, graphdb -> 1 row
B: virtuoso -> 2 rows

B vs A:
  columns: ?name | ?datatype
  only in B (1):
  + "Bob" | <http://www.w3.org/2001/XMLSchema#string>
```

## language-tags [DISAGREE]: string functions on language-tagged literals

```
A (baseline): fuseki, oxigraph, graphdb -> 2 rows
B: virtuoso -> 2 rows
C: qlever -> 2 rows

B vs A:
  columns: ?name | ?upper | ?shout | ?length | ?english
  only in A (2):
  - "Ana"@es | "ANA"@es | "Ana!" | 3^^xsd:integer | "false"^^<http://www.w3.org/2001/XMLSchema#boolean>
  - "Anna"@en-gb | "ANNA"@en-gb | "Anna!" | 4^^xsd:integer | "true"^^<http://www.w3.org/2001/XMLSchema#boolean>
  only in B (2):
  + "Ana"@es | "ANA"@es | "Ana!" | 3^^xsd:integer | 0^^xsd:integer
  + "Anna"@en-gb | "ANNA"@en-gb | "Anna!" | 4^^xsd:integer | 1^^xsd:integer

C vs A: same values, only datatypes differ
  columns: ?name | ?upper | ?shout | ?length | ?english
  only in A (2):
  - "Ana"@es | "ANA"@es | "Ana!" | 3^^xsd:integer | "false"^^<http://www.w3.org/2001/XMLSchema#boolean>
  - "Anna"@en-gb | "ANNA"@en-gb | "Anna!" | 4^^xsd:integer | "true"^^<http://www.w3.org/2001/XMLSchema#boolean>
  only in C (2):
  + "Ana"@es | "ANA"@es | "Ana!" | 3^^xsd:int | "false"^^<http://www.w3.org/2001/XMLSchema#boolean>
  + "Anna"@en-gb | "ANNA"@en-gb | "Anna!" | 4^^xsd:int | "true"^^<http://www.w3.org/2001/XMLSchema#boolean>
```

## distinct-count [datatypes differ]: COUNT DISTINCT over blank nodes

```
A (baseline): fuseki, oxigraph, virtuoso, graphdb -> 1 row
B: qlever -> 1 row

B vs A: same values, only datatypes differ
  columns: ?matches | ?notes | ?tags
  only in A (1):
  - 3^^xsd:integer | 2^^xsd:integer | 2^^xsd:integer
  only in B (1):
  + 3^^xsd:int | 2^^xsd:int | 2^^xsd:int
```

## group-concat-order [DISAGREE]: GROUP_CONCAT order is undefined

```
A (baseline): qlever, graphdb -> 1 row
B: fuseki -> 1 row
C: oxigraph -> 1 row
D: virtuoso -> 1 row

B vs A:
  columns: ?names
  only in A (1):
  - "Ana, Anna, Bob, Carl, Dave"
  only in B (1):
  + "Anna, Ana, Bob, Carl"

C vs A:
  columns: ?names
  only in A (1):
  - "Ana, Anna, Bob, Carl, Dave"
  only in C (1):
  + "Carl, Bob, Anna, Ana"

D vs A:
  columns: ?names
  only in A (1):
  - "Ana, Anna, Bob, Carl, Dave"
  only in D (1):
  + "Anna, Ana, Bob, Bob, Carl, Dave"
```

## default-graph [DISAGREE]: is the default graph the union of all graphs?

```
A (baseline): fuseki, oxigraph -> 1 row
B: virtuoso, graphdb -> 1 row
C: qlever -> 1 row

B vs A:
  columns: ?people
  only in A (1):
  - 3^^xsd:integer
  only in B (1):
  + 4^^xsd:integer

C vs A:
  columns: ?people
  only in A (1):
  - 3^^xsd:integer
  only in C (1):
  + 4^^xsd:int
```

## order-by-mixed [DISAGREE]: ORDER BY over mixed numbers and a string

```
A (baseline): fuseki, virtuoso -> 4 rows
B: oxigraph, graphdb -> 4 rows
C: qlever -> 4 rows

B vs A:
  same rows, different order

C vs A:
  columns: ?price
  only in A (2):
  - 1.5^^xsd:double
  - 10^^xsd:integer
  only in C (2):
  + 1.5^^xsd:decimal
  + 10^^xsd:int
```
