"""Real Cartesia speech and cloning. Runs with make test-live.

No real person's voice is cloned: a stock Cartesia voice reads a passage,
that synthetic recording is cloned, the clone speaks one line, and the
clone is deleted again.
"""

import pytest

from ai.config import AISettings
from ai.providers import make_voice_clone_client
from ai.voice_cloning.base import ProsodyParams, VoiceSample
from ai.voice_cloning.wav import join_wav, read_wav

pytestmark = pytest.mark.live
pytest.importorskip("cartesia", reason="needs the voice-clone extra")

PASSAGE = (
    "Thanks for taking the time today. Our team plan is forty dollars per seat each month, "
    "and most customers see churn fall within the first quarter. We integrate with the tools "
    "your reps already use, so there is very little to set up. I would love to walk you "
    "through a short demo and answer any questions about security or pricing."
)


@pytest.fixture(scope="module")
def cartesia():
    settings = AISettings(voice_clone_provider="cartesia")
    if not settings.cartesia_api_key.get_secret_value():
        pytest.skip("CARTESIA_API_KEY is not set")
    return make_voice_clone_client(settings)


def test_stock_voice_speaks_clone_and_delete(cartesia, tmp_path):
    stock = next(iter(cartesia._client.voices.list())).id
    clip = cartesia.synthesize(PASSAGE, stock, ProsodyParams("confident"))
    pcm = read_wav(clip)
    assert (pcm.rate, pcm.channels) == (16_000, 1)
    assert pcm.duration_ms > 8_000

    sample = tmp_path / "synthetic.wav"
    sample.write_bytes(clip)
    voice_id = cartesia.clone_voice(VoiceSample(sample), "pitchme-live-test")
    try:
        line = cartesia.synthesize("Yes, we are audited every year.", voice_id, ProsodyParams())
        both = join_wav([line, line], [300])
        assert read_wav(both).duration_ms > 2 * read_wav(line).duration_ms
    finally:
        cartesia.delete_voice(voice_id)
