#!/usr/bin/env python3
"""
Find the reference build a pull request's binaries should be compared with.

The PR job builds GitHub's merge ref, i.e. the current tip of the base branch
plus the PR, so the reference is the workflow run for the push of the base
commit (`github.event.pull_request.base.sha`) to main. If that run is still in
progress it is awaited. If it does not exist or did not succeed, the nearest
ancestor commit with a successful run is used instead and the distance is
reported, so the comment can say that the reference is a few commits behind.

Writes `run_id`, `sha`, `short_sha`, `behind` and `note` to $GITHUB_OUTPUT.
`run_id` is empty when no reference build could be found; that is not an error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from typing import Any

API = "https://api.github.com"


def api(path: str, token: str, **params: str | int) -> Any:
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def runs_of(
    repo: str, workflow: str, branch: str, sha: str, token: str
) -> list[dict[str, Any]]:
    """Runs of the workflow for pushes of the commit, newest first."""
    data = api(
        f"/repos/{repo}/actions/workflows/{workflow}/runs",
        token,
        head_sha=sha,
        branch=branch,
        event="push",
        per_page=10,
    )
    return data["workflow_runs"]


def write_outputs(**values: str) -> None:
    lines = [f"{key}={value}" for key, value in values.items()]
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a") as f:
            f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--sha", required=True, help="base commit of the pull request")
    parser.add_argument("--workflow", default="core.yml", help="workflow file name")
    parser.add_argument(
        "--branch", default="main", help="branch the reference builds run on"
    )
    parser.add_argument(
        "--max-behind", type=int, default=20, help="how many ancestors to try"
    )
    parser.add_argument(
        "--wait-minutes",
        type=int,
        default=20,
        help="how long to wait for an unfinished build",
    )
    parser.add_argument("--poll-seconds", type=int, default=30)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is not set", file=sys.stderr)
        return 1

    # ancestors of the base commit, the base itself first
    commits = api(
        f"/repos/{args.repo}/commits", token, sha=args.sha, per_page=args.max_behind
    )
    deadline = time.monotonic() + args.wait_minutes * 60

    for behind, commit in enumerate(commits):
        sha = commit["sha"]
        runs = runs_of(args.repo, args.workflow, args.branch, sha, token)
        if behind == 0:
            while runs and not any(r["status"] == "completed" for r in runs):
                if time.monotonic() >= deadline:
                    print(f"gave up waiting for the build of {sha[:10]}")
                    break
                print(
                    f"build of {sha[:10]} is {runs[0]['status']}, waiting {args.poll_seconds} s"
                )
                time.sleep(args.poll_seconds)
                runs = runs_of(args.repo, args.workflow, args.branch, sha, token)
        completed = [r for r in runs if r["status"] == "completed"]
        if not completed:
            continue
        run = completed[0]
        if behind > 0 and run["conclusion"] != "success":
            continue
        if run["conclusion"] != "success":
            # the exact base is worth more than a clean ancestor: whatever it built is usable
            print(
                f"build of {sha[:10]} concluded with {run['conclusion']}, using what it produced"
            )
        note = (
            ""
            if behind == 0
            else f"{behind} commit{'s' if behind > 1 else ''} behind the base of this PR"
        )
        print(
            f"reference build: run {run['id']} of {sha[:10]} ({note or 'the base commit'})"
        )
        write_outputs(
            run_id=str(run["id"]),
            sha=sha,
            short_sha=sha[:7],
            behind=str(behind),
            note=note,
        )
        return 0

    print(f"no reference build found within {len(commits)} commits of {args.sha[:10]}")
    write_outputs(run_id="", sha="", short_sha="", behind="", note="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
