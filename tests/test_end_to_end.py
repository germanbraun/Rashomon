"""Run the CLI against fake SPARQL endpoints served from a local HTTP server."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from rashomon.cli import EXIT_AGREE, EXIT_DIFFERENCES, EXIT_USAGE, main

XSD = "http://www.w3.org/2001/XMLSchema#"


def select(var, *literals):
    return {
        "head": {"vars": [var]},
        "results": {"bindings": [{var: literal} for literal in literals]},
    }


# path -> (status, JSON body or text, extra headers)
RESPONSES = {
    "/a": (200, select("avg", {"type": "literal", "value": "2.5", "datatype": XSD + "decimal"}), {}),
    "/b": (200, select("avg", {"type": "typed-literal", "value": "2.5", "datatype": XSD + "decimal"}), {}),
    "/c": (200, select("avg", {"type": "literal", "value": "2.5E0", "datatype": XSD + "double"}),
           {"X-SQL-State": "S1TAT"}),
    "/broken": (400, "Parse error near line 1", {}),
}


class FakeEndpoint(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        if self.path == "/slow":
            time.sleep(1)
            return
        status, body, headers = RESPONSES[self.path]
        payload = body if isinstance(body, str) else json.dumps(body)
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload.encode())

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def server_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeEndpoint)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def write_config(tmp_path, url, endpoints):
    lines = ["settings: {timeout: 0.3}", "endpoints:"]
    lines += [f"  - {{name: {name}, url: '{url}/{name}'}}" for name in endpoints]
    lines += ["queries:", "  - {id: avg, query: 'SELECT (AVG(?x) AS ?avg) WHERE { ?s ?p ?x }'}"]
    path = tmp_path / "rashomon.yaml"
    path.write_text("\n".join(lines))
    return path


def test_agreeing_engines(tmp_path, server_url, capsys):
    config = write_config(tmp_path, server_url, ["a", "b"])
    assert main(["run", str(config)]) == EXIT_AGREE
    assert "agree" in capsys.readouterr().out


def test_disagreement_report(tmp_path, server_url, capsys):
    config = write_config(tmp_path, server_url, ["a", "b", "c", "broken", "slow"])
    assert main(["run", str(config)]) == EXIT_DIFFERENCES
    out = capsys.readouterr().out
    assert "datatypes differ" in out
    assert "A (baseline): a, b" in out
    assert "+ 2.5^^xsd:double" in out
    assert "B!" in out and "S1TAT" in out
    assert "HTTP 400: Parse error" in out
    assert "T/O" in out and "timeout on slow" in out


def test_json_and_markdown(tmp_path, server_url):
    config = write_config(tmp_path, server_url, ["a", "c"])
    report = tmp_path / "report.json"
    main(["run", str(config), "--format", "json", "-o", str(report)])
    doc = json.loads(report.read_text())
    assert doc["queries"][0]["verdict"] == "same-values"

    report = tmp_path / "report.md"
    main(["run", str(config), "--format", "markdown", "-o", str(report)])
    assert "| query | verdict | a | c |" in report.read_text()


def test_bad_config(tmp_path, capsys):
    path = tmp_path / "bad.yaml"
    path.write_text("endpoints: [{name: a, url: x}]\nqueries: [{id: q, query: 'ASK {}'}]")
    assert main(["run", str(path)]) == EXIT_USAGE
    assert "at least two endpoints" in capsys.readouterr().err
