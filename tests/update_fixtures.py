#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
from typing import Iterable

import click

from ui_tests import update_fixtures
from ui_tests.common import FIXTURES_FILE, get_current_fixtures


@click.group()
def cli():
    pass


@cli.command()
@click.option("-r", "--remove-missing", is_flag=True, help="Remove missing tests")
def local(remove_missing: bool) -> None:
    """Update fixtures file with results from latest local test run."""
    print("Updating from local test run...")
    changes_amount = update_fixtures(remove_missing)
    print(f"Updated fixtures.json with data from {changes_amount} tests.")


def _get_current_git_branch() -> str:
    return (
        subprocess.check_output(["git", "branch", "--show-current"])
        .decode("ascii")
        .strip()
    )


@cli.command()
@click.option(
    "-g",
    "--github",
    is_flag=True,
    help="Fetch from GitHub Actions (default)",
    hidden=True,
    expose_value=False,
)
@click.option("-b", "--branch", help="Branch name")
@click.option("-r", "--run-id", help="GitHub Actions run id", type=int)
@click.option(
    "-o",
    "--only-jobs",
    help="Job names which to process",
    multiple=True,
)
@click.option(
    "-e",
    "--exclude-jobs",
    help="Not take these jobs",
    multiple=True,
)
@click.option("-r", "--remove-missing", is_flag=True, help="Remove missing tests")
def ci(
    branch: str | None,
    run_id: int | None,
    only_jobs: Iterable[str] | None,
    exclude_jobs: Iterable[str] | None,
    remove_missing: bool,
) -> None:
    """Update fixtures file with results from CI."""
    print("Updating from CI...")

    if only_jobs and exclude_jobs:
        raise click.UsageError("Cannot use both --only-jobs and --exclude-jobs")

    if branch is None:
        branch = _get_current_git_branch()

    print(f"Branch: {branch}")
    if only_jobs:
        print(f"Only jobs: {only_jobs}")
    if exclude_jobs:
        print(f"Exclude jobs: {exclude_jobs}")

    from github import get_branch_ui_fixtures_results

    ui_results = get_branch_ui_fixtures_results(branch, only_jobs, exclude_jobs, run_id)
    current_fixtures = get_current_fixtures()

    is_error = False
    differing_total = 0
    for job_name, ui_res_dict in ui_results.items():
        print(f"Updating results from {job_name}...")
        if not ui_res_dict:
            is_error = True
            print("No results found.")
            continue
        _model, lang, _job = job_name.split("-")
        model = next(iter(ui_res_dict.keys()))
        assert model == _model
        group = next(iter(ui_res_dict[model].keys()))
        current_model = current_fixtures.setdefault(model, {})
        current_group = current_model.setdefault(group, {})  # type: ignore

        if remove_missing:
            # get rid of tests that were not run in CI
            removed = 0
            for key in list(current_group.keys()):
                if not key.startswith(f"{model}_{lang}_"):
                    continue
                if key not in ui_res_dict[model][group]:
                    current_group.pop(key)
                    removed += 1
            print(f"Removed {removed} tests.")

        differing = 0
        for test_name, res in ui_res_dict[model][group].items():
            if current_group.get(test_name) != res:
                differing += 1
            current_group[test_name] = res

        print(f"Updated {differing} tests.")
        differing_total += differing

    print(80 * "-")
    print(f"Updated {differing_total} tests in total.")

    FIXTURES_FILE.write_text(
        json.dumps(current_fixtures, indent=0, sort_keys=True) + "\n"
    )
    print("Updated fixtures.json with data from CI.")
    if is_error:
        print(80 * "-")
        raise click.ClickException("Some jobs did not have any results.")


if __name__ == "__main__":
    cli()
