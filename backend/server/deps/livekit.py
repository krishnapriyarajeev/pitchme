from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from server.config import Settings, get_settings
from server.services.livekit import LiveCalls, LiveKitCalls


def get_live_calls(settings: Annotated[Settings, Depends(get_settings)]) -> LiveCalls:
    """Tests override this with a fake LiveKit."""
    return LiveKitCalls(settings)


LiveCallsDep = Annotated[LiveCalls, Depends(get_live_calls)]
