-- Run once by the Virtuoso image when the database is created.
-- Triples without a graph in data.nq go to <http://example.org/graph/default>:
-- Virtuoso has no separate default graph; it queries the union of all graphs.
ld_dir('/data', 'data.nq', 'http://example.org/graph/default');
rdf_loader_run();
checkpoint;
