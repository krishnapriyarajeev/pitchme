# PitchMe backend

Python 3.11+, managed with [uv](https://docs.astral.sh/uv/).

```
backend/
  ai/       analysis layer (providers, pipelines, Q&A agent, voice cloning)
  server/   FastAPI app
  tests/
```

## Setup

```bash
make dev   # install deps, create .env from .env.example
make up    # Postgres + MinIO in Docker
make test  # unit tests
```

Run `make` to see every target.
