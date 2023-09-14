#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
from typing import Iterable

import click

from gitlab import UI_JOB_NAMES, get_branch_ui_fixtures_results, get_jobs_of_interest
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
@click.option("-b", "--branch", help="Branch name")
@click.option(
    "-o",
    "--only-jobs",
    type=click.Choice(UI_JOB_NAMES),
    help="Job names which to process",
    multiple=True,
)
@click.option(
    "-e",
    "--exclude-jobs",
    type=click.Choice(UI_JOB_NAMES),
    help="Not take these jobs",
    multiple=True,
)
@click.option("-r", "--remove-missing", is_flag=True, help="Remove missing tests")
def ci(
    branch: str | None,
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

    jobs_of_interest = get_jobs_of_interest(only_jobs, exclude_jobs)
    ui_results = get_branch_ui_fixtures_results(branch, jobs_of_interest)

    current_fixtures = get_current_fixtures()

    is_error = False
    differing_total = 0
    for job_name, ui_res_dict in ui_results.items():
        print(f"Updating results from {job_name}...")
        if not ui_res_dict:
            is_error = True
            print("No results found.")
            continue
        model = next(iter(ui_res_dict.keys()))
        group = next(iter(ui_res_dict[model].keys()))
        current_model = current_fixtures.setdefault(model, {})
        current_group = current_model.setdefault(group, {})  # type: ignore

        if remove_missing:
            # get rid of tests that were not run in CI
            removed = 0
            for key in list(current_group.keys()):
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
