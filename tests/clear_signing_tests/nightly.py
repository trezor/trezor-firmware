#!/usr/bin/env python3

# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""The steps of the nightly clear-signing workflow around the tests themselves.

See docs/tests/clear-signing-tests.md.

- `resolve-inputs`: find the trezor/definitions and registry commits to test.
- `check-definitions`: check that a copy of the dev definitions is usable.
- `fetch-baseline`: get the UI fixtures to compare with, the screens of the last nightly run.
- `summarize`: write the results as Markdown (summary.md.mako), for $GITHUB_STEP_SUMMARY.
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import click
import requests
from mako.template import Template
from registry import definitions_source, load_cases, read_results

from trezorlib import definitions

ROOT = Path(__file__).resolve().parents[2]


@click.group()
def cli() -> None:
    pass


# --- resolve-inputs --------------------------------------------------------------

DEFINITIONS_REPO = "trezor/definitions"
DEPLOY_WORKFLOW = "deploy-dev-definitions.yaml"
REGISTRY_SUBMODULE = "ethereum/clear-signing-erc7730-registry"
REGISTRY_REPO = "ethereum/clear-signing-erc7730-registry"


def _github_get(path: str) -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(
        f"https://api.github.com/{path}", headers=headers, timeout=30
    )
    response.raise_for_status()
    return response.json()


def _last_deploy() -> dict:
    runs = _github_get(
        f"repos/{DEFINITIONS_REPO}/actions/workflows/{DEPLOY_WORKFLOW}/runs?per_page=1"
    )["workflow_runs"]
    if not runs:
        raise click.ClickException(f"{DEFINITIONS_REPO} has no {DEPLOY_WORKFLOW} runs")
    run = runs[0]
    url = run["html_url"]
    # A run that did not finish may have left the bucket half-synced (`aws s3 sync --delete`).
    if run["status"] != "completed":
        raise click.ClickException(
            f"The last unsigned dev deploy is still {run['status']}: {url}"
        )
    if run["conclusion"] != "success":
        raise click.ClickException(
            f"The last unsigned dev deploy ended with '{run['conclusion']}', so the dev "
            f"definitions may be incomplete: {url}\nRe-run the deploy."
        )
    return {
        "definitions_sha": run["head_sha"],
        "definitions_ref": run["head_branch"],
        "deploy_run_url": url,
        "deployed_at": run["updated_at"],
    }


@cli.command()
@click.option(
    "--definitions-sha",
    help="Use this trezor/definitions commit instead of the last unsigned dev deploy.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write the inputs as JSON to this file.",
)
def resolve_inputs(definitions_sha: str | None, output: Path | None) -> None:
    """Resolve the inputs of the nightly clear-signing tests.

    The tests run the ERC-7730 registry cases against the unsigned dev definitions. Both
    must come from the same trezor/definitions commit: the one that the last run of its
    "[Deploy] unsigned dev firmware definitions" workflow built (from any branch). The
    registry is the submodule that this commit pins.

    Writes the result as JSON, and as step outputs when $GITHUB_OUTPUT is set.
    """
    if definitions_sha:
        inputs = {
            "definitions_sha": definitions_sha,
            "definitions_ref": None,
            "deploy_run_url": None,
            "deployed_at": None,
        }
    else:
        inputs = _last_deploy()

    submodule = _github_get(
        f"repos/{DEFINITIONS_REPO}/contents/{REGISTRY_SUBMODULE}"
        f"?ref={inputs['definitions_sha']}"
    )
    if submodule.get("type") != "submodule":
        raise click.ClickException(
            f"{REGISTRY_SUBMODULE} is not a submodule at {inputs['definitions_sha']}"
        )
    inputs["registry_repo"] = REGISTRY_REPO
    inputs["registry_sha"] = submodule["sha"]

    text = json.dumps(inputs, indent=2)
    click.echo(text)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n")
    if github_output := os.environ.get("GITHUB_OUTPUT"):
        with open(github_output, "a") as f:
            for key in ("definitions_sha", "registry_sha"):
                f.write(f"{key}={inputs[key]}\n")


# --- check-definitions -----------------------------------------------------------

TIMESTAMPS_FILE = (
    ROOT / "common" / "defs" / "ethereum" / "released-definitions-timestamp.json"
)
FORMAT_VERSION = "2"


