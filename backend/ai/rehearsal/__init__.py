"""The live rehearsal call: an AI buyer the user pitches to over LiveKit.

`deal` and `prompts` are plain Python, so the API can build a room's
metadata without the agent SDK. `agent`, `worker` and `report` need the
rehearsal extra and are imported only by the worker.
"""

from .deal import AUDIENCES, COMPOSURES, STAGES, CallSetup, Deal, InvalidSetup

__all__ = ["AUDIENCES", "COMPOSURES", "STAGES", "CallSetup", "Deal", "InvalidSetup"]
