"""Run the analysis job worker: `make worker`.

Takes jobs from the "analysis" queue in Redis (REDIS_URL, or REDIS_PORT on
localhost). Start more than one to analyse several calls at once.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rq import Worker

from server.config import get_settings
from server.jobs.queue import get_analysis_queue, get_redis
from server.logging_config import configure_logging

if __name__ == "__main__":
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_dir)
    Worker([get_analysis_queue()], connection=get_redis()).work()
