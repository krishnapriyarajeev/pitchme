"""Which parts of the call recording are the seller.

The recording has both voices on one track, and speech and voice must
score the seller alone; the first version scored the AI buyer's voice
too. ai.diarize can split voices, but it needs torch and a voice model. A
rehearsal needs less: the buyer is our own agent, and the worker reports
every line it spoke. Those lines are found in the recording's transcript
by aligning words, and whatever is not the buyer is the seller.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from difflib import SequenceMatcher

from ai.core.transcript import Transcript
from ai.diarize.base import DiarizedSegment

SELLER = "seller"
BUYER = "buyer"

# A match shorter than this is a common word ("yes", "the"), not a line.
MIN_MATCH_TOKENS = 3
# A few misheard words inside a buyer line are still the buyer.
MAX_GAP_WORDS = 2


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def buyer_words(transcript: Transcript, buyer_lines: Sequence[str]) -> list[bool]:
    """For each word in the transcript, whether the buyer said it."""
    words = transcript.words
    owner: list[int] = []
    tokens: list[str] = []
    for i, word in enumerate(words):
        for token in _tokens(word.text):
            tokens.append(token)
            owner.append(i)
    said = [t for line in buyer_lines for t in _tokens(line)]

    hits = [0] * len(words)
    totals = [0] * len(words)
    for i in owner:
        totals[i] += 1
    matcher = SequenceMatcher(None, tokens, said, autojunk=False)
    for block in matcher.get_matching_blocks():
        if block.size >= MIN_MATCH_TOKENS:
            for k in range(block.a, block.a + block.size):
                hits[owner[k]] += 1
    mask = [totals[i] > 0 and hits[i] * 2 >= totals[i] for i in range(len(words))]
    return _fill_gaps(mask)


def _fill_gaps(mask: list[bool]) -> list[bool]:
    """Seller runs of at most MAX_GAP_WORDS between buyer words become buyer."""
    out = list(mask)
    i = 0
    while i < len(out):
        if out[i]:
            i += 1
            continue
        j = i
        while j < len(out) and not out[j]:
            j += 1
        if i > 0 and j < len(out) and j - i <= MAX_GAP_WORDS:
            out[i:j] = [True] * (j - i)
        i = j
    return out


def separate_speakers(
    transcript: Transcript, buyer_lines: Sequence[str]
) -> tuple[DiarizedSegment, ...]:
    """Seller and buyer stretches of the recording, in the form ai.diarize
    produces, so its filter_transcript and filter_audio cut the seller out."""
    words = transcript.words
    mask = buyer_words(transcript, buyer_lines)
    segments: list[DiarizedSegment] = []
    for word, is_buyer in zip(words, mask, strict=True):
        speaker = BUYER if is_buyer else SELLER
        if segments and segments[-1].speaker == speaker:
            last = segments[-1]
            segments[-1] = DiarizedSegment(speaker, last.start_ms, max(last.end_ms, word.end_ms))
        else:
            segments.append(DiarizedSegment(speaker, word.start_ms, word.end_ms))
    return tuple(segments)
