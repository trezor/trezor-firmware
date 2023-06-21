from __future__ import annotations

import requests
from typing import Callable, Iterator
import click


BRANCHES_API_TEMPLATE = "https://gitlab.com/satoshilabs/trezor/trezor-firmware/-/pipelines.json?scope=branches&page={}"
GRAPHQL_API = "https://gitlab.com/api/graphql"


def get_gitlab_branches(page: int) -> list[dict]:
    return requests.get(BRANCHES_API_TEMPLATE.format(page)).json()["pipelines"]


def get_branch_obj(branch_name: str) -> dict:
    # Trying first 10 pages of branches
    for page in range(1, 11):
        if page > 1:
            print(f"Checking page {page} / 10")
        for branch_obj in get_gitlab_branches(page):
            if branch_obj["ref"]["name"] == branch_name:
                return branch_obj
    raise ValueError(f"Branch {branch_name} not found")


def get_last_pipeline_id(branch_name: str) -> int:
    branch_obj = get_branch_obj(branch_name)
    return branch_obj["id"]


def get_pipeline_jobs_info(pipeline_iid: int) -> dict:
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


def yield_pipeline_jobs(pipeline_iid: int) -> Iterator[dict]:
    jobs_info = get_pipeline_jobs_info(pipeline_iid)
    stages = jobs_info["data"]["project"]["pipeline"]["stages"]["nodes"]
    for stage in stages:
        nodes = stage["groups"]["nodes"]
        for node in nodes:
            jobs = node["jobs"]["nodes"]
            for job in jobs:
                yield job


def get_latest_links_for_branch(branch_name: str) -> dict[str, str]:
    branch_obj = get_branch_obj(branch_name)
    pipeline_iid = branch_obj["iid"]

    links: dict[str, str] = {}

    for job in yield_pipeline_jobs(pipeline_iid):
        for job_of_interest, func in get_jobs_of_interests():
            if job["name"] == job_of_interest:
                job_id = job["id"].split("/")[-1]
                links[job["name"]] = func(job_id)

    return links


@click.command()
@click.argument("branch", default="master")
def main(branch: str):
    print(f"Getting links for branch: {branch}")
    links = get_latest_links_for_branch(branch)
    for name, link in links.items():
        print(f"{name}: {link}")


if __name__ == "__main__":
    main()
