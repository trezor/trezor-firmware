"""Launcher configuration and readiness/stop protocol without opening windows."""

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

from tools.ward_stack import SCRIPT, combined_log, copy_log, reserve_ports


@pytest.fixture
def launch_args(tmp_path: Path) -> tuple[list[str], dict[str, str]]:
    suite = tmp_path / "suite with spaces"
    cli = suite / "packages/wardd/src/cli.ts"
    cli.parent.mkdir(parents=True)
    cli.touch()
    for _ in range(100):
        manager = 30000 + secrets.randbelow(20000)
        daemon = 30000 + secrets.randbelow(20000)
        emulator = 30008 + 8 * secrets.randbelow(3000)
        try:
            reserve_ports(manager, daemon, emulator)
        except OSError:
            continue
        break
    else:
        pytest.fail("No free ports for launcher test")
    env = {
        **os.environ,
        "WARD_MANAGER_PORT": str(manager),
        "WARDD_PORT": str(daemon),
        "TREZOR_UDP_PORT": str(emulator),
    }
    return [
        sys.executable,
        str(SCRIPT),
        "--suite",
        str(suite),
        "--headless",
        "--dry-run",
    ], env


def test_propagates_environment_ports_to_every_nix_shell(launch_args) -> None:
    args, env = launch_args
    result = subprocess.run(args, env=env, capture_output=True, text=True, check=True)
    match = re.search(r"Run directory: (.+)", result.stdout)
    assert match is not None
    root = Path(match.group(1))
    try:
        config = json.loads((root / "config.json").read_text())
        exported = config["environment"]
        assert exported["WARD_MANAGER_PORT"] == env["WARD_MANAGER_PORT"]
        assert exported["WARDD_PORT"] == env["WARDD_PORT"]
        assert exported["TREZOR_UDP_PORT"] == env["TREZOR_UDP_PORT"]
        assert (
            exported["WARD_MANAGER_URL"]
            == f"http://127.0.0.1:{env['WARD_MANAGER_PORT']}"
        )
        assert exported["WARDD_URL"] == f"ws://127.0.0.1:{env['WARDD_PORT']}"
        assert exported["TREZOR_PATH"] == f"udp:127.0.0.1:{env['TREZOR_UDP_PORT']}"
        for name in ("manager", "wardd", "emulator", "hwi"):
            body = (root / f"{name}.sh").read_text()
            assert f"export WARD_MANAGER_PORT={env['WARD_MANAGER_PORT']}" in body
            assert f"export TREZOR_UDP_PORT={env['TREZOR_UDP_PORT']}" in body
        assert result.stdout.count("nix-shell ") == 4
        assert not (root / "stop").exists()
    finally:
        shutil.rmtree(root)


def test_command_line_port_overrides_environment(launch_args) -> None:
    args, env = launch_args
    old_manager = env["WARD_MANAGER_PORT"]
    env["WARD_MANAGER_PORT"] = "not-a-port"
    result = subprocess.run(
        args + ["--manager-port", old_manager],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    match = re.search(r"Run directory: (.+)", result.stdout)
    assert match is not None
    root = Path(match.group(1))
    try:
        assert (
            json.loads((root / "config.json").read_text())["environment"][
                "WARD_MANAGER_PORT"
            ]
            == old_manager
        )
    finally:
        shutil.rmtree(root)


def test_delays_are_exported_to_every_component(launch_args) -> None:
    args, env = launch_args
    result = subprocess.run(
        args + ["--delays"], env=env, capture_output=True, text=True, check=True
    )
    match = re.search(r"Run directory: (.+)", result.stdout)
    assert match is not None
    root = Path(match.group(1))
    try:
        config = json.loads((root / "config.json").read_text())
        assert config["delays"] is True
        assert config["environment"]["WARD_DELAYS"] == "1"
        for role in ("manager", "wardd", "emulator", "hwi"):
            assert "export WARD_DELAYS=1" in (root / f"{role}.sh").read_text()
    finally:
        shutil.rmtree(root)


@pytest.mark.parametrize("flag", ["--full_log", "--full-log"])
def test_full_log_is_enabled_and_announced(launch_args, flag: str) -> None:
    args, env = launch_args
    result = subprocess.run(
        args + [flag], env=env, capture_output=True, text=True, check=True
    )
    match = re.search(r"Run directory: (.+)", result.stdout)
    assert match is not None
    root = Path(match.group(1))
    try:
        assert json.loads((root / "config.json").read_text())["full_log"] is True
        assert (root / "full.log").is_file()
        assert f"Combined log: {root / 'full.log'}" in result.stdout
    finally:
        shutil.rmtree(root)


def test_combined_log_preserves_concurrent_records(tmp_path: Path) -> None:
    path = tmp_path / "full.log"
    records = [
        (role, f"record {i} " + "x" * 10000)
        for role in ("manager", "wardd", "emulator", "hwi")
        for i in range(10)
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
        copy_log(process, tmp_path / "hwi.log", "", tmp_path / "full.log", "hwi")
        assert process.wait(timeout=5) == 0
        assert (tmp_path / "hwi.log").read_text() == "out\nerr\nlast"
        assert [
            line.split(" [hwi] ", 1)[1]
            for line in (tmp_path / "full.log").read_text().splitlines()
        ] == ["out", "err", "last"]
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_rejects_occupied_ports_before_launching(launch_args) -> None:
    args, env = launch_args
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", int(env["WARD_MANAGER_PORT"])))
        result = subprocess.run(args, env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert "Cannot use the requested ports" in result.stderr
    assert "Run directory:" not in result.stdout


def test_rejects_default_device_port(launch_args) -> None:
    args, env = launch_args
    env["TREZOR_UDP_PORT"] = "21324"
    result = subprocess.run(args, env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert "30001" in result.stderr


def test_stop_releases_emulator_wait_command(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"run_dir": str(tmp_path)}))
    wait = subprocess.Popen([sys.executable, str(SCRIPT), "--wait", str(config)])
    try:
        deadline = time.monotonic() + 5
        while not (tmp_path / "emulator.ready").exists():
            assert time.monotonic() < deadline
            time.sleep(0.05)
        subprocess.run(
            [sys.executable, str(SCRIPT), "--stop", str(tmp_path)], check=True
        )
        assert wait.wait(timeout=5) == 0
    finally:
        if wait.poll() is None:
            wait.terminate()
            wait.wait(timeout=5)
