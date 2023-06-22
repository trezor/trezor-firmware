from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

AnyDict = dict[Any, Any]


@dataclass
class BranchInfo:
    name: str
    branch_link: str
    pull_request_number: int
    pull_request_name: str
    pull_request_link: str
    last_commit_sha: str
    last_commit_timestamp: int
    last_commit_datetime: str
    job_infos: dict[str, JobInfo]

    @classmethod
    def from_dict(cls, data: AnyDict) -> BranchInfo:
        self = BranchInfo(**data)
        # Need to transform job_info dict to JobInfo objects,
        # as that was not done automatically by dataclass
        self.job_infos = {
            job_name: JobInfo.from_dict(job_info_dict)  # type: ignore
            for job_name, job_info_dict in self.job_infos.items()
        }
        return self

    def to_dict(self) -> AnyDict:
        return asdict(self)


@dataclass
class JobInfo:
    name: str
    link: str
    status: str | None = None
    diff_screens: int | None = None

    @classmethod
    def from_dict(cls, data: AnyDict) -> JobInfo:
        return JobInfo(**data)

    def to_dict(self) -> AnyDict:
        return asdict(self)


def get_logger(name: str, log_file_path: str | Path) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    log_handler = logging.FileHandler(log_file_path)
    log_formatter = logging.Formatter("%(asctime)s %(message)s")
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)
    return logger
