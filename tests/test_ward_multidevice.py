"""Real same-seed devices, wardd/Evolu and HTTP WM.

WARD_STACK_INTEGRATION=1 pytest tests/test_ward_multidevice.py -v
"""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

import pytest

from tools.ward_stack import SCRIPT, find_suite, reserve_ports

pytestmark = pytest.mark.skipif(
    os.environ.get("WARD_STACK_INTEGRATION") != "1",
    reason="Set WARD_STACK_INTEGRATION=1 to launch three real emulators",
)

RECOVERY_CHECKS = {
    "recovery-reconstructs-last-complete-prefix-after-evolu-loss",
    "recovery-cached-confirmation-does-not-bypass-user-approval",
    "recovery-second-device-verifies-rollback-in-history",
    "recovery-rebuilds-trie-and-allows-new-writes",
}


def _run_stack(tmp_path: Path, model: str, scenario: str) -> set[str]:
    for _ in range(100):
        manager, daemon, debug = (35000 + secrets.randbelow(15000) for _ in range(3))
        emulator = 35000 + 8 * secrets.randbelow(1800)
        try:
            reserve_ports(manager, daemon, emulator, 3, debug, model == "T3W1")
        except OSError:
            continue
        break
    else:
        pytest.fail("No free ports for the multi-device stack")
    process = subprocess.Popen(
        [
            sys.executable,
            str(SCRIPT),
            "--suite",
            str(find_suite()),
            "--devices",
            "3",
            "--model",
            model,
            "--scenario",
            scenario,
            "--headless",
            "--once",
            "--full-log",
            "--manager-port",
            str(manager),
            "--wardd-port",
            str(daemon),
            "--debug-port",
            str(debug),
            "--emulator-port",
            str(emulator),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=360)
    except BaseException:
        # Let the launcher signal its own components and clean up its emulator/model processes.
        process.terminate()
        try:
            process.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)
        raise
    (tmp_path / "stack.log").write_text(stdout + stderr)
    assert process.returncode == 0, stdout[-20000:] + stderr
    match = re.search(r"Run directory: (.+)", stdout)
    assert match is not None
    run_dir = Path(match.group(1))
    assert not list(run_dir.glob("*.failed"))
    return set(json.loads((run_dir / "multi-device-results.json").read_text()))


@pytest.mark.parametrize("model", ["T3T1", "T3W1"])
def test_shared_seed_synchronization_offline_queue_collisions_and_rollback(
    tmp_path: Path, model: str
) -> None:
    assert _run_stack(tmp_path, model, "all") == RECOVERY_CHECKS | {
        "same-seed-wallet",
        "cross-device-synchronization",
        "one-device-offline-queues-without-advancing-anchor",
        "reconnect-integrates-queue-and-preserves-online-changes",
        "same-entry-collision-serializes-both-authorized-intents",
        "devices-reject-signed-rollback-and-replayed-attestation",
        "same-counter-root-substitution-rejected",
        "cross-confirmations-device-2-to-device-1",
        "cross-confirmations-device-1-to-device-2",
        "three-device-concurrent-publication",
    }


@pytest.mark.parametrize("model", ["T3T1", "T3W1"])
def test_recovery_from_missing_evolu_publication(tmp_path: Path, model: str) -> None:
    assert _run_stack(tmp_path, model, "recovery") == RECOVERY_CHECKS
