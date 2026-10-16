# SPARQL engine comparison

| query | verdict | fuseki | oxigraph | virtuoso | qlever | graphdb | anzograph |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sum-avg-mixed | DISAGREE | A 0.831s | A 0.027s | B 0.119s | B 0.127s | A 0.319s | C 0.426s |
| avg-with-string | DISAGREE | A 0.385s | A 0.011s | B 0.025s | C 0.011s | A 0.062s | D 0.213s |
| integer-division | DISAGREE | A 0.163s | A 0.016s | B 0.019s | A 0.031s | A 0.166s | C 0.214s |
| filter-in-optional | DISAGREE | A 0.946s | A 0.025s | B 0.056s | C 0.140s | B 0.398s | D 0.469s |
| filter-scope | DISAGREE | A 0.470s | A 0.014s | B 0.036s | A 0.037s | C 0.273s | A 0.147s |
| plain-vs-xsd-string | DISAGREE | A 0.157s | A 0.008s | B 0.011s | A 0.012s | A 0.054s | A 0.135s |
| language-tags | DISAGREE | A 0.330s | A 0.009s | C 0.024s | B 0.036s | A 0.062s | B 0.409s |
| distinct-count | datatypes differ | A 0.720s | A 0.024s | A 0.084s | B 0.061s | A 0.308s | C 0.506s |
| group-concat-order | DISAGREE | B 0.625s | C 0.032s | D 0.093s | A 0.038s | A 0.193s | E 0.354s |
| default-graph | DISAGREE | A 0.346s | A 0.014s | B 0.046s | C 0.018s | B 0.103s | D 0.128s |
| order-by-mixed | DISAGREE | A 0.293s | B 0.007s | A 0.009s | C 0.019s | B 0.134s | D 0.539s |

Same letter = same answer. A is the most common answer, not necessarily the correct one. ERR = error, T/O = timeout, ! = engine flagged a partial result.

_Times are wall-clock seconds for a single run measured by this client, including HTTP and JSON parsing, with no warm-up. Indicative only, not a benchmark._

## sum-avg-mixed [DISAGREE]: SUM/AVG over integer, decimal and double

```
A (baseline): fuseki, oxigraph, graphdb -> 1 row
B: virtuoso, qlever -> 1 row
C: anzograph -> 1 row

B vs A: same values, only datatypes differ
  columns: ?sum | ?avg
  only in A (1):
  - 14^^xsd:double | 4.666667^^xsd:double
  only in B (1):
  + 14^^xsd:decimal | 4.666667^^xsd:decimal

C vs A:
  columns: ?sum | ?avg
  only in A (1):
  - 14^^xsd:double | 4.666667^^xsd:double
  only in C (1):
  + 14^^xsd:double | 4.66667^^xsd:double
```

## avg-with-string [DISAGREE]: AVG when one value is a string

```
A (baseline): fuseki, oxigraph, graphdb -> 1 row
B: virtuoso -> 1 row
C: qlever -> 1 row
D: anzograph -> 1 row

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

D vs A: same values, only datatypes differ
  columns: ?avg | ?n
  only in A (1):
  - UNBOUND | 4^^xsd:integer
  only in D (1):
  + UNBOUND | 4^^xsd:long
```

## integer-division [DISAGREE]: AVG and division over integers

```
A (baseline): fuseki, oxigraph, qlever, graphdb -> 1 row
B: virtuoso -> 1 row
C: anzograph -> 1 row

B vs A:
  columns: ?avg | ?ratio | ?third
  only in A (1):
  - 23.5^^xsd:decimal | 23.5^^xsd:decimal | 0.333333^^xsd:decimal
  only in B (1):
  + 23.5^^xsd:decimal | 23^^xsd:integer | 0^^xsd:integer

C vs A:
  columns: ?avg | ?ratio | ?third
  only in A (1):
  - 23.5^^xsd:decimal | 23.5^^xsd:decimal | 0.333333^^xsd:decimal
  only in C (1):
  + 23.5^^xsd:double | 23^^xsd:long | 0^^xsd:int
```

## filter-in-optional [DISAGREE]: FILTER inside OPTIONAL

```
A (baseline): fuseki, oxigraph -> 3 rows
B: virtuoso, graphdb -> 4 rows
C: qlever -> 4 rows
D: anzograph -> 3 rows

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

D vs A: same values, only datatypes differ
  columns: ?person | ?age
  only in A (1):
  - <http://example.org/ana> | 30^^xsd:integer
  only in D (1):
  + <http://example.org/ana> | 30^^xsd:int
```

