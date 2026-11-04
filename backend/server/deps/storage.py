from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from server.storage import Storage, get_storage

StorageDep = Annotated[Storage, Depends(get_storage)]
