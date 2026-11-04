# PitchMe backend

Python 3.11+, managed with [uv](https://docs.astral.sh/uv/).

```
backend/
  ai/          analysis layer (providers, pipelines, Q&A agent, voice cloning)
  server/      FastAPI app (config, logging, routes)
  scripts/     dev.sh and helper scripts
  tests/
```

## Setup

```bash
make dev    # install deps, create .env from .env.example
```

Fill in `.env`. At minimum set the passwords, `JWT_SECRET`, `AI_CALLBACK_KEY`
and `LIVEKIT_API_SECRET` (32+ characters).

## Run

```bash
make up         # Postgres, MinIO, Redis, LiveKit, Egress
make run        # API on :8000 with reload (API_PORT=8001 make run to change)
make practice   # everything above, with URLs set for a phone on your LAN
```

| Service | URL |
|---|---|
| API docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| MinIO console | http://localhost:9001 |
| LiveKit | ws://localhost:7880 |

## Database

Postgres with SQLAlchemy 2.0 models in `server/db/` and Alembic migrations in
`alembic/versions/`.

```bash
make migrate                      # apply migrations
make revision m="add some column" # autogenerate a migration from model changes
```

| Table | Holds |
|---|---|
| `users` | Login, profile, voice sample and playbook keys, voice clone id |
| `practice_sessions` | Deal details, call status, transcript, recording key, analysis job state and result |

## Storage

Media lives in an S3 bucket (MinIO locally) and never streams through the API.
The app uploads to presigned URLs; workers read from the bucket. Every object a
user owns sits under `users/<user_id>/` (see `server/storage/keys.py`).

## Checks

```bash
make test   # unit tests, no services needed
make lint   # ruff format + lint
make check  # what CI runs
make test-all  # starts services, then runs integration tests too
```

Integration tests create a throwaway database and bucket, and skip when
Postgres or MinIO is not running.

Optional dependencies are split by area (`api` for now) so a change to one
part does not pull in heavy libraries from another. `uv sync --all-extras`
installs all of them.
