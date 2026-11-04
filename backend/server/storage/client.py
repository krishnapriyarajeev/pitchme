"""S3-compatible object storage (MinIO locally).

Media never streams through the API. The app PUTs to a presigned URL and the
workers read from the same bucket, so a long upload never holds an API worker.
"""

from __future__ import annotations

import io
import mimetypes
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from minio import Minio
from minio.deleteobjects import DeleteObject
from minio.error import S3Error

from server.config import Settings, get_settings
from server.storage.keys import ObjectKey

# Long enough for a slow mobile upload, short enough that a leaked URL expires.
UPLOAD_TTL = timedelta(hours=1)
# Playback links are fetched on demand, so they can be short lived.
DOWNLOAD_TTL = timedelta(minutes=15)
# S3 caps one delete request at 1000 keys.
DELETE_BATCH = 1000

_MISSING = {"NoSuchKey", "NoSuchObject", "NotFound"}


class StorageError(RuntimeError):
    """An object storage call failed."""


@dataclass(frozen=True)
class ObjectStat:
    size: int
    content_type: str | None


def _host_and_tls(endpoint: str) -> tuple[str, bool]:
    """MinIO takes `host:port` plus a TLS flag, not a URL."""
    parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
    return parsed.netloc or parsed.path, parsed.scheme == "https"


class Storage:
    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self.bucket = settings.media_bucket
        self._access_key = settings.storage_access_key
        self._secret_key = settings.storage_secret_key
        self._region = settings.s3_region

        self._client = self._connect(settings.s3_endpoint)
        # Presigned URLs embed the host they were signed for, so links for the
        # phone are signed with the LAN-reachable endpoint, not localhost.
        public = settings.storage_public_endpoint
        self._public = self._client if public == settings.s3_endpoint else self._connect(public)

    def _connect(self, endpoint: str) -> Minio:
        host, secure = _host_and_tls(endpoint)
        return Minio(
            host,
            access_key=self._access_key,
            secret_key=self._secret_key,
            secure=secure,
            region=self._region,
        )

    # ---- presigned URLs for the app ----

    def presign_upload(self, key: ObjectKey, expires: timedelta = UPLOAD_TTL) -> str:
        """URL the app PUTs a file to. The content type is not signed, so check
        the stored object with `stat` before trusting it."""
        try:
            return self._public.presigned_put_object(self.bucket, key, expires=expires)
        except S3Error as exc:
            raise StorageError(f"presign upload failed for {key}: {exc}") from exc

    def presign_download(self, key: ObjectKey, expires: timedelta = DOWNLOAD_TTL) -> str:
        try:
            return self._public.presigned_get_object(self.bucket, key, expires=expires)
        except S3Error as exc:
            raise StorageError(f"presign download failed for {key}: {exc}") from exc

    # ---- server side reads and writes ----

    def put_file(
        self, key: ObjectKey, path: str | Path, content_type: str | None = None
    ) -> ObjectKey:
        path = Path(path)
        ctype = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        try:
            self._client.fput_object(self.bucket, key, str(path), content_type=ctype)
        except S3Error as exc:
            raise StorageError(f"upload failed for {key}: {exc}") from exc
        return key

    def put_bytes(self, key: ObjectKey, data: bytes, content_type: str) -> ObjectKey:
        try:
            self._client.put_object(
                self.bucket, key, io.BytesIO(data), length=len(data), content_type=content_type
            )
        except S3Error as exc:
            raise StorageError(f"upload failed for {key}: {exc}") from exc
        return key

    def get_file(self, key: ObjectKey, dest: str | Path) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._client.fget_object(self.bucket, key, str(dest))
        except S3Error as exc:
            raise StorageError(f"download failed for {key}: {exc}") from exc
        return dest

    def get_bytes(self, key: ObjectKey) -> bytes:
        """Small objects only (a voice sample, a playbook), not call recordings."""
        try:
            response = self._client.get_object(self.bucket, key)
        except S3Error as exc:
            reason = "no object" if exc.code in _MISSING else "download failed"
            raise StorageError(f"{reason} for {key}: {exc}") from exc
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def stat(self, key: ObjectKey) -> ObjectStat | None:
        """Metadata, or None if the object is not there (yet)."""
        try:
            info = self._client.stat_object(self.bucket, key)
        except S3Error as exc:
            if exc.code in _MISSING:
                return None
            raise StorageError(f"stat failed for {key}: {exc}") from exc
        return ObjectStat(size=info.size or 0, content_type=info.content_type)

    def exists(self, key: ObjectKey) -> bool:
        return self.stat(key) is not None

    def list_prefix(self, prefix: str) -> Iterator[str]:
        for obj in self._client.list_objects(self.bucket, prefix=prefix, recursive=True):
            if obj.object_name:
                yield obj.object_name

    def delete_prefix(self, prefix: str) -> int:
        """Delete every object under a prefix; returns how many were removed."""
        names = list(self.list_prefix(prefix))
        for start in range(0, len(names), DELETE_BATCH):
            batch = (DeleteObject(n) for n in names[start : start + DELETE_BATCH])
            # remove_objects is lazy: nothing is sent until the result is consumed.
            errors = list(self._client.remove_objects(self.bucket, batch))
            if errors:
                raise StorageError(f"delete failed for {errors[0].name}: {errors[0].message}")
        return len(names)

    def ensure_bucket(self) -> None:
        """Create the bucket when missing (compose's minio-init normally does this)."""
        try:
            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)
        except S3Error as exc:
            raise StorageError(f"could not create bucket {self.bucket}: {exc}") from exc


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    """One client per process; the MinIO client is thread safe and pools connections."""
    return Storage()
