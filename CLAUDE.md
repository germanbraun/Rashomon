# CLAUDE.md

## Project: rashomon

Differential testing for SPARQL engines: run the same queries on several
endpoints and report where the answers differ. See [README.md](README.md).

**Commands** (inside the `.venv`):
- `pip install -e ".[dev]"`: install
- `pytest`: run all tests (no engines needed; they use a fake HTTP endpoint)
- `cd examples && docker compose up -d && rashomon run rashomon.yaml`: compare real engines

**Pipeline:** `client → normalize → compare → report`, one module per step in `rashomon/`.
`runner.py` loops over queries and endpoints; `cli.py` wires it together.

**Rules:**
- Only `client.py` does network I/O. Everything after it works on plain Python data.
- `model.py`, `normalize.py` and the bag diff in `compare.py` started as copies of
  sparql-kata's modules. If you fix a bug in them, check whether sparql-kata has it too.
- The baseline (group A) is the most common answer, never call it "correct" in output.
- Timings are indicative only; keep the disclaimer next to them in every report format.
- Code must run on Python 3.10, the oldest version CI tests. Only runtime dependency: PyYAML.
- Keep `requirements.txt` in sync with the dependencies in `pyproject.toml`.
