from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

AnyDict = dict[Any, Any]


@dataclass
class BranchInfo:
    name: str
    pull_request_number: int
    pull_request_name: str
    last_commit_sha: str
    last_commit_timestamp: int
    last_commit_datetime: str
    job_infos: dict[str, JobInfo]


@dataclass
class JobInfo:
    name: str
    link: str
    status: str | None = None
    diff_screens: int | None = None


def get_logger(name: str, log_file_path: str | Path) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    log_handler = logging.FileHandler(log_file_path)
    log_formatter = logging.Formatter("%(asctime)s %(message)s")
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)
    return logger
