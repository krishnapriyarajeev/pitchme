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

## API

Interactive docs at `/docs`. Use **Authorize** with your email and password.

| Method | Path | Auth | What it does |
|---|---|---|---|
| POST | `/api/auth/register` | none | Create an account, returns a bearer token |
| POST | `/api/auth/login` | none | Sign in, returns a bearer token |
| GET | `/api/profile` | bearer | Profile with short-lived links to the voice sample and playbook |
| PUT | `/api/profile` | bearer | Change only the fields sent |
| POST | `/api/profile/upload-url` | bearer | Presigned PUT for `voice` or `playbook` |
| POST | `/api/profile/upload-confirm` | bearer | Check the upload and save it to the profile |

Uploads go straight to storage: ask for an upload URL, PUT the file to it, then
confirm. Confirm checks that the key belongs to you, that the file is there and
that it fits the size limit (voice 20 MB, playbook 25 MB).

Errors are JSON with a stable `code`, for example
`{"detail": "An account with this email already exists.", "code": "email_taken"}`.

Calls from our own workers (the LiveKit agent) send `X-Internal-Key` with the
value of `AI_CALLBACK_KEY`.

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
