# PitchMe backend

Python 3.11+, managed with [uv](https://docs.astral.sh/uv/).

```
backend/
  ai/          analysis layer (core contracts, providers, pipelines, voice cloning)
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

## AI layer

`ai/` holds everything that analyses a call. It has no HTTP layer or
database and never imports `server/` (a test checks this), so a script, a
test or the LiveKit worker can call it directly.

| Module | What it holds |
|---|---|
| `ai/core` | `LLMClient`, `Transcript` (segments and words with timing), `Finding` and `Severity` |
| `ai/transcribe` | `TranscribeClient` interface |
| `ai/providers` | Groq and Gemini LLMs, Groq Whisper and local faster-whisper, and the factories |
| `ai/utils` | `extract_audio` (ffmpeg to 16 kHz mono WAV), `local_media` (path or storage key to a local file) |
| `ai/config.py` | Provider settings, read from the same `.env` |

Code asks for a client and never names a provider:

```python
from ai.providers import get_llm_client, get_transcribe_client

verdict = get_llm_client().complete_json(prompt, schema=schema)
transcript = get_transcribe_client().transcribe("call.wav")
```

| Setting | Values | Default |
|---|---|---|
| `LLM_PROVIDER` | `groq`, `gemini` | `groq` |
| `TRANSCRIBE_PROVIDER` | `groq`, `local` | `groq` |
| `GROQ_MODEL` / `GEMINI_MODEL` | model ids | `openai/gpt-oss-20b` / `gemini-3.8-flash` |
| `WHISPER_MODEL` | Groq Whisper model | `whisper-large-v3-turbo` |
| `WHISPER_MODEL_SIZE` / `WHISPER_DEVICE` | local model and device | `base` / `auto` |

Groq gives confidence per segment only, so its words have `logprob=None`.
Local faster-whisper gives a real per-word confidence. ffmpeg must be
installed for audio extraction.

## Checks

```bash
make test   # unit tests, no services needed
make lint   # ruff format + lint
make check  # what CI runs
make test-all  # starts services, then runs integration tests too
make test-live # real Groq and Gemini calls with the keys in .env (spends quota)
```

Integration tests create a throwaway database and bucket, and skip when
Postgres or MinIO is not running.

Optional dependencies are split by area (`api`, `llm`, `whisper-local`) so a
change to one part does not pull in heavy libraries from another. `uv sync --all-extras`
installs all of them.
