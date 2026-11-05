"""Start the LiveKit agent worker that plays the AI buyer.

    uv run --extra rehearsal python scripts/run_agent.py start     # serve rehearsal rooms
    uv run --extra rehearsal python scripts/run_agent.py dev       # same, with reload
    uv run --extra rehearsal python scripts/run_agent.py console   # talk to the buyer locally

Settings come from .env: LIVEKIT_*, DEEPGRAM_API_KEY, GROQ_API_KEY,
AI_CALLBACK_KEY and SERVER_PUBLIC_BASE_URL.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from livekit.agents import cli

from ai.rehearsal.worker import build_server

if __name__ == "__main__":
    cli.run_app(build_server())
