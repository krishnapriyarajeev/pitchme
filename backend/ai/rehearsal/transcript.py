"""The call transcript, with when each turn was spoken.

Each turn has its start and end in milliseconds from the moment the
seller joined, which is close to where the recording starts, so the
analysis can line a turn up with the recording.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any, Literal

from ai.content.report import Line

CallRole = Literal["seller", "buyer"]

# LiveKit chat roles: the user is the seller, the agent is the buyer.
_ROLES: dict[str, CallRole] = {"user": "seller", "assistant": "buyer"}


@dataclass(frozen=True)
class CallTurn:
    role: CallRole
    text: str
    start_ms: int
    end_ms: int
    # The buyer was cut off, or the seller talked over the buyer.
    interrupted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _offset_ms(at: float, call_start: float) -> int:
    return max(0, round((at - call_start) * 1000))


def turn_from_message(
    *,
    role: str,
    text: str | None,
    created_at: float,
    metrics: Mapping[str, Any],
    interrupted: bool,
    call_start: float,
) -> CallTurn | None:
    """A chat message as a turn, or None for system text and empty messages.
    Times are Unix seconds; a message without speech timing (typed text)
    is placed at the moment it was added."""
    call_role = _ROLES.get(role)
    if call_role is None or not text or not text.strip():
        return None
    start = metrics.get("started_speaking_at") or created_at
    end = metrics.get("stopped_speaking_at") or max(start, created_at)
    return CallTurn(
        call_role,
        text.strip(),
        _offset_ms(start, call_start),
        _offset_ms(end, call_start),
        interrupted,
    )


class Transcript:
    """Collects turns as the call goes. A seller turn is added only once it
    is transcribed, which can be after the buyer starts to answer, so turns
    are put in order of when they were spoken."""

    def __init__(self, call_start: float) -> None:
        self.call_start = call_start
        self._turns: list[CallTurn] = []

    def add(self, message: Any) -> None:
        """Adds a livekit ChatMessage (or anything with the same fields)."""
        turn = turn_from_message(
            role=str(getattr(message, "role", "")),
            text=getattr(message, "text_content", None),
            created_at=getattr(message, "created_at", self.call_start),
            metrics=getattr(message, "metrics", None) or {},
            interrupted=bool(getattr(message, "interrupted", False)),
            call_start=self.call_start,
        )
        if turn is not None:
            self._turns.append(turn)

    @property
    def turns(self) -> tuple[CallTurn, ...]:
        return tuple(sorted(self._turns, key=lambda t: (t.start_ms, t.end_ms)))


def to_lines(turns: Iterable[CallTurn]) -> tuple[Line, ...]:
    """Turns as content-judge lines, where the seller is the "agent" and
    the buyer the "customer"."""
    return tuple(
        Line(
            role="agent" if t.role == "seller" else "customer",
            text=t.text,
            start_ms=t.start_ms,
            end_ms=t.end_ms,
        )
        for t in turns
    )
