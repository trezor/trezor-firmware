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
LANGUAGES = ["en", "cs", "de", "es", "fr", "it", "pt", "tr"]
JOBS = ["core_device_test", "core_click_test", "core_persistence_test"]


def get_branch_ui_fixtures_results(
    branch_name: str,
    only_jobs: Iterable[str] | None,
    exclude_jobs: Iterable[str] | None,
    run_id: int | None,
) -> dict[str, AnyDict]:
    print(f"Checking branch {branch_name}")

    response = requests.get(
        LIST_RUNS_TEMPLATE.format(branch=branch_name, workflow="core.yml")
    )
    response.raise_for_status()
    run_id = run_id or response.json()["workflow_runs"][0]["id"]

    def yield_key_value() -> Iterator[tuple[str, AnyDict]]:
        for model in MODELS:
            for lang in LANGUAGES:
                for job in JOBS:
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
