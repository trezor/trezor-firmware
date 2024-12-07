"""
Helper functions for communication with GitHub.

Allowing for interaction with the test results, e.g. with UI tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Iterator

import requests

from trezorlib import models

AnyDict = dict[Any, Any]

HERE = Path(__file__).parent

LIST_RUNS_TEMPLATE = "https://api.github.com/repos/trezor/trezor-firmware/actions/workflows/{workflow}/runs?branch={branch}"
FIXTURES_TEMPLATE = "https://data.trezor.io/dev/firmware/ui_report/{run}/{model}-{lang}-{job}/fixtures.results.json"

MODELS = [model.internal_name for model in models.TREZORS]
CORE_LANGUAGES = ["en", "cs", "de", "es", "fr", "it", "pt", "tr"]
CORE_JOBS = ["core_device_test", "core_click_test", "core_persistence_test"]
LEGACY_LANGUAGES = ["en"]
LEGACY_JOBS = ["legacy_device_test"]


def get_last_run(branch_name: str, workflow: str) -> int | None:
    response = requests.get(
        LIST_RUNS_TEMPLATE.format(branch=branch_name, workflow=workflow)
    )
    response.raise_for_status()
    try:
        return response.json()["workflow_runs"][0]["id"]
    except IndexError:
        print(f"No workflow runs found for {workflow}")
        return None


def get_branch_ui_fixtures_results(
    branch_name: str,
    only_jobs: Iterable[str] | None,
    exclude_jobs: Iterable[str] | None,
    run_id: int | None,
) -> dict[str, AnyDict]:
    print(f"Checking branch {branch_name}")

    core_run_id = run_id or get_last_run(branch_name, "core.yml")
    legacy_run_id = run_id or get_last_run(branch_name, "legacy.yml")

    def yield_key_value() -> Iterator[tuple[str, AnyDict]]:
        for model in MODELS:
            if model == "T1B1":
                run_id = legacy_run_id
                jobs = LEGACY_JOBS
                languages = LEGACY_LANGUAGES
            else:
                run_id = core_run_id
                jobs = CORE_JOBS
                languages = CORE_LANGUAGES

            if run_id is None:
                continue

            for lang in languages:
                for job in jobs:
                    job_instance = f"{model}-{lang}-{job}"

                    if only_jobs and all(
                        (job not in job_instance) for job in only_jobs
                    ):
                        continue
                    if exclude_jobs and any(
                        (job in job_instance) for job in exclude_jobs
                    ):
                        continue

                    response = requests.get(
                        FIXTURES_TEMPLATE.format(
                            run=run_id, model=model, lang=lang, job=job
                        )
                    )
                    if response.status_code != 200:
                        print(
                            f"Failed to get fixtures for {job_instance}: {response.status_code}"
                        )
                        continue
                    yield job_instance, response.json()

    return dict(yield_key_value())
