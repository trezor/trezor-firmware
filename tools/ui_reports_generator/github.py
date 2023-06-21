from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterator

import requests

from common_all import AnyDict, BranchInfo

HERE = Path(__file__).parent

GITHUB_PR_API = "https://api.github.com/repos/trezor/trezor-firmware/pulls"
GH_TOKEN = os.getenv("GH_TOKEN")
GH_HEADERS = {"Authorization": f"token {GH_TOKEN}"} if GH_TOKEN else {}


def load_cache_file() -> AnyDict:
    return json.loads(CACHE_FILE.read_text())


def load_branches_cache() -> dict[str, BranchInfo]:
    cache_dict = load_cache_file()["branches"]
    return {key: BranchInfo(**value) for key, value in cache_dict.items()}


def update_cache(cache_dict: dict[str, BranchInfo]) -> None:
    CACHE.update(cache_dict)
    json_writable_cache_dict = {key: asdict(value) for key, value in CACHE.items()}
    content = {
        "branches": json_writable_cache_dict,
        "metadata": {
            "last_update_timestamp": int(datetime.now().timestamp()),
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    }
    CACHE_FILE.write_text(json.dumps(content, indent=2))


CACHE_FILE = HERE / "github_cache.json"
if not CACHE_FILE.exists():
    CACHE_FILE.write_text("{}")
CACHE: dict[str, BranchInfo] = load_branches_cache()


def get_commit_ts(commit_hash: str) -> int:
    res = requests.get(
        f"https://api.github.com/repos/trezor/trezor-firmware/commits/{commit_hash}",
        headers=GH_HEADERS,
    )
    res.raise_for_status()
    return int(
        datetime.fromisoformat(
            res.json()["commit"]["committer"]["date"].replace("Z", "")
        ).timestamp()
    )


def get_all_gh_pulls() -> list[AnyDict]:
    res = requests.get(GITHUB_PR_API, headers=GH_HEADERS)
    res.raise_for_status()
    return res.json()


def yield_recently_updated_gh_pr_branches() -> Iterator[BranchInfo]:
    for pr in get_all_gh_pulls():
        last_commit_sha = pr["head"]["sha"]
        branch_name = pr["head"]["ref"]
        print(f"Getting branch {branch_name}")

        # Skip when we already have this commit in cache
        if branch_name in CACHE:
            cache_info = CACHE[branch_name]
            if cache_info.last_commit_sha == last_commit_sha:
                print(f"Skipping, commit did not change - {last_commit_sha}")
                continue

        # It can come from a fork - we do not have UI tests for it
        if branch_name == "master":
            print("Ignoring a fork")
            continue

        last_commit_timestamp = get_commit_ts(last_commit_sha)
        last_commit_datetime = datetime.fromtimestamp(last_commit_timestamp).isoformat()

        yield BranchInfo(
            name=branch_name,
            pull_request_number=pr["number"],
            pull_request_name=pr["title"],
            last_commit_sha=last_commit_sha,
            last_commit_timestamp=last_commit_timestamp,
            last_commit_datetime=last_commit_datetime,
            job_infos={},
        )
