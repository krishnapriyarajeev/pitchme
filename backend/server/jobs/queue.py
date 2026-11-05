from __future__ import annotations

from functools import lru_cache

from redis import Redis
from rq import Queue

from server.config import get_settings

ANALYSIS_QUEUE = "analysis"


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_dsn)


def get_analysis_queue() -> Queue:
    """Tests override this with a queue on fakeredis that runs jobs at once."""
    return Queue(ANALYSIS_QUEUE, connection=get_redis())
