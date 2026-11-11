"""The adversarial launcher must propagate failures and reject skipped evidence."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools import ward_adversarial


@pytest.mark.parametrize("outcome", ["pass", "failure", "skip", "timeout"])
def test_orchestrator_reports_every_group_and_fails_closed(
    tmp_path, monkeypatch, outcome
):
    suite = tmp_path / "suite"
    package = suite / "packages/wardd"
    package.mkdir(parents=True)
    (package / "package.json").write_text("{}")
    report = tmp_path / "reports"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ward_adversarial.py",
            "--path",
            "udp:127.0.0.1:39000",
            "--suite",
            str(suite),
            "--report-dir",
            str(report),
        ],
    )
    monkeypatch.setenv("WARDD_DEBUG_PORT", "21331")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs["env"]["TREZOR_PATH"] == "udp:127.0.0.1:39000"
        assert kwargs["timeout"] > 0
        assert "WARDD_DEBUG_PORT" not in kwargs["env"]
        if "pytest" in command:
            from pathlib import Path

            skipped = int(outcome == "skip")
            Path(command[command.index("--junitxml") + 1]).write_text(
                f'<testsuites><testsuite tests="2" failures="0" errors="0" skipped="{skipped}"/></testsuites>'
            )
        elif "--outputFile" in command:
            target = command[command.index("--outputFile") + 1]
            if target.endswith("host.json") and outcome == "timeout":
                raise subprocess.TimeoutExpired(command, 900)
            if target.endswith("history.json") and outcome == "failure":
                return subprocess.CompletedProcess(command, 1)
            from pathlib import Path

            Path(target).write_text(
                json.dumps(
                    {
                        "success": True,
                        "numPassedTests": 3,
                        "numPendingTests": 0,
                        "numTodoTests": 0,
                    }
                )
            )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", run)
    assert ward_adversarial.main() == (0 if outcome == "pass" else 1)
    assert len(calls) == 5
    summary = json.loads((report / "summary.json").read_text())
    assert summary["passed"] is (outcome == "pass")
    assert [group["group"] for group in summary["groups"]] == [
        "manager-crypto-firmware",
        "offline-cache",
        "host-persistence",
        "history-reconstruction",
        "adapter-protocol",
    ]


def test_empty_jest_report_does_not_count_as_a_pass(tmp_path):
    (tmp_path / "host.json").write_text(
        json.dumps({"success": True, "numPassedTests": 0})
    )
    assert not ward_adversarial.report_success("host-persistence", tmp_path)


@pytest.mark.parametrize("hardware", [False, True])
def test_usb_path_requires_the_hardware_opt_in(tmp_path, monkeypatch, hardware):
    suite = tmp_path / "suite"
    (suite / "packages/wardd").mkdir(parents=True)
    (suite / "packages/wardd/package.json").write_text("{}")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ward_adversarial.py",
            "--path",
            "webusb",
            "--suite",
            str(suite),
            "--report-dir",
            str(tmp_path / "reports"),
            *(["--hardware"] if hardware else []),
        ],
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 1),
    )
    if hardware:
        # Accepted: every group runs (and fails here, as no reports are written).
        assert ward_adversarial.main() == 1
    else:
        with pytest.raises(SystemExit):
            ward_adversarial.main()


def test_yarn_command_can_be_overridden(tmp_path):
    yarn = ["node", "/suite/.yarn/releases/yarn.cjs"]
    commands = [
        command
        for _, _, command in ward_adversarial.plan(tmp_path, tmp_path, yarn)
        if "test:unit" in command
    ]
    assert len(commands) == 2
    assert all(command[:2] == yarn for command in commands)


def test_relative_report_dir_reaches_children_as_absolute(tmp_path, monkeypatch):
    # Jest runs in the Suite package directories, so a relative report path breaks there.
    suite = tmp_path / "suite"
    (suite / "packages/wardd").mkdir(parents=True)
    (suite / "packages/wardd/package.json").write_text("{}")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ward_adversarial.py",
            "--path",
            "udp:127.0.0.1:39000",
            "--suite",
            str(suite),
            "--report-dir",
            "reports",
        ],
    )
    outputs = []

    def run(command, **kwargs):
        for flag in ("--junitxml", "--outputFile"):
            if flag in command:
                outputs.append(command[command.index(flag) + 1])
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(subprocess, "run", run)
    ward_adversarial.main()
    assert len(outputs) == 4
    assert all(Path(output).is_absolute() for output in outputs)
    assert (tmp_path / "reports/summary.json").is_file()
