from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterator

import requests

from common_all import AnyDict, JobInfo

HERE = Path(__file__).parent

BRANCHES_API_TEMPLATE = "https://gitlab.com/satoshilabs/trezor/trezor-firmware/-/pipelines.json?scope=branches&page={}"
GRAPHQL_API = "https://gitlab.com/api/graphql"

SCREEN_AMOUNT_CACHE_FILE = HERE / "gitlab_cache.json"
if not SCREEN_AMOUNT_CACHE_FILE.exists():
    SCREEN_AMOUNT_CACHE_FILE.write_text("{}")
BRANCH_CACHE: dict[str, int] = json.loads(SCREEN_AMOUNT_CACHE_FILE.read_text())


def update_branch_cache(link: str, amount: int) -> None:
    BRANCH_CACHE[link] = amount
    SCREEN_AMOUNT_CACHE_FILE.write_text(json.dumps(BRANCH_CACHE, indent=2))


@lru_cache(maxsize=32)
def get_gitlab_branches_cached(page: int) -> list[AnyDict]:
    return requests.get(BRANCHES_API_TEMPLATE.format(page)).json()["pipelines"]


def get_newest_gitlab_branches() -> list[AnyDict]:
    return requests.get(BRANCHES_API_TEMPLATE.format(1)).json()["pipelines"]


def get_branch_obj(branch_name: str) -> AnyDict:
    # Trying first 10 pages of branches
    for page in range(1, 11):
        if page == 1:
            # First page should be always updated,
            # rest can be cached
            branches = get_newest_gitlab_branches()
        else:
            branches = get_gitlab_branches_cached(page)
            print(f"Checking page {page} / 10")
        for branch_obj in branches:
            if branch_obj["ref"]["name"] == branch_name:
                return branch_obj
    raise ValueError(f"Branch {branch_name} not found")


def get_pipeline_jobs_info(pipeline_iid: int) -> AnyDict:
    query = {
        "query": "fragment CiNeeds on JobNeedUnion {\n  ...CiBuildNeedFields\n  ...CiJobNeedFields\n}\n\nfragment CiBuildNeedFields on CiBuildNeed {\n  id\n  name\n}\n\nfragment CiJobNeedFields on CiJob {\n  id\n  name\n}\n\nfragment LinkedPipelineData on Pipeline {\n  __typename\n  id\n  iid\n  path\n  cancelable\n  retryable\n  userPermissions {\n    updatePipeline\n  }\n  status: detailedStatus {\n    __typename\n    id\n    group\n    label\n    icon\n  }\n  sourceJob {\n    __typename\n    id\n    name\n    retried\n  }\n  project {\n    __typename\n    id\n    name\n    fullPath\n  }\n}\n\nquery getPipelineDetails($projectPath: ID!, $iid: ID!) {\n  project(fullPath: $projectPath) {\n    __typename\n    id\n    pipeline(iid: $iid) {\n      __typename\n      id\n      iid\n      complete\n      usesNeeds\n      userPermissions {\n        updatePipeline\n      }\n      downstream {\n        __typename\n        nodes {\n          ...LinkedPipelineData\n        }\n      }\n      upstream {\n        ...LinkedPipelineData\n      }\n      stages {\n        __typename\n        nodes {\n          __typename\n          id\n          name\n          status: detailedStatus {\n            __typename\n            id\n            action {\n              __typename\n              id\n              icon\n              path\n              title\n            }\n          }\n          groups {\n            __typename\n            nodes {\n              __typename\n              id\n              status: detailedStatus {\n                __typename\n                id\n                label\n                group\n                icon\n              }\n              name\n              size\n              jobs {\n                __typename\n                nodes {\n                  __typename\n                  id\n                  name\n                  kind\n                  scheduledAt\n                  needs {\n                    __typename\n                    nodes {\n                      __typename\n                      id\n                      name\n                    }\n                  }\n                  previousStageJobsOrNeeds {\n                    __typename\n                    nodes {\n                      ...CiNeeds\n                    }\n                  }\n                  status: detailedStatus {\n                    __typename\n                    id\n                    icon\n                    tooltip\n                    hasDetails\n                    detailsPath\n                    group\n                    label\n                    action {\n                      __typename\n                      id\n                      buttonTitle\n                      icon\n                      path\n                      title\n                    }\n                  }\n                }\n              }\n            }\n          }\n        }\n      }\n    }\n  }\n}\n",
        "variables": {
            "projectPath": "satoshilabs/trezor/trezor-firmware",
            "iid": pipeline_iid,
        },
    }
    return requests.post(GRAPHQL_API, json=query).json()


def get_differint_screens_link(job_id: str) -> str:
    return f"https://satoshilabs.gitlab.io/-/trezor/trezor-firmware/-/jobs/{job_id}/artifacts/test_ui_report/differing_screens.html"


def get_master_diff_link(job_id: str) -> str:
    return f"https://satoshilabs.gitlab.io/-/trezor/trezor-firmware/-/jobs/{job_id}/artifacts/master_diff/differing_screens.html"


def get_jobs_of_interests() -> list[tuple[str, Callable[[str], str]]]:
    return [
        ("core click R test", get_differint_screens_link),
        ("core device R test", get_differint_screens_link),
        ("core click test", get_differint_screens_link),
        ("core device test", get_differint_screens_link),
        ("unix ui changes", get_master_diff_link),
    ]


def yield_pipeline_jobs(pipeline_iid: int) -> Iterator[AnyDict]:
    jobs_info = get_pipeline_jobs_info(pipeline_iid)
    stages = jobs_info["data"]["project"]["pipeline"]["stages"]["nodes"]
    for stage in stages:
        nodes = stage["groups"]["nodes"]
        for node in nodes:
            jobs = node["jobs"]["nodes"]
            for job in jobs:
                yield job


def get_diff_screens_from_text(html_text: str) -> int:
    row_identifier = 'bgcolor="red"'
    return html_text.count(row_identifier)


def get_status_from_link(job: AnyDict, link: str) -> tuple[str, int]:
    if job["status"]["label"] == "skipped":
        return "Skipped", 0

    if link in BRANCH_CACHE:
        return "Finished", BRANCH_CACHE[link]

    res = requests.get(link)
    status = res.status_code
    if status == 200:
        diff_screens = get_diff_screens_from_text(res.text)
        update_branch_cache(link, diff_screens)
        return "Finished", diff_screens
    else:
        return "Running...", 0


def get_job_info(job: AnyDict, link: str, find_status: bool = True) -> JobInfo:
    if find_status:
        status, diff_screens = get_status_from_link(job, link)
    else:
        status, diff_screens = None, None

    return JobInfo(
        name=job["name"], link=link, status=status, diff_screens=diff_screens
    )


def get_latest_infos_for_branch(
    branch_name: str, find_status: bool
) -> dict[str, JobInfo]:
    branch_obj = get_branch_obj(branch_name)
    pipeline_iid = branch_obj["iid"]

    def yield_key_value() -> Iterator[tuple[str, JobInfo]]:
        for job in yield_pipeline_jobs(pipeline_iid):
            for job_of_interest, link_func in get_jobs_of_interests():
                if job["name"] == job_of_interest:
                    job_id = job["id"].split("/")[-1]
                    link = link_func(job_id)
                    yield job["name"], get_job_info(job, link, find_status)

    return dict(yield_key_value())
