# PitchMe

Have the meeting before the meeting.

PitchMe is a rehearsal room for sales calls. Set up a deal, then talk it
through on a live call with an AI buyer who acts like that prospect. After
the call you get a debrief: scores for content, speech, voice and body
language, answers checked against your own playbook, and stronger answers
played back in your own cloned voice.

## Repository layout

| Folder | What it is |
|---|---|
| `backend/` | Python backend: FastAPI API (`server/`) and the AI analysis layer (`ai/`) |
| `app/` | Phone app: Expo SDK 57, React Native and expo-router |

Each folder has its own README with setup steps.

## Status

The backend and the app are complete: sign-up and onboarding, the live call
with the AI buyer, the review job and the debrief. To run a real call you
need a development build of the app (see `app/README.md`) and the provider
keys in `backend/.env` (see `backend/.env.example`).
