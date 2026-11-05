"""Resemble AI voice cloning and speech.

Resemble's first clone is free, which makes it a cheap way to test. Its
clone flow has more steps than Cartesia's:

1. create a voice record, which needs a consent URL (a recording of the
   speaker reading Resemble's consent statement);
2. upload the sample with its transcript;
3. start training and wait for it to finish;
4. speak through a project, created once and reused.

There are no emotion or speed settings, so prosody is not applied; pauses
still are, when clips are joined. The SDK keeps its API key in class state,
so one process works with one Resemble key.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ai.voice_cloning.base import ProsodyParams, VoiceCloneClient, VoiceCloneError, VoiceSample

PROJECT_NAME = "pitchme-playback"
BUILD_POLL_S = 5.0
BUILD_TIMEOUT_S = 600.0
SAMPLE_RATE = 16_000


def _ok(result: dict, action: str) -> dict:
    if not result.get("success", False):
        raise VoiceCloneError(f"Resemble {action} failed: {result.get('message', result)}")
    return result


class ResembleVoiceClient(VoiceCloneClient):
    def __init__(
        self,
        api_key: str | None = None,
        *,
        sdk: Any = None,
        fetch: Any = None,
        sleep: Any = time.sleep,
    ) -> None:
        if sdk is None:
            if not api_key:
                raise VoiceCloneError(
                    "RESEMBLE_API_KEY is not set (https://app.resemble.ai/account/api)."
                )
            from resemble import Resemble

            Resemble.api_key(api_key)
            sdk = Resemble
        self._v2 = sdk.v2
        self._fetch = fetch or _download
        self._sleep = sleep
        self._project: str | None = None

    def _project_uuid(self) -> str:
        if self._project is None:
            listing = self._v2.projects.all(1, 100)
            found = [p for p in listing.get("items", []) if p.get("name") == PROJECT_NAME]
            if found:
                self._project = found[0]["uuid"]
            else:
                created = _ok(
                    self._v2.projects.create(PROJECT_NAME, "PitchMe answer playback"),
                    "project creation",
                )
                self._project = created["item"]["uuid"]
        return self._project

    def _wait_until_built(self, voice_uuid: str) -> None:
        deadline = time.monotonic() + BUILD_TIMEOUT_S
        while time.monotonic() < deadline:
            status = self._v2.voices.get(voice_uuid).get("item", {}).get("status")
            if status == "finished":
                return
            if status not in ("initializing", "running", "queued"):
                raise VoiceCloneError(f"Resemble voice training stopped with status {status!r}")
            self._sleep(BUILD_POLL_S)
        raise VoiceCloneError(f"Resemble voice training took longer than {BUILD_TIMEOUT_S:.0f} s")

    def clone_voice(self, sample: VoiceSample, name: str) -> str:
        if not sample.consent_url or not sample.transcript:
            raise VoiceCloneError(
                "Resemble needs the sample's transcript and a consent recording URL to clone"
            )
        voice = _ok(
            self._v2.voices.create(name=name, consent=sample.consent_url, voice_type="rapid"),
            "voice creation",
        )["item"]["uuid"]
        path = Path(sample.audio_path)
        try:
            with path.open("rb") as audio:
                _ok(
                    self._v2.recordings.create(
                        voice, audio, path.stem, sample.transcript, True, "neutral"
                    ),
                    "sample upload",
                )
        except OSError as exc:
            raise VoiceCloneError(f"Could not read voice sample {path}: {exc}") from exc
        _ok(self._v2.voices.build(voice), "training request")
        self._wait_until_built(voice)
        return voice

    def synthesize(self, text: str, voice_id: str, prosody: ProsodyParams) -> bytes:
        result = _ok(
            self._v2.clips.create_sync(
                self._project_uuid(),
                voice_id,
                text,
                sample_rate=SAMPLE_RATE,
                output_format="wav",
            ),
            "speech",
        )
        return self._fetch(result["item"]["audio_src"])

    def delete_voice(self, voice_id: str) -> None:
        _ok(self._v2.voices.delete(voice_id), "voice deletion")


def _download(url: str) -> bytes:  # pragma: no cover - network
    import requests

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.content
