from __future__ import annotations

import click

from github import update_cache, yield_recently_updated_gh_pr_branches
from gitlab import get_latest_infos_for_branch


@click.group()
def cli():
    pass


@cli.command(name="branch")
@click.argument("branch", default="master")
@click.option("--no-status", is_flag=True, default=False)
def get_branch(branch: str, no_status: bool):
    print(f"Getting links for branch: {branch}")
    tests_info = get_latest_infos_for_branch(branch, not no_status)

    for name, info in tests_info.items():
        print(
            f"{name}\n  - LINK: {info.link}\n  - STATUS: {info.status}\n  - DIFF SCREENS: {info.diff_screens}"
        )


def do_update_pulls():
    new_branch_infos = list(yield_recently_updated_gh_pr_branches())
    print(80 * "*")
    print(f"Found {len(new_branch_infos)} new branches")
    for branch in new_branch_infos:
        print(f"Getting links for branch: {branch}")
        try:
            tests_info = get_latest_infos_for_branch(branch.name, True)
            branch.job_infos = tests_info
        except Exception as e:
            print(f"Failed to get links for branch: {branch.name}")
            print(e)

    branch_dict = {branch.name: branch for branch in new_branch_infos}
    update_cache(branch_dict)


@cli.command(name="pulls")
def update_pulls():
    do_update_pulls()


if __name__ == "__main__":
    cli()
