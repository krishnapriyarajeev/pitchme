from pathlib import Path

import pytest

from ai.utils.media import local_media, resolve_media


class FakeStore:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects
        self.calls: list[str] = []

    def get_file(self, key: str, dest: str | Path) -> Path:
        self.calls.append(key)
        Path(dest).write_bytes(self.objects[key])
        return Path(dest)


def test_local_file_is_used_as_is(tmp_path):
    clip = tmp_path / "clip.wav"
    clip.write_bytes(b"x")
    store = FakeStore({})
    assert resolve_media(str(clip), store, tmp_path / "dl") == clip.resolve()
    assert store.calls == []


def test_key_is_downloaded(tmp_path):
    key = "users/u1/sessions/s1/recording.mp4"
    store = FakeStore({key: b"video"})
    path = resolve_media(key, store, tmp_path / "dl")
    assert path == tmp_path / "dl" / "recording.mp4"
    assert path.read_bytes() == b"video"


def test_key_without_store(tmp_path):
    with pytest.raises(FileNotFoundError, match="no storage"):
        resolve_media("users/u1/profile/voice.wav", None, tmp_path)


def test_store_that_writes_nothing(tmp_path):
    class EmptyStore:
        def get_file(self, key, dest):
            return Path(dest)

    with pytest.raises(FileNotFoundError, match="no file"):
        resolve_media("users/u1/profile/voice.wav", EmptyStore(), tmp_path)


def test_local_media_cleans_up():
    key = "users/u1/profile/voice.m4a"
    with local_media(key, FakeStore({key: b"audio"})) as path:
        assert path.read_bytes() == b"audio"
        workdir = path.parent
    assert not workdir.exists()


@pytest.mark.integration
def test_server_storage_fits_the_protocol(storage):
    key = "users/u1/sessions/s1/recording.mp4"
    storage.put_bytes(key, b"from-minio", "video/mp4")
    with local_media(key, storage) as path:
        assert path.read_bytes() == b"from-minio"
