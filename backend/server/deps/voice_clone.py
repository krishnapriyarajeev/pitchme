from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from server.db.session import get_sessionmaker
from server.deps.storage import StorageDep
from server.services.voice_clone import VoiceCloner


def get_voice_cloner(storage: StorageDep) -> VoiceCloner:
    """Tests override this to clone with a fake provider."""
    return VoiceCloner(get_sessionmaker(), storage)


VoiceClonerDep = Annotated[VoiceCloner, Depends(get_voice_cloner)]
