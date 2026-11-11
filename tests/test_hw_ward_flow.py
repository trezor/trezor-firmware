"""Exercise the hardware workflow's real parameter and build-command generation."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/core-hw.yml"


@pytest.mark.parametrize(
    "models, expected",
    [
        (["T3T1", "T3W1"], ["T3T1", "T3W1"]),
        (["T1B1", "T2T1", "T3W1"], ["T3W1"]),
        (["T2T1"], []),
    ],
)
@pytest.mark.parametrize("ward_only", [False, True])
def test_hardware_pipeline_selects_only_supported_ward_models(
    tmp_path: Path, models: list[str], expected: list[str], ward_only: bool
) -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    script = workflow["jobs"]["param"]["steps"][0]["run"]
    output = tmp_path / "github-output"
    subprocess.run(
        ["bash", "-c", script],
        env={
            **os.environ,
            "MODELS": json.dumps(models),
            "WARD_ONLY": str(ward_only).lower(),
            "GITHUB_OUTPUT": str(output),
        },
        check=True,
        capture_output=True,
    )
    values = dict(line.split("=", 1) for line in output.read_text().splitlines())
    assert json.loads(values["ward_models"]) == expected
    assert json.loads(values["core_models"]) == (
        [] if ward_only else [model for model in models if model != "T1B1"]
    )
    assert values["run_legacy"] == ("1" if "T1B1" in models and not ward_only else "0")


@pytest.mark.parametrize("model", ["T3T1", "T3W1"])
def test_service_hardware_build_has_debuglink_without_vcp_endpoint_overflow(
    model: str,
) -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    profile = {
        key: str(value)
        for key, value in workflow["jobs"]["core_ward_channels"]["env"].items()
    }
    result = subprocess.run(
        ["make", "-n", "-C", "core", "build_firmware"],
        cwd=ROOT,
        env={**os.environ, **profile, "TREZOR_MODEL": model, "XTASK_BUILD_OPTS": ""},
        check=True,
        capture_output=True,
        text=True,
    )
    command = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith("xtask build firmware")
    )
    args = shlex.split(command)
    assert args[args.index("--model") + 1] == model
    assert "--enable-ward-service-channel" in args
    assert "--debug-link" in args
    assert args[args.index("--dbg-console") + 1] == "swo"
    assert "--btc-only" not in args
    # Wire + DebugLink + WebAuthn + WARD consume four endpoint pairs (limit five).
    assert args[args.index("--pyopt") + 1] == "false"


@pytest.mark.parametrize("bitcoin_only", [False, True])
def test_regular_hardware_build_enables_ward_only_for_universal(
    bitcoin_only: bool,
) -> None:
    result = subprocess.run(
        ["make", "-n", "-C", "core", "build_firmware"],
        cwd=ROOT,
        env={
            **os.environ,
            "TREZOR_MODEL": "T3W1",
            "PYOPT": "0",
            "WARD": "0" if bitcoin_only else "1",
            "WARD_SERVICE_CHANNEL": "0",
            "BITCOIN_ONLY": "1" if bitcoin_only else "0",
            "DBG_CONSOLE": "vcp",
            "XTASK_BUILD_OPTS": "",
        },
        check=True,
        capture_output=True,
        text=True,
    )
    command = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith("xtask build firmware")
    )
    args = shlex.split(command)
    assert ("--ward" in args) is not bitcoin_only
    assert ("--btc-only" in args) is bitcoin_only
    assert "--enable-ward-service-channel" not in args
