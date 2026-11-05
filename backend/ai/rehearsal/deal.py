"""The deal a rehearsal is about, and how it reaches the agent worker.

The API packs a `CallSetup` into the LiveKit room metadata when it creates
the room. The worker reads it back when it joins. Both sides use this
module, so the format cannot drift between them.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, fields

STAGES = (
    "cold_call",
    "discovery",
    "demo",
    "proposal",
    "negotiation",
    "closing",
    "renewal",
)
AUDIENCES = (
    "general",
    "ceo",
    "cto",
    "vp_sales",
    "procurement",
    "product_manager",
    "investor",
)
COMPOSURES = ("warm", "direct", "analytical", "guarded")

_ALIASES = {"close": "closing", "cold": "cold_call", "negotiate": "negotiation"}


def normalize(value: str, allowed: tuple[str, ...], field: str) -> str:
    """'Cold call', 'cold-call' and 'COLD_CALL' all become 'cold_call'.
    A label with a note after it, like 'Direct - low patience', is read by
    its first word."""
    text = value.strip().lower()
    key = re.sub(r"[\s\-/]+", "_", text)
    first = re.split(r"[^a-z]", text, maxsplit=1)[0]
    for candidate in (key, _ALIASES.get(key), first, _ALIASES.get(first)):
        if candidate in allowed:
            return candidate
    raise ValueError(f"unknown {field} {value!r}; expected one of {', '.join(allowed)}")


@dataclass(frozen=True)
class Deal:
    """Who the user pitches to, and what they sell."""

    prospect_name: str
    company: str
    deal_stage: str = "discovery"
    industry: str | None = None
    buyer_composure: str | None = None
    competitors: str | None = None
    audience_type: str = "general"
    # From the user's profile: what they sell and their job title.
    product: str | None = None
    seller_role: str | None = None

    def __post_init__(self) -> None:
        set_ = object.__setattr__
        set_(self, "deal_stage", normalize(self.deal_stage, STAGES, "deal stage"))
        set_(
            self, "audience_type", normalize(self.audience_type or "general", AUDIENCES, "audience")
        )
        if self.buyer_composure:
            set_(self, "buyer_composure", normalize(self.buyer_composure, COMPOSURES, "composure"))


class InvalidSetup(ValueError):
    """Room metadata that is not a PitchMe rehearsal."""


@dataclass(frozen=True)
class CallSetup:
    """Everything the worker needs, carried in the room metadata."""

    session_id: str
    # The LiveKit identity the user joins with; the buyer talks only to them.
    seller_identity: str
    deal: Deal

    KIND = "pitchme.rehearsal"
    VERSION = 1

    def to_metadata(self) -> str:
        return json.dumps(
            {
                "kind": self.KIND,
                "version": self.VERSION,
                "session_id": self.session_id,
                "seller_identity": self.seller_identity,
                "deal": asdict(self.deal),
            }
        )

    @classmethod
    def from_metadata(cls, raw: str) -> CallSetup:
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise InvalidSetup("room metadata is not JSON") from exc
        if not isinstance(data, dict) or data.get("kind") != cls.KIND:
            raise InvalidSetup("room is not a PitchMe rehearsal")
        if data.get("version") != cls.VERSION:
            raise InvalidSetup(f"unsupported rehearsal metadata version {data.get('version')!r}")
        known = {f.name for f in fields(Deal)}
        try:
            deal = Deal(**{k: v for k, v in data["deal"].items() if k in known})
            return cls(str(data["session_id"]), str(data["seller_identity"]), deal)
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            raise InvalidSetup(f"rehearsal metadata is incomplete: {exc}") from exc
