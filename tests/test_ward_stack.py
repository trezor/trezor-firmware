"""Launcher configuration, logging and the stop protocol, without opening windows.

Ported from the service-channel branch's launcher tests to this branch's components: an Evolu
relay as the database, the WARD Manager, wardd, the emulator and the WARD adapter.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pytest

from tools.ward_stack import (
    SCRIPT,
    combined_log,
    command,
    copy_log,
    reserve_ports,
    wm_down_requested,
)

ROLES = ("relay", "wm", "wardd", "emulator", "wardd2", "emulator2", "adapter")


@pytest.fixture
def launch_args(tmp_path: Path) -> tuple[list[str], dict[str, str]]:
    suite = tmp_path / "suite with spaces"
    relay = suite / "packages/wardd/src/relayCli.ts"
    relay.parent.mkdir(parents=True)
    relay.touch()
    (relay.parent / "cli.ts").touch()
    (relay.parent / "wmCli.ts").touch()
    for _ in range(100):
        relay_port = 30000 + secrets.randbelow(20000)
        wardd_port = 30000 + secrets.randbelow(20000)
        wm_port = 30000 + secrets.randbelow(20000)
        wardd2_port = 30000 + secrets.randbelow(20000)
        emulator = 30008 + 16 * secrets.randbelow(1500)
        try:
            reserve_ports(relay_port, wardd_port, emulator, wm_port, wardd2_port, emulator + 8)
        except (OSError, ValueError):
            continue
        break
    else:
        pytest.fail("No free ports for launcher test")
    env = {
        **os.environ,
        "WARD_RELAY_PORT": str(relay_port),
        "WARDD_PORT": str(wardd_port),
        "WARD_WM_PORT": str(wm_port),
        "WARDD2_PORT": str(wardd2_port),
        "TREZOR_UDP_PORT": str(emulator),
        "TREZOR_UDP_PORT2": str(emulator + 8),
    }
    return [
        sys.executable,
        str(SCRIPT),
        "--suite",
        str(suite),
        "--headless",
        "--dry-run",
    ], env


def _launch(args: list[str], env: dict[str, str]) -> tuple[Path, str]:
    result = subprocess.run(args, env=env, capture_output=True, text=True, check=True)
    match = re.search(r"Run directory: (.+)", result.stdout)
    assert match is not None
    return Path(match.group(1)), result.stdout


def test_propagates_ports_to_every_nix_shell(launch_args) -> None:
    args, env = launch_args
    root, stdout = _launch(args, env)
    try:
        exported = json.loads((root / "config.json").read_text())["environment"]
        assert exported["WARD_RELAY_URL"] == f"ws://127.0.0.1:{env['WARD_RELAY_PORT']}"
        assert exported["WARDD_URL"] == f"ws://127.0.0.1:{env['WARDD_PORT']}"
        assert exported["WARD_WM_URL"] == f"http://127.0.0.1:{env['WARD_WM_PORT']}"
        assert exported["WARD_STACK_RUN_DIR"] == str(root)
        assert exported["TREZOR_PATH"] == f"udp:127.0.0.1:{env['TREZOR_UDP_PORT']}"
        for role in ROLES:
            body = (root / f"{role}.sh").read_text()
            assert f"export WARDD_PORT={env['WARDD_PORT']}" in body
            assert f"export TREZOR_UDP_PORT={env['TREZOR_UDP_PORT']}" in body
        assert stdout.count("nix-shell ") == len(ROLES)
        assert not (root / "stop").exists()
    finally:
        shutil.rmtree(root)


def test_command_line_port_overrides_environment(launch_args) -> None:
    args, env = launch_args
    port = env["WARD_RELAY_PORT"]
    env["WARD_RELAY_PORT"] = "not-a-port"
    root, _ = _launch(args + ["--relay-port", port], env)
    try:
        exported = json.loads((root / "config.json").read_text())["environment"]
        assert exported["WARD_RELAY_PORT"] == port
    finally:
        shutil.rmtree(root)


def test_wardd_replicates_through_the_relay_and_logs_verbosely(launch_args) -> None:
    args, env = launch_args
    root, _ = _launch(args, env)
    try:
        config = json.loads((root / "config.json").read_text())
        wardd, _ = command(config, "wardd", root / "config.json")
        assert wardd[wardd.index("--relay") + 1] == f"ws://127.0.0.1:{env['WARD_RELAY_PORT']}"
        assert "--verbose" in wardd and "--memory" not in wardd
        assert wardd[wardd.index("--token-file") + 1] == str(root / "token")
        relay, _ = command(config, "relay", root / "config.json")
        assert relay[relay.index("--data-dir") + 1] == str(root / "relay")
        assert "--verbose" not in relay
        # the pairing token exists before anything starts, and only this user can read it
        assert (root / "token").stat().st_mode & 0o777 == 0o600
    finally:
        shutil.rmtree(root)


def test_wardd_asks_the_separate_wm_which_keeps_its_own_state(launch_args) -> None:
    args, env = launch_args
    root, stdout = _launch(args, env)
    try:
        config = json.loads((root / "config.json").read_text())
        wardd, _ = command(config, "wardd", root / "config.json")
        assert wardd[wardd.index("--wm") + 1] == f"http://127.0.0.1:{env['WARD_WM_PORT']}"
        wm, directory = command(config, "wm", root / "config.json")
        assert "src/wmCli.ts" in wm
        assert wm[wm.index("--port") + 1] == env["WARD_WM_PORT"]
        assert wm[wm.index("--data-dir") + 1] == str(root / "wm")
        assert directory.name == "wardd"
        assert f"wm={env['WARD_WM_PORT']}" in stdout
    finally:
        shutil.rmtree(root)


def test_the_second_device_has_its_own_wardd_and_emulator_and_waits_for_the_adapter(
    launch_args,
) -> None:
    args, env = launch_args
    root, _ = _launch(args, env)
    try:
        config = json.loads((root / "config.json").read_text())
        wardd2, _ = command(config, "wardd2", root / "config.json")
        assert wardd2[wardd2.index("--port") + 1] == env["WARDD2_PORT"]
        assert wardd2[wardd2.index("--data-dir") + 1] == str(root / "wardd2")
        assert wardd2[wardd2.index("--relay") + 1] == f"ws://127.0.0.1:{env['WARD_RELAY_PORT']}"
        # only the second device's wardd plays the hostile host
        assert "--adversarial-tests" in wardd2
        wardd, _ = command(config, "wardd", root / "config.json")
        assert "--adversarial-tests" not in wardd
        emulator2, _ = command(config, "emulator2", root / "config.json")
        assert emulator2[emulator2.index("-P") + 1] == env["TREZOR_UDP_PORT2"]
        assert emulator2[emulator2.index("-p") + 1] == str(root / "emulator2")
        assert emulator2[emulator2.index("--wait-role") + 1] == "emulator2"
        # the firmware's WARD lines are the point of the emulator terminals
        assert "-q" not in emulator2
        exported = config["environment"]
        assert exported["WARDD2_URL"] == f"ws://127.0.0.1:{env['WARDD2_PORT']}"
    finally:
        shutil.rmtree(root)


def test_emulator_log_keeps_only_ward_lines(tmp_path: Path) -> None:
    from tools.ward_stack import _EMULATOR_KEEP

    process = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-c",
            "print('1 trezor.loop DEBUG spawn'); print('2 apps.ward.flush_queue INFO flush: CONFLICT');"
            "print('Emulator ready after 0.5 seconds'); print('3 trezor.ui DEBUG paint')",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    copy_log(process, tmp_path / "emulator.log", "", None, "emulator", _EMULATOR_KEEP)
    process.wait(timeout=5)
    assert (tmp_path / "emulator.log").read_text().splitlines() == [
        "2 apps.ward.flush_queue INFO flush: CONFLICT",
        "Emulator ready after 0.5 seconds",
    ]


def test_wm_down_is_requested_by_a_file_in_the_run_directory(tmp_path: Path) -> None:
    # the adapter and the WM terminal drive the same switch; without a tty only the file counts
    assert not wm_down_requested(tmp_path)
    (tmp_path / "wm.down").touch()
    assert wm_down_requested(tmp_path)
    (tmp_path / "wm.down").unlink()
    assert not wm_down_requested(tmp_path)


def test_rejects_one_port_for_the_wm_and_wardd(launch_args) -> None:
    args, env = launch_args
    env["WARD_WM_PORT"] = env["WARDD_PORT"]
    result = subprocess.run(args, env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert "distinct" in result.stderr


def test_relay_debug_reaches_only_the_relay(launch_args) -> None:
    args, env = launch_args
    root, _ = _launch(args + ["--relay-debug"], env)
    try:
        config = json.loads((root / "config.json").read_text())
        relay, _ = command(config, "relay", root / "config.json")
        assert "--verbose" in relay
    finally:
        shutil.rmtree(root)


@pytest.mark.parametrize("flag", ["--full_log", "--full-log"])
def test_full_log_is_enabled_and_announced(launch_args, flag: str) -> None:
    args, env = launch_args
    root, stdout = _launch(args + [flag], env)
    try:
        assert json.loads((root / "config.json").read_text())["full_log"] is True
        assert (root / "full.log").is_file()
        assert "full.log" in stdout
    finally:
        shutil.rmtree(root)


def test_combined_log_preserves_concurrent_records(tmp_path: Path) -> None:
    path = tmp_path / "full.log"
    records = [
        (role, f"record {i} " + "x" * 10000) for role in ROLES for i in range(10)
    ]
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda record: combined_log(path, *record), records))
    actual = []
    timestamps = []
    for line in path.read_text().splitlines():
        timestamp, source, message = line.split(" ", 2)
        timestamps.append(datetime.fromisoformat(timestamp))
        actual.append((source.strip("[]"), message))
    assert sorted(actual) == sorted(records)
    assert timestamps == sorted(timestamps)


def test_copy_log_merges_stdout_stderr_and_final_partial_line(tmp_path: Path) -> None:
    process = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-c",
            "import sys; print('out'); print('err', file=sys.stderr); sys.stdout.write('last')",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        copy_log(process, tmp_path / "wardd.log", "", tmp_path / "full.log", "wardd")
        assert process.wait(timeout=5) == 0
        assert (tmp_path / "wardd.log").read_text() == "out\nerr\nlast"
        assert [
            line.split(" [wardd] ", 1)[1]
            for line in (tmp_path / "full.log").read_text().splitlines()
        ] == ["out", "err", "last"]
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_rejects_occupied_ports_before_launching(launch_args) -> None:
    args, env = launch_args
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", int(env["WARD_RELAY_PORT"])))
        result = subprocess.run(args, env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert "Cannot use the requested ports" in result.stderr
    assert "Run directory:" not in result.stdout


def test_rejects_the_default_device_port(launch_args) -> None:
    args, env = launch_args
    env["TREZOR_UDP_PORT"] = "21324"
    result = subprocess.run(args, env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert "30001" in result.stderr


def test_rejects_one_port_for_relay_and_wardd(launch_args) -> None:
    args, env = launch_args
    env["WARD_RELAY_PORT"] = env["WARDD_PORT"]
    result = subprocess.run(args, env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert "distinct" in result.stderr


def test_stop_releases_the_emulator_wait_command(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"run_dir": str(tmp_path)}))
    wait = subprocess.Popen([sys.executable, str(SCRIPT), "--wait", str(config)])
    try:
        deadline = time.monotonic() + 5
        while not (tmp_path / "emulator.ready").exists():
            assert time.monotonic() < deadline
            time.sleep(0.05)
        subprocess.run([sys.executable, str(SCRIPT), "--stop", str(tmp_path)], check=True)
        assert wait.wait(timeout=5) == 0
    finally:
        if wait.poll() is None:
            wait.terminate()
            wait.wait(timeout=5)


def test_display_is_visible_by_default_and_hidden_only_explicitly(launch_args) -> None:
    args, env = launch_args
    root, _ = _launch(args, env)
    try:
        config = json.loads((root / "config.json").read_text())
        emulator, _ = command(config, "emulator", root / "config.json")
        assert "-h" in emulator  # --headless was asked for
        config["gui"] = True
        emulator, _ = command(config, "emulator", root / "config.json")
        assert "-h" not in emulator
    finally:
        shutil.rmtree(root)