## filter-scope [DISAGREE]: FILTER in a nested group can't see outer variables

```
A (baseline): fuseki, oxigraph, qlever, anzograph -> 0 rows
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
A (baseline): fuseki, oxigraph, qlever, graphdb, anzograph -> 1 row
B: virtuoso -> 2 rows

B vs A:
  columns: ?name | ?datatype
  only in B (1):
  + "Bob" | <http://www.w3.org/2001/XMLSchema#string>
```

## language-tags [DISAGREE]: string functions on language-tagged literals

```
A (baseline): fuseki, oxigraph, graphdb -> 2 rows
B: qlever, anzograph -> 2 rows
C: virtuoso -> 2 rows

B vs A: same values, only datatypes differ
  columns: ?name | ?upper | ?shout | ?length | ?english
  only in A (2):
  - "Ana"@es | "ANA"@es | "Ana!" | 3^^xsd:integer | "false"^^<http://www.w3.org/2001/XMLSchema#boolean>
  - "Anna"@en-gb | "ANNA"@en-gb | "Anna!" | 4^^xsd:integer | "true"^^<http://www.w3.org/2001/XMLSchema#boolean>
  only in B (2):
  + "Ana"@es | "ANA"@es | "Ana!" | 3^^xsd:int | "false"^^<http://www.w3.org/2001/XMLSchema#boolean>
  + "Anna"@en-gb | "ANNA"@en-gb | "Anna!" | 4^^xsd:int | "true"^^<http://www.w3.org/2001/XMLSchema#boolean>

C vs A:
  columns: ?name | ?upper | ?shout | ?length | ?english
  only in A (2):
  - "Ana"@es | "ANA"@es | "Ana!" | 3^^xsd:integer | "false"^^<http://www.w3.org/2001/XMLSchema#boolean>
  - "Anna"@en-gb | "ANNA"@en-gb | "Anna!" | 4^^xsd:integer | "true"^^<http://www.w3.org/2001/XMLSchema#boolean>
  only in C (2):
  + "Ana"@es | "ANA"@es | "Ana!" | 3^^xsd:integer | 0^^xsd:integer
  + "Anna"@en-gb | "ANNA"@en-gb | "Anna!" | 4^^xsd:integer | 1^^xsd:integer
```

## distinct-count [datatypes differ]: COUNT DISTINCT over blank nodes

```
A (baseline): fuseki, oxigraph, virtuoso, graphdb -> 1 row
B: qlever -> 1 row
C: anzograph -> 1 row

B vs A: same values, only datatypes differ
  columns: ?matches | ?notes | ?tags
  only in A (1):
  - 3^^xsd:integer | 2^^xsd:integer | 2^^xsd:integer
  only in B (1):
  + 3^^xsd:int | 2^^xsd:int | 2^^xsd:int

C vs A: same values, only datatypes differ
  columns: ?matches | ?notes | ?tags
  only in A (1):
  - 3^^xsd:integer | 2^^xsd:integer | 2^^xsd:integer
  only in C (1):
  + 3^^xsd:long | 2^^xsd:long | 2^^xsd:long
```

## group-concat-order [DISAGREE]: GROUP_CONCAT order is undefined

```
A (baseline): qlever, graphdb -> 1 row
B: fuseki -> 1 row
C: oxigraph -> 1 row
D: virtuoso -> 1 row
E: anzograph -> 1 row

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

E vs A:
  columns: ?names
  only in A (1):
  - "Ana, Anna, Bob, Carl, Dave"
  only in E (1):
  + "Ana, Bob, Anna, Carl"
```

## default-graph [DISAGREE]: is the default graph the union of all graphs?

```
A (baseline): fuseki, oxigraph -> 1 row
B: virtuoso, graphdb -> 1 row
C: qlever -> 1 row
D: anzograph -> 1 row

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

D vs A: same values, only datatypes differ
  columns: ?people
  only in A (1):
  - 3^^xsd:integer
  only in D (1):
  + 3^^xsd:long
```

## order-by-mixed [DISAGREE]: ORDER BY over mixed numbers and a string

```
A (baseline): fuseki, virtuoso -> 4 rows
B: oxigraph, graphdb -> 4 rows
C: qlever -> 4 rows
D: anzograph -> 4 rows

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

D vs A:
  columns: ?price
  only in A (2):
  - 10^^xsd:integer
  - 2.5^^xsd:decimal
  only in D (2):
  + 10^^xsd:int
  + 2.5^^xsd:double
```
