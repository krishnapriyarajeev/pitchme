"""Turn a media reference into a local file.

Pipelines take either a local path or an object-storage key. The caller
passes in something that can download a key (the server's `Storage` fits),
so this module never imports `server`.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol


class MediaStore(Protocol):
    def get_file(self, key: str, dest: str | Path) -> Path: ...


def resolve_media(ref: str | Path, store: MediaStore | None, dest_dir: str | Path) -> Path:
    """A local path for `ref`, downloading it into `dest_dir` if it is a key.

    An existing local file always wins, so tests and scripts can pass plain
    paths. Anything else is treated as a storage key.
    """
    path = Path(ref)
    if path.is_file():
        return path.resolve()
    if store is None:
        raise FileNotFoundError(f"{ref} is not a local file and no storage was given")
    target = Path(dest_dir) / Path(str(ref)).name
    target.parent.mkdir(parents=True, exist_ok=True)
    store.get_file(str(ref), target)
    if not target.is_file():
        raise FileNotFoundError(f"Storage returned no file for {ref}")
    return target


@contextmanager
def local_media(ref: str | Path, store: MediaStore | None = None) -> Iterator[Path]:
    """`resolve_media` into a temporary folder that is removed afterwards."""
    workdir = Path(tempfile.mkdtemp(prefix="pitchme-media-"))
    try:
        yield resolve_media(ref, store, workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