def _utc(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


@cli.command()
@click.argument(
    "definitions_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option("--chain-id", type=int, default=1, show_default=True)
def check_definitions(definitions_dir: Path, chain_id: int) -> None:
    """Check DEFINITIONS_DIR, a copy of `<deploy>/v2/definitions/`.

    The firmware rejects definitions older than its minimum data version, which comes
    from common/defs/ethereum/released-definitions-timestamp.json. Since the dev
    definitions are only deployed on demand, they go stale whenever that timestamp
    moves past them.
    """
    chain_dir = definitions_dir / "eth" / "chain-id" / str(chain_id)
    files = sorted(chain_dir.rglob("*.dat"))
    if not files:
        raise click.ClickException(
            f"No definitions in {chain_dir}. Did the download from S3 fail?"
        )
    if not (chain_dir / "network.dat").exists():
        raise click.ClickException(f"No network definition in {chain_dir}.")

    min_timestamp = int(
        datetime.fromisoformat(
            json.loads(TIMESTAMPS_FILE.read_text())[FORMAT_VERSION]
        ).timestamp()
    )
    kinds: Counter[str] = Counter()
    stale: list[Path] = []
    timestamps: list[int] = []
    for path in files:
        payload = definitions.Definition.parse(path.read_bytes()).payload
        if payload.version.decode() != FORMAT_VERSION:
            raise click.ClickException(
                f"{path}: format version {payload.version!r}, expected {FORMAT_VERSION}"
            )
        kinds[payload.data_type.name] += 1
        timestamps.append(payload.timestamp)
        if payload.timestamp < min_timestamp:
            stale.append(path)

    for kind, count in sorted(kinds.items()):
        click.echo(f"{kind}: {count}")
    click.echo(f"Timestamps: {_utc(min(timestamps))} .. {_utc(max(timestamps))}")
    click.echo(f"Firmware minimum: {_utc(min_timestamp)}")

    if stale:
        raise click.ClickException(
            f"{len(stale)} of {len(files)} dev definitions are older than the minimum "
            f"that the firmware accepts ({_utc(min_timestamp)}), e.g. {stale[0].name}. "
            "Re-run '[Deploy] unsigned dev firmware definitions' in trezor/definitions."
        )


# --- fetch-baseline --------------------------------------------------------------

FIRMWARE_REPO = "trezor/trezor-firmware"
WORKFLOW = "core-clear-signing.yml"
JOB = "core_clear_signing_test"
LANG = "en"
MODELS = ["T2T1", "T3B1", "T3T1", "T3W1"]
REPORT_URL = (
    "https://data.trezor.io/dev/firmware/ui_report/{run}/{model}-{lang}-{job}-{page}"
)
BASE_FIXTURES = Path(__file__).resolve().parent / "fixtures.json"


def _run_fixtures(run_id: int, model: str) -> dict | None:
    """The screens that a run recorded for `model`, from its UI report."""
    url = REPORT_URL.format(
        run=run_id, model=model, lang=LANG, job=JOB, page="fixtures.results.json"
    )
    response = requests.get(url, timeout=30)
    # S3 answers 403 for objects that do not exist.
    if response.status_code in (403, 404):
        return None
    response.raise_for_status()
    return response.json().get(model, {})


@cli.command()
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Write the fixtures to this file.",
)
@click.option(
    "--models",
    "models_json",
    default=json.dumps(MODELS),
    show_default=True,
    help="Models as a JSON list.",
)
@click.option("--branch", default="main", show_default=True)
@click.option(
    "--max-runs",
    type=int,
    default=10,
    show_default=True,
    help="How many earlier runs to look through.",
)
@click.option(
    "--sources",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write which run the fixtures of each model come from as JSON.",
)
def fetch_baseline(
    output: Path,
    models_json: str,
    branch: str,
    max_runs: int,
    sources: Path | None,
) -> None:
    """Get the UI fixtures to compare a run with: the screens of the last nightly run.

    For each model, these are the screens of the last finished scheduled run on BRANCH
    that has them (its `fixtures.results.json` in the UI report). So every nightly run
    shows what changed since the one before, and its own screens are the baseline of
    the next one. Models that no recent run has screens for keep the base fixtures,
    tests/clear_signing_tests/fixtures.json.
    """
    models: list[str] = json.loads(models_json)
    try:
        runs = _github_get(
            f"repos/{FIRMWARE_REPO}/actions/workflows/{WORKFLOW}/runs"
            f"?branch={branch}&event=schedule&status=completed&per_page={max_runs}"
        )["workflow_runs"]
    except requests.HTTPError as e:
        # The workflow is not on the default branch yet.
        if e.response is None or e.response.status_code != 404:
            raise
        runs = []

    fixtures = json.loads(BASE_FIXTURES.read_text())
    used: dict[str, dict | None] = {}
    for model in models:
        for run in runs:
            run_fixtures = _run_fixtures(run["id"], model)
            if run_fixtures is None:
                continue
            fixtures[model] = run_fixtures
            used[model] = {
                "run_id": run["id"],
                "run_number": run["run_number"],
                "run_url": run["html_url"],
                "created_at": run["created_at"],
            }
            count = len(run_fixtures.get("clear_signing_tests", {}))
            click.echo(f"{model}: {count} tests from run {run['html_url']}")
            break
        else:
            used[model] = None
            click.echo(
                f"{model}: no run in the last {len(runs)}, using {BASE_FIXTURES.name}"
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(fixtures, indent=0, sort_keys=True) + "\n")
    if sources:
        sources.parent.mkdir(parents=True, exist_ok=True)
        sources.write_text(json.dumps(used, indent=2) + "\n")


# --- summarize -------------------------------------------------------------------

SUMMARY_TEMPLATE = Path(__file__).resolve().parent / "summary.md.mako"
# Longer lists are cut, the step summary has a size limit.
MAX_LINES = 300


@dataclass
class _ModelRow:
    model: str
    counts: Counter[str]
    report_url: str
    differing_url: str
    # the run whose screens this one was compared with, None for the base fixtures
    baseline: dict | None


@cli.command()
@click.option(
    "--inputs",
    "inputs_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--registry",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--definitions", required=True, help="Copy or URL of the dev definitions."
)
@click.option(
    "--results",
    "results_dir",
    type=click.Path(file_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--baseline",
    "baseline_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="The `fetch-baseline --sources` file.",
)
@click.option("--run-id", required=True)
@click.option(
    "--models", "models_json", required=True, help="Tested models as a JSON list."
)
def summarize(
    inputs_file: Path,
    registry: Path,
    definitions: str,
    results_dir: Path,
    baseline_file: Path | None,
    run_id: str,
    models_json: str,
) -> None:
    """Summarize the test results as Markdown, for $GITHUB_STEP_SUMMARY."""
    inputs = json.loads(inputs_file.read_text())
    baseline = json.loads(baseline_file.read_text()) if baseline_file else {}
    models: list[str] = json.loads(models_json)
    cases = load_cases(registry, definitions_source(definitions))
    to_run = [case for case in cases if not case.skip_reason]
    results = read_results(results_dir) if results_dir.exists() else {}

    rows: list[_ModelRow] = []
    # test_id -> ["T3W1: error DataError: ...", ...]
    problems: dict[str, list[str]] = defaultdict(list)
    # test_id -> models
    blind: dict[str, list[str]] = defaultdict(list)
    # test_id -> (models, missing texts)
    not_found: dict[str, tuple[list[str], list[str]]] = {}
    for model in models:
        model_results = results.get(model, {})
        counts: Counter[str] = Counter()
        for case in to_run:
            result = model_results.get(case.test_id)
            status = result["status"] if result else "not run"
            counts[status] += 1
            if status == "clear_signed":
                if result and (missing := result.get("missing")):
                    counts["text not found"] += 1
                    entry = not_found.setdefault(case.test_id, ([], missing))
                    entry[0].append(model)
            elif status == "blind":
                blind[case.test_id].append(model)
            else:
                detail = (result or {}).get("message", "")
                problems[case.test_id].append(f"{model}: {status} {detail}".strip())
        report_url, differing_url = (
            REPORT_URL.format(run=run_id, model=model, lang=LANG, job=JOB, page=page)
            for page in ("index.html", "differing_screens.html")
        )
        rows.append(
            _ModelRow(model, counts, report_url, differing_url, baseline.get(model))
        )

    skipped = Counter(case.skip_reason for case in cases if case.skip_reason)
    summary = Template(filename=str(SUMMARY_TEMPLATE), strict_undefined=True).render(
        inputs=inputs,
        total=len(cases),
        run=len(to_run),
        rows=rows,
        skipped=skipped.most_common(),
        problems=sorted(problems.items()),
        blind=sorted(blind.items()),
        not_found=sorted(not_found.items()),
        max_lines=MAX_LINES,
    )
    click.echo(summary, nl=False)


if __name__ == "__main__":
    cli()
