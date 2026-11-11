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

from tools.ward_stack import SCRIPT, combined_log, command, copy_log, reserve_ports


@pytest.fixture
def launch_args(tmp_path: Path) -> tuple[list[str], dict[str, str]]:
    suite = tmp_path / "suite with spaces"
    cli = suite / "packages/wardd/src/cli.ts"
    cli.parent.mkdir(parents=True)
    cli.touch()
    for _ in range(100):
        manager = 30000 + secrets.randbelow(20000)
        daemon = 30000 + secrets.randbelow(20000)
        debug = 30000 + secrets.randbelow(20000)
        emulator = 30008 + 8 * secrets.randbelow(3000)
        try:
            reserve_ports(manager, daemon, emulator, 3, debug, True)
        except OSError:
            continue
        break
    else:
        pytest.fail("No free ports for launcher test")
    env = {
        **os.environ,
        "WARD_MANAGER_PORT": str(manager),
        "WARDD_PORT": str(daemon),
        "WARDD_DEBUG_PORT": str(debug),
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


@pytest.mark.parametrize(
    "flag", ["--long", "--extra_long", "--extra-long", "--adversarial"]
)
def test_long_demo_reaches_the_hwi(launch_args, flag) -> None:
    args, env = launch_args
    result = subprocess.run(
        args + [flag], env=env, capture_output=True, text=True, check=True
    )
    match = re.search(r"Run directory: (.+)", result.stdout)
    assert match is not None
    root = Path(match.group(1))
    try:
        config = json.loads((root / "config.json").read_text())
        hwi_args, _ = command(config, "hwi", root / "config.json")
        assert ("--extra_long" if flag == "--extra-long" else flag) in hwi_args
    finally:
        shutil.rmtree(root)


@pytest.mark.parametrize("model", ["T3T1", "T3W1"])
def test_model_selects_its_own_emulator(launch_args, model) -> None:
    args, env = launch_args
    result = subprocess.run(
        args + ["--model", model], env=env, capture_output=True, text=True, check=True
    )
    match = re.search(r"Run directory: (.+)", result.stdout)
    assert match is not None
    root = Path(match.group(1))
    try:
        config = json.loads((root / "config.json").read_text())
        emulator, _ = command(config, "emulator", root / "config.json")
        assert config["model"] == model
        assert (
            str(Path("artifacts") / model / "firmware-emu")
            in emulator[emulator.index("--executable") + 1]
        )
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


def test_multiple_devices_use_distinct_profiles_ports_and_one_shared_backend(
    launch_args,
) -> None:
    args, env = launch_args
    result = subprocess.run(
        args + ["--devices", "3"], env=env, capture_output=True, text=True, check=True
    )
    match = re.search(r"Run directory: (.+)", result.stdout)
    assert match is not None
    root = Path(match.group(1))
    try:
        config = json.loads((root / "config.json").read_text())
        profiles = []
        for index in range(3):
            argv, _ = command(config, f"emulator-{index + 1}", root / "config.json")
            assert (
                int(argv[argv.index("-P") + 1]) == config["emulator_port"] + 8 * index
            )
            assert "-s" in argv
            profiles.append(argv[argv.index("-p") + 1])
            assert (root / f"emulator-{index + 1}.sh").is_file()
        assert len(set(profiles)) == 3
        assert result.stdout.count("nix-shell ") == 6
        argv, _ = command(config, "hwi", root / "config.json")
        assert str(SCRIPT.parent / "ward_multi.py") in argv
        assert config["environment"]["WARDD_DEBUG_PORT"] == str(config["debug_port"])
    finally:
        shutil.rmtree(root)


def test_rejects_overlapping_manager_and_debug_ports(launch_args) -> None:
    args, env = launch_args
    result = subprocess.run(
        args + ["--debug-port", env["WARD_MANAGER_PORT"]],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "Cannot use the requested ports" in result.stderr


def test_reserves_the_second_devices_entire_port_block(launch_args) -> None:
    args, env = launch_args
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as occupied:
        occupied.bind(("127.0.0.1", int(env["TREZOR_UDP_PORT"]) + 14))
        result = subprocess.run(
            args + ["--devices", "2"], env=env, capture_output=True, text=True
        )
    assert result.returncode == 2
    assert "Cannot use the requested ports" in result.stderr


def test_multiple_tropic_emulators_get_independent_model_ports(launch_args) -> None:
    args, env = launch_args
    result = subprocess.run(
        args + ["--devices", "2", "--model", "T3W1"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    match = re.search(r"Run directory: (.+)", result.stdout)
    assert match is not None
    root = Path(match.group(1))
    try:
        config = json.loads((root / "config.json").read_text())
        for index in range(2):
            argv, _ = command(config, f"emulator-{index + 1}", root / "config.json")
            assert (
                int(argv[argv.index("--tropic-emulator-port") + 1])
                == config["emulator_port"] + 8 * index + 6
            )
    finally:
        shutil.rmtree(root)


def test_tropic_model_port_is_reserved(launch_args) -> None:
    args, env = launch_args
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind(("127.0.0.1", int(env["TREZOR_UDP_PORT"]) + 14))
        result = subprocess.run(
            args + ["--devices", "2", "--model", "T3W1"],
            env=env,
            capture_output=True,
            text=True,
        )
    assert result.returncode == 2
    assert "Cannot use the requested ports" in result.stderr


def test_service_mode_uses_direct_daemon_and_wallet_driver_without_relay_port(
    launch_args,
) -> None:
    args, env = launch_args
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", int(env["WARDD_PORT"])))
        result = subprocess.run(
            args + ["--service-channel"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
    match = re.search(r"Run directory: (.+)", result.stdout)
    assert match is not None
    root = Path(match.group(1))
    try:
        config = json.loads((root / "config.json").read_text())
        daemon, _ = command(config, "wardd", root / "config.json")
        driver, _ = command(config, "hwi", root / "config.json")
        emulator, _ = command(config, "emulator", root / "config.json")
        assert (
            daemon[daemon.index("--service-channel") + 1]
            == f"udp:127.0.0.1:{env['TREZOR_UDP_PORT']}"
        )
        assert "--wallet-relay" not in daemon
        assert "--service-channel" in driver
        assert "--service-channel" not in emulator
        assert "--enable-ward-service-channel" not in emulator
    finally:
        shutil.rmtree(root)


def test_service_udp_port_is_reserved_even_without_host_binding(launch_args) -> None:
    args, env = launch_args
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as occupied:
        occupied.bind(("127.0.0.1", int(env["TREZOR_UDP_PORT"]) + 7))
        result = subprocess.run(args, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Cannot use the requested ports" in result.stderr


@pytest.mark.parametrize("headless", [False, True])
def test_display_is_visible_by_default_and_hidden_only_explicitly(
    launch_args, headless: bool
) -> None:
    args, env = launch_args
    args = [arg for arg in args if arg != "--headless"]
    args += ["--headless"] if headless else ["--terminal", "xterm"]
    result = subprocess.run(args, env=env, capture_output=True, text=True, check=True)
    match = re.search(r"Run directory: (.+)", result.stdout)
    assert match is not None
    root = Path(match.group(1))
    try:
        config = json.loads((root / "config.json").read_text())
        emulator, _ = command(config, "emulator", root / "config.json")
        assert ("-h" in emulator) is headless
        assert config["gui"] is not headless
        assert config["confirm_delay"] == 2.0
        assert config["environment"]["WARD_CONFIRM_DELAY"] == "2.0"
    finally:
        shutil.rmtree(root)


@pytest.mark.parametrize("delay", ["0", "0.5", "3"])
def test_confirmation_delay_reaches_the_driver_and_multi_device_config(
    launch_args, delay: str
) -> None:
    args, env = launch_args
    result = subprocess.run(
        args + ["--confirm-delay", delay, "--devices", "2"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    match = re.search(r"Run directory: (.+)", result.stdout)
    assert match is not None
    root = Path(match.group(1))
    try:
        config = json.loads((root / "config.json").read_text())
        assert config["confirm_delay"] == float(delay)
        assert float(config["environment"]["WARD_CONFIRM_DELAY"]) == float(delay)
        for role in ("hwi", "emulator-1", "emulator-2"):
            assert (
                f"export WARD_CONFIRM_DELAY={float(delay)}"
                in (root / f"{role}.sh").read_text()
            )
    finally:
        shutil.rmtree(root)


@pytest.mark.parametrize("delay", ["-1", "nan", "inf"])
def test_invalid_confirmation_delays_fail_before_startup(
    launch_args, delay: str
) -> None:
    args, env = launch_args
    result = subprocess.run(
        args + ["--confirm-delay", delay], env=env, capture_output=True, text=True
    )
    assert result.returncode == 2
    assert "finite, nonnegative" in result.stderr
