# Licenses for opt-in engines

Put license files here. Everything in this directory except this README and
`.gitignore` is ignored by git, so licenses are never committed.

| engine | file | how to get it |
|---|---|---|
| Stardog | `stardog-license-key.bin` | from Stardog (trial or free license); the server refuses to start without it |

Then, from `examples/`:

```bash
docker compose --profile licensed up -d
rashomon run rashomon-licensed.yaml
```
