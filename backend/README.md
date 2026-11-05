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
| POST | `/api/profile/upload-confirm` | bearer | Check the upload and save it to the profile; a voice sample also starts cloning the voice |
| POST | `/api/profile/voice-clone` | bearer | Clone the voice again from the current sample (202) |

Uploads go straight to storage: ask for an upload URL, PUT the file to it, then
confirm. Confirm checks that the key belongs to you, that the file is there and
that it fits the size limit (voice 20 MB, playbook 25 MB).

Cloning runs in the background after a voice sample is confirmed. The
profile's `voice_clone_status` goes from `pending` to `ready` (with
`voice_clone_id`) or `failed` (with a plain `voice_clone_error`). A new
sample replaces the old clone, which is deleted from the provider.

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
| `users` | Login, profile, voice sample and playbook keys, voice clone id and status |
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
| `ai/speech` | Fluency (pace, pauses, fillers) and articulation from the transcript |
| `ai/voice` | Pitch, intonation, loudness, nervousness and syllable rate from the waveform |
| `ai/vision` | Posture, eye contact, expression and gestures from video, and the annotated video |
| `ai/content` | Playbook extraction and the content judge (how each buyer question was answered) |
| `ai/diarize` | Who spoke when, which voice is the user, and cutting a recording to one speaker |
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

### Speech and voice

```python
from ai.speech import score_speech
from ai.voice import score_voice

speech = score_speech(transcript)  # one LLM call, for fillers
voice = score_voice("call.wav", mode="qa")  # a path or a storage key; no LLM
for finding in speech.findings + voice.findings:
    print(finding.severity, finding.summary)
```

Both return their raw measures plus a list of `Finding`s, most severe
first. Only patterns a listener would notice become findings.

| Pipeline | Measures | Findings |
|---|---|---|
| Speech | Words per minute in rolling 15 s windows, pauses (hesitation or deliberate), fillers, clarity | Pace too fast or slow, frequent fillers, hesitation runs, unclear articulation |
| Voice | Pitch and range, monotone share, loudness over speech frames, jitter, shimmer, HNR, syllables a second | Monotone, flat energy, volume drops, tension, nervousness spikes, pace, pitch outliers |

- **Fillers** have no fixed word list. The model decides what was a filler
  in this talk, and each count is capped at how often the word appears in
  the transcript.
- **Articulation** uses per-word confidence from local faster-whisper. With
  Groq, which scores segments only, a whole unsure segment is flagged.
- **Voice modes:** `presentation` (default) and `qa`. Q&A thresholds are
  looser, because answers are unrehearsed.
- The voice pipeline needs the `voice` extra (numpy and Praat through
  parselmouth) and ffmpeg for anything that is not a 16 kHz mono WAV.

### Vision

```bash
make models   # MediaPipe pose and face models into ai/models (not committed)
```

mediapipe also needs the system EGL and GLES libraries. They are usually
present on a desktop; on a Debian or Ubuntu server run
`apt-get install libegl1 libgles2`.

```python
from ai.vision import render_annotated_video, score_vision, voice_timeline

vision = score_vision("call.mp4", mode="qa")  # a path or a storage key
render_annotated_video(
    "call.mp4",
    vision.frames,
    "annotated.mp4",
    voice=voice_timeline(voice),  # optional voice panel
    movement_level=vision.movement.movement_level,
)
```

Frames are sampled 2 times a second. Each frame gives shoulder tilt,
slouch, eye contact, expression and wrist positions.

- **Posture:** shoulder tilt, and slouch from torso height. In a webcam
  shot the hips are out of view, so slouch then uses head height above
  the shoulders. Landmark x is scaled by the aspect ratio first, so
  level shoulders in a 16:9 video read as level.
- **Eye contact:** both irises centred and the head facing the camera.
- **Expression:** happy, surprised, tense or neutral, from MediaPipe face
  blendshapes.
- **Gestures:** speed of the more active hand, in shoulder widths a
  second. Gestures are not judged when the hands are in view less than
  30% of the time.
- **Annotated video:** skeleton, badges, eye contact light, voice panel
  and running scores, encoded as H.264 with the original sound.

### Content

```python
from ai.content import Line, extract_reference, score_content

playbook = extract_reference("playbook.pdf")  # .pdf .pptx .docx .txt .md .vtt .srt
report = score_content(lines, playbook)  # lines: Line(role, text, start_ms, end_ms, words)
```

One LLM call finds each buyer question or objection and judges the
answer: `dodged`, `inaccurate`, `unsupported`, `weak` or `handled`, with a
0-100 score and a coaching summary. Without a playbook it judges answers
on their own merits, and the accuracy categories are not used. Each quote
is found again in the conversation, to the exact words when the line has
word timings, so a finding points at the right moment. PowerPoint speaker
notes and tables are read too.

### Diarization

For one recording with two voices on it. Needs the `diarize` extra
(pyannote and torch, a large download) and `HF_TOKEN`, a Hugging Face
read token whose account accepted the licences of
`pyannote/speaker-diarization-3.1` and `pyannote/segmentation-3.0`. Voice
matching uses the WeSpeaker model from the same pipeline, which needs no
other licence.

```python
import os

from ai.diarize.align import tag_speakers
from ai.diarize.filter_speaker import filter_transcript
from ai.diarize.identify import identify_speaker
from ai.providers import get_diarize_client
from ai.providers.pyannote.embedding import PyannoteEmbedder

segments = get_diarize_client().diarize("call.wav")
embedder = PyannoteEmbedder(os.environ["HF_TOKEN"])
user = identify_speaker(embedder, "call.wav", segments, "voice_sample.wav")
tagged = tag_speakers(transcript, segments)
user_only = filter_transcript(tagged, user.speaker, segments)  # for speech
```

Cutting to one speaker closes up the gaps, so the buyer's turns do not
read as long hesitations by the user. `lines_from_turns(tagged.turns(),
user.speaker)` gives the content judge its lines.

### Voice cloning

The user's voice is cloned once, in the background, when they upload a
voice sample (see the API section). After a call, each answer the content
judge flagged is rewritten and spoken in that voice:

```python
from ai.voice_cloning import correct_answers, speak_answers

fixes = correct_answers(content_report.needs_work)
clips = speak_answers(fixes, user.voice_clone_id)  # one WAV per stronger answer
```

- A rewrite may only use facts from the answer, the question and the
  playbook. Every number in it, as digits or words, is checked against
  those; one with a new number is marked unverified and is not spoken.
- `correct_script` and `speak_script` lightly correct a solo talk with
  delivery cues (emotion, speed, pauses) and render it as one WAV. A
  rewrite that drifts from the original wording is spoken as said.
- `VOICE_CLONE_PROVIDER` is `cartesia` (default) or `resemble`. Cartesia
  applies emotion and speed only on `sonic-3` and later. Resemble also
  needs a transcript of the sample and a consent recording URL.

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

Optional dependencies are split by area (`api`, `llm`, `voice`, `vision`, `content`, `diarize`, `voice-clone`, `whisper-local`) so a
change to one part does not pull in heavy libraries from another. `uv sync --all-extras`
installs all of them.
