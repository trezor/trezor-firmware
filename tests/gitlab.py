"""
Helper functions for communication with Gitlab.

Allowing for interaction with the test results, e.g. with UI tests.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

import requests

AnyDict = dict[Any, Any]

HERE = Path(__file__).parent

BRANCHES_API_TEMPLATE = "https://gitlab.com/satoshilabs/trezor/trezor-firmware/-/pipelines.json?scope=branches&page={}"
GRAPHQL_API = "https://gitlab.com/api/graphql"
RAW_REPORT_URL_TEMPLATE = (
    "https://gitlab.com/satoshilabs/trezor/trezor-firmware/-/jobs/{}/raw"
)

UI_JOB_NAMES = (
    "core click R test",
    "core device R test",
    "core click test",
    "core device test",
    "core persistence test",
    "legacy device test",
)

SAVE_GRAPHQL_RESULTS = False


@dataclass
class TestResult:
    failed: int = 0
    passed: int = 0
    error: int = 0

    @classmethod
    def from_line(cls, line: str) -> TestResult:
        self = TestResult()
        for key in self.__annotations__:
            match = re.search(rf"(\d+) {key}", line)
            if match:
                setattr(self, key, int(match.group(1)))
        return self

    @classmethod
    def from_job_id(cls, job_id: str) -> TestResult:
        report_link = RAW_REPORT_URL_TEMPLATE.format(job_id)
        raw_content = requests.get(report_link).text
        result_pattern = r"= .* passed.*s \(\d.*\) ="
        result_line_match = re.search(result_pattern, raw_content)
        if not result_line_match:
            print("No results yet.")
            return TestResult()
        return cls.from_line(result_line_match.group(0))


def _get_gitlab_branches(page: int) -> list[AnyDict]:
    return requests.get(BRANCHES_API_TEMPLATE.format(page)).json()["pipelines"]


def _get_branch_obj(branch_name: str) -> AnyDict:
    # Trying first 10 pages of branches
    for page in range(1, 11):
        branches = _get_gitlab_branches(page)
        for branch_obj in branches:
            if branch_obj["ref"]["name"] == branch_name:
                return branch_obj
    raise ValueError(f"Branch {branch_name} not found")


def _get_pipeline_jobs_info(pipeline_iid: int) -> AnyDict:
    # Getting just the stuff we need - the job names and IDs
    graphql_query = """
query getJobsFromPipeline($projectPath: ID!, $iid: ID!) {
  project(fullPath: $projectPath) {
    pipeline(iid: $iid) {
      stages {
        nodes {
          groups {
            nodes {
              jobs {
                nodes {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
  }
}
    """
    query = {
        "query": graphql_query,
        "variables": {
            "projectPath": "satoshilabs/trezor/trezor-firmware",
            "iid": pipeline_iid,
        },
    }
    return requests.post(GRAPHQL_API, json=query).json()


def _yield_pipeline_jobs(pipeline_iid: int) -> Iterator[AnyDict]:
    jobs_info = _get_pipeline_jobs_info(pipeline_iid)
    if SAVE_GRAPHQL_RESULTS:  # for development purposes
        with open("jobs_info.json", "w") as f:
            json.dump(jobs_info, f, indent=2)
    stages = jobs_info["data"]["project"]["pipeline"]["stages"]["nodes"]
    for stage in stages:
        nodes = stage["groups"]["nodes"]
        for node in nodes:
            jobs = node["jobs"]["nodes"]
            for job in jobs:
                yield job


def _get_job_ui_fixtures_results(job: AnyDict) -> AnyDict:
    print(f"Checking job {job['name']}")
    job_id = job["id"].split("/")[-1]

    job_results = TestResult.from_job_id(job_id)
    if job_results.failed:
        print(f"ERROR: Job {job['name']} failed - {job_results}")
        return {}

    url = f"https://satoshilabs.gitlab.io/-/trezor/trezor-firmware/-/jobs/{job_id}/artifacts/tests/ui_tests/fixtures.results.json"
    response = requests.get(url)
    if response.status_code != 200:
        print("No UI results found")
        return {}
    return response.json()


def get_jobs_of_interest(
    only_jobs: Iterable[str] | None, exclude_jobs: Iterable[str] | None
) -> Iterable[str]:
    if only_jobs and exclude_jobs:
        raise ValueError("Cannot specify both only_jobs and exclude_jobs")
    if only_jobs:
        return [job for job in UI_JOB_NAMES if job in only_jobs]
    if exclude_jobs:
        return [job for job in UI_JOB_NAMES if job not in exclude_jobs]
    return UI_JOB_NAMES


def get_branch_ui_fixtures_results(
    branch_name: str, jobs_of_interest: Iterable[str] | None = None
) -> dict[str, AnyDict]:
    print(f"Checking branch {branch_name}")

    if jobs_of_interest is None:
        jobs_of_interest = UI_JOB_NAMES

    branch_obj = _get_branch_obj(branch_name)
    pipeline_iid = branch_obj["iid"]

    def yield_key_value() -> Iterator[tuple[str, AnyDict]]:
        for job in _yield_pipeline_jobs(pipeline_iid):
            for ui_job_name in jobs_of_interest:
                if job["name"] == ui_job_name:
                    yield job["name"], _get_job_ui_fixtures_results(job)

    return dict(yield_key_value())
