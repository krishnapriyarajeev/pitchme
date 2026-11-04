import httpx
import pytest

from server.storage import ObjectKey, StorageError

pytestmark = pytest.mark.integration


def test_put_stat_get(storage, tmp_path):
    key = ObjectKey("users/u1/profile/voice.wav")
    assert storage.stat(key) is None

    storage.put_bytes(key, b"RIFF....", "audio/wav")
    stat = storage.stat(key)
    assert stat is not None
    assert stat.size == 8
    assert stat.content_type == "audio/wav"
    assert storage.get_bytes(key) == b"RIFF...."

    dest = storage.get_file(key, tmp_path / "out" / "voice.wav")
    assert dest.read_bytes() == b"RIFF...."


def test_get_bytes_missing_raises(storage):
    with pytest.raises(StorageError, match="no object"):
        storage.get_bytes(ObjectKey("users/u1/missing.wav"))


def test_presigned_round_trip(storage):
    key = ObjectKey("users/u1/profile/playbook.pdf")
    upload = storage.presign_upload(key)
    assert httpx.put(upload, content=b"%PDF-1.7").status_code == 200

    download = storage.presign_download(key)
    assert httpx.get(download).content == b"%PDF-1.7"


def test_list_and_delete_prefix(storage):
    for name in ("a", "b", "c"):
        storage.put_bytes(ObjectKey(f"users/u1/sessions/s1/{name}"), b"x", "text/plain")
    storage.put_bytes(ObjectKey("users/u2/keep"), b"x", "text/plain")

    assert sorted(storage.list_prefix("users/u1/")) == [
        "users/u1/sessions/s1/a",
        "users/u1/sessions/s1/b",
        "users/u1/sessions/s1/c",
    ]
    assert storage.delete_prefix("users/u1/") == 3
    assert list(storage.list_prefix("users/")) == ["users/u2/keep"]
