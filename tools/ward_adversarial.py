#!/usr/bin/env python3
"""Run WARD attack/rejection tests on a caller-provided disposable device.

The device is a disposable emulator, or with --hardware a dedicated CI device: the
tests wipe it.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

FIRMWARE = Path(__file__).resolve().parent.parent


def plan(
    suite: Path, report: Path, yarn: list[str] | None = None
) -> list[tuple[str, Path, list[str]]]:
    yarn = yarn or ["yarn"]
    return [
        (
            "manager-crypto-firmware",
            FIRMWARE,
            [
                sys.executable,
                "-m",
                "pytest",
                "-v",
                "--tb=short",
                "-ra",
                "--junitxml",
                str(report / "python.xml"),
                "tests/test_ward_manager.py",
                "python/tests/test_ward_crypto.py",
                "tests/device_tests/misc/test_ward_adversarial.py",
                "tests/device_tests/misc/test_ward_mpt.py",
            ],
        ),
        (
            # The offline cache: sticky entries need the user's approval, are used only
            # while no proof can be had, follow every verified answer, and a replayed
            # backup brings nothing back -- on the device and through a real wardd.
            # Needs an emulator built with the offline store (xtask --ward); a skip
            # fails the group.
            "offline-cache",
            FIRMWARE,
            [
                sys.executable,
                "-m",
                "pytest",
                "-v",
                "--tb=short",
                "-ra",
                "--junitxml",
                str(report / "cache.xml"),
                "tests/device_tests/misc/test_ward_sticky.py",
                "tests/device_tests/misc/test_ward_cache.py",
                "tests/device_tests/misc/test_ward_relay.py::test_ward_relay_cache_entry",
                "tests/device_tests/misc/test_ward_relay.py"
                "::test_ward_relay_cache_follows_ward_on_another_device",
            ],
        ),
        (
            "host-persistence",
            suite / "packages/wardd",
            [
                *yarn,
                "test:unit",
                "--runInBand",
                "--detectOpenHandles",
                "--json",
                "--outputFile",
                str(report / "host.json"),
                "--runTestsByPath",
                "src/host.security.test.ts",
                "src/wm.test.ts",
                "src/reconstruction.test.ts",
                "src/__tests__/host.test.ts",
                "src/__tests__/server.test.ts",
            ],
        ),
        (
            "history-reconstruction",
            suite / "packages/ward",
            [
                *yarn,
                "test:unit",
                "--runInBand",
                "--coverage=false",
                "--json",
                "--outputFile",
                str(report / "history.json"),
                "--runTestsByPath",
                "src/app/index.test.ts",
                "src/mocks/__tests__/ward.test.ts",
            ],
        ),
        (
            "adapter-protocol",
            FIRMWARE,
            [
                "cargo",
                "test",
                "--locked",
                "--manifest-path",
                "rust/ward-relay/Cargo.toml",
                "--test",
                "protocol",
            ],
        ),
    ]


def report_success(name: str, report: Path) -> bool:
    """Skipped tests and missing reports do not demonstrate resilience."""
    junit = {"manager-crypto-firmware": "python.xml", "offline-cache": "cache.xml"}
    if name in junit:
        counts = list(ET.parse(report / junit[name]).getroot().iter("testsuite"))
        return (
            bool(counts)
            and sum(int(item.get("tests", "0")) for item in counts) > 0
            and all(
                int(item.get(field, "0")) == 0
                for item in counts
                for field in ("failures", "errors", "skipped")
            )
        )
    filename = {
        "host-persistence": "host.json",
        "history-reconstruction": "history.json",
    }.get(name)
    if filename:
        data = json.loads((report / filename).read_text())
        return (
            data.get("success") is True
            and data.get("numPassedTests", 0) > 0
            and data.get("numPendingTests", 0) == 0
            and data.get("numTodoTests", 0) == 0
        )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default=os.environ.get("TREZOR_PATH"))
    parser.add_argument("--suite", type=Path, default=os.environ.get("WARDD_SUITE_DIR"))
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument(
        "--hardware",
        action="store_true",
        help="Accept a USB --path: a dedicated CI device that the tests may wipe",
    )
    args = parser.parse_args()
    if not args.path or not (args.path.startswith("udp:") or args.hardware):
        parser.error(
            "--path must identify a disposable UDP emulator, or a dedicated device "
            "with --hardware; tests wipe it"
        )
    if args.suite is None or not (args.suite / "packages/wardd/package.json").is_file():
        parser.error("--suite must select a prepared Suite checkout")
    report = args.report_dir or (
        Path(os.environ["WARD_DATA_DIR"]).parent / "adversarial"
        if os.environ.get("WARD_DATA_DIR")
        else Path(tempfile.mkdtemp(prefix="ward-adversarial-"))
    )
    # Children run in other directories (Jest in the Suite packages): pass absolute paths.
    report = report.resolve()
    report.mkdir(parents=True, exist_ok=True)
    scratch = report / "tmp"
    scratch.mkdir(exist_ok=True)
    environment = {
        **os.environ,
        "TREZOR_PATH": args.path,
        "WARDD_SUITE_DIR": str(args.suite),
        "TMPDIR": str(scratch.resolve()),
    }

    # Child tests start private wardd instances, not the stack's debug listener.
    environment.pop("WARDD_DEBUG_PORT", None)

    def log(event: str, **fields: object) -> None:
        print(
            json.dumps(
                {
                    "time": datetime.now(timezone.utc).isoformat(
                        timespec="milliseconds"
                    ),
                    "service": "WARD adversarial",
                    "event": event,
                    **fields,
                }
            ),
            flush=True,
        )

    log("adversarial.start", reportDir=str(report), path=args.path)
    results = []
    # A runner without a yarn binary can name the pinned release: WARD_YARN="node .../yarn.cjs".
    yarn = shlex.split(os.environ.get("WARD_YARN", "yarn"))
    for name, cwd, command in plan(args.suite, report, yarn):
        log("adversarial.group.start", group=name)
        try:
            completed = subprocess.run(
                command, cwd=cwd, env=environment, timeout=900, check=False
            )
            passed = completed.returncode == 0 and report_success(name, report)
        except (OSError, ValueError, ET.ParseError, subprocess.TimeoutExpired) as error:
            log("adversarial.group.error", group=name, error=str(error))
            passed = False
        results.append({"group": name, "passed": passed})
        log("adversarial.group.complete", **results[-1])
    success = all(item["passed"] for item in results)
    summary = {"passed": success, "groups": results, "reportDir": str(report)}
    (report / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    log("adversarial.complete", **summary)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
