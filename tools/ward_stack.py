#!/usr/bin/env python3
"""Open the WARD development stack in four separate nix-shell terminals."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import select
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

FIRMWARE = Path(__file__).resolve().parent.parent
SCRIPT = Path(__file__).resolve()
ROLES = {
    "manager": "WARD Manager",
    "wardd": "wardd / Evolu",
    "emulator": "Trezor emulator",
    "hwi": "WARD HWI",
}


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def stopped(config: dict[str, Any]) -> bool:
    return (Path(config["run_dir"]) / "stop").exists()


def stop(config: dict[str, Any]) -> None:
    (Path(config["run_dir"]) / "stop").touch()


def wait_for(
    config: dict[str, Any], ready: Any, process: subprocess.Popen | None = None
) -> None:
    deadline = time.monotonic() + config["timeout"]
    while not stopped(config):
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"Service exited with status {process.returncode}")
        try:
            if ready():
                return
        except (OSError, ValueError):
            pass
        if time.monotonic() >= deadline:
            raise TimeoutError(
                "Timed out waiting for the stack; see the component logs"
            )
        time.sleep(0.2)
    raise InterruptedError("Stack stopped")


def command(
    config: dict[str, Any], role: str, config_path: Path
) -> tuple[list[str], Path]:
    python = str(FIRMWARE / ".venv/bin/python")
    root = Path(config["run_dir"])
    if role == "manager":
        return [
            python,
            str(FIRMWARE / "tools/ward_manager.py"),
            "--debug-key",
            "--db",
            str(root / "manager.sqlite3"),
        ], FIRMWARE
    if role == "wardd":
        return [
            "node",
            "--import",
            "tsx",
            "src/cli.ts",
            "--data-dir",
            str(root / "evolu"),
            "--verbose",
        ], Path(config["suite"]) / "packages/wardd"
    if role == "emulator":
        return [
            python,
            str(FIRMWARE / "core/emu.py"),
            "--executable",
            str(FIRMWARE / "core/build/artifacts/T3T1/firmware-emu"),
            *([] if config.get("gui", False) else ["-h"]),
            "-s",
            "-q",
            "-p",
            str(root / "emulator"),
            "-c",
            python,
            str(SCRIPT),
            "--wait",
            str(config_path),
        ], FIRMWARE
    return [
        python,
        str(FIRMWARE / "rust/ward-relay/examples/trezor_hwi.py"),
        "--jade-host",
        "--label",
        config["label"],
    ], FIRMWARE


def combined_log(path: Path, source: str, line: str) -> None:
    with path.open("a", encoding="utf-8") as logfile:
        fcntl.flock(logfile, fcntl.LOCK_EX)
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        message = line.rstrip("\n")
        logfile.write(f"{timestamp} [{source}] {message}\n")
        logfile.flush()
        fcntl.flock(logfile, fcntl.LOCK_UN)


def copy_log(
    process: subprocess.Popen,
    path: Path,
    prefix: str,
    combined: Path | None = None,
    source: str = "component",
) -> None:
    assert process.stdout is not None
    with path.open("a") as logfile:
        for line in process.stdout:
            logfile.write(line)
            logfile.flush()
            if combined is not None:
                combined_log(combined, source, line)
            try:
                print(f"{prefix}{line}", end="", flush=True)
            except (BrokenPipeError, OSError):
                pass


def component(config_path: Path, role: str) -> int:
    config = load_config(config_path)
    root = Path(config["run_dir"])
    os.environ.update(config["environment"])
    for name in ("SIGINT", "SIGTERM", "SIGHUP"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *_: stop(config))
    process = None
    output = None
    result = 0
    try:
        if stopped(config):
            return 0
        if role == "wardd":
            wait_for(config, lambda: (root / "manager.ready").exists())
        if role == "hwi":
            wait_for(
                config,
                lambda: all(
                    (root / f"{name}.ready").exists()
                    for name in ("manager", "wardd", "emulator")
                ),
            )
        args, directory = command(config, role, config_path)
        print(f"{ROLES[role]}: {shlex.join(args)}", flush=True)
        print(f"Nix shell: {os.environ.get('IN_NIX_SHELL', 'missing')}", flush=True)
        while not stopped(config):
            process = subprocess.Popen(
                args,
                cwd=directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
            output = threading.Thread(
                target=copy_log,
                args=(
                    process,
                    root / f"{role}.log",
                    f"[{role}] " if config["headless"] else "",
                    root / "full.log" if config.get("full_log", False) else None,
                    role,
                ),
                daemon=True,
            )
            output.start()
            if role == "manager":

                def ready() -> bool:
                    with urlopen(
                        f"http://127.0.0.1:{config['manager_port']}/health",
                        timeout=3 if config.get("delays", False) else 1,
                    ) as response:
                        return response.status == 200

                wait_for(config, ready, process)
                (root / "manager.ready").touch()
            elif role == "wardd":

                def ready() -> bool:
                    if not (root / "evolu/token").is_file():
                        return False
                    with socket.create_connection(
                        ("127.0.0.1", config["wardd_port"]), timeout=1
                    ):
                        return True

                wait_for(config, ready, process)
                (root / "wardd.ready").touch()
            while process.poll() is None and not stopped(config):
                time.sleep(0.2)
            if stopped(config):
                break
            result = process.wait()
            output.join(timeout=2)
            if result != 0:
                raise RuntimeError(f"{role} exited with status {result}")
            if role != "hwi":
                raise RuntimeError(f"{role} stopped unexpectedly")
            (root / "hwi.done").write_text("0")
            if config["once"]:
                break
            print("Demo passed. Enter reruns it; q stops the whole stack.", flush=True)
            while not stopped(config):
                if select.select([sys.stdin], [], [], 0.2)[0]:
                    response = sys.stdin.readline()
                    if not response or response.strip().lower() == "q":
                        stop(config)
                    break
    except InterruptedError:
        pass
    except Exception as error:
        result = 1
        message = f"{role}: {error}"
        print(message, file=sys.stderr, flush=True)
        (root / f"{role}.failed").write_text(message)
        stop(config)
    finally:
        if process is not None and process.poll() is None:
            if role == "emulator":
                # emu.py -c exits its waiting command and cleans up its own firmware process.
                stop(config)
            else:
                process.send_signal(
                    signal.SIGINT if role == "manager" else signal.SIGTERM
                )
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                if role == "emulator":
                    pidfile = root / "emulator/trezor.pid"
                    if pidfile.exists():
                        try:
                            os.kill(int(pidfile.read_text()), signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                    process.wait(timeout=10)
                else:
                    process.kill()
                    process.wait(timeout=5)
        if (
            role != "hwi"
            and process is not None
            and process.returncode
            not in (
                None,
                0,
                -signal.SIGTERM,
                -signal.SIGINT,
                128 + signal.SIGTERM,
                128 + signal.SIGINT,
            )
        ):
            result = 1
            failure = root / f"{role}.failed"
            if not failure.exists():
                failure.write_text(
                    f"{role}: shutdown failed with status {process.returncode}; see {role}.log"
                )
        if output is not None:
            output.join(timeout=2)
    return result


def reserve_ports(manager: int, wardd: int, emulator: int) -> None:
    if not all(1 <= port <= 65535 for port in (manager, wardd)):
        raise ValueError("TCP ports must be between 1 and 65535")
    if not 30000 < emulator <= 65529:
        raise ValueError("TREZOR_UDP_PORT must be between 30001 and 65529")
    sockets = []
    try:
        for kind, port in [
            (socket.SOCK_STREAM, manager),
            (socket.SOCK_STREAM, wardd),
            *[(socket.SOCK_DGRAM, port) for port in range(emulator, emulator + 7)],
        ]:
            sock = socket.socket(socket.AF_INET, kind)
            sockets.append(sock)
            sock.bind(("127.0.0.1", port))
    finally:
        for sock in sockets:
            sock.close()


def find_suite() -> Path:
    if os.environ.get("WARDD_SUITE_DIR"):
        return Path(os.environ["WARDD_SUITE_DIR"])
    for path in (
        FIRMWARE.parent / "trezor-suite-petrsusil/.worktrees/ward-poc-encrypted",
        FIRMWARE.parent / "trezor-suite-petrsusil",
        FIRMWARE.parent / "trezor-suite",
    ):
        if (path / "packages/wardd/src/cli.ts").exists():
            return path
    return FIRMWARE.parent / "trezor-suite"


def terminal_command(terminal: str, title: str, shell: list[str]) -> list[str]:
    if terminal == "gnome-terminal":
        return [terminal, "--wait", "--window", "--title", title, "--", *shell]
    if terminal == "konsole":
        return [terminal, "--separate", "-p", f"tabtitle={title}", "-e", *shell]
    return [terminal, "-T", title, "-e", *shell]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=find_suite())
    parser.add_argument(
        "--manager-port", type=int, default=os.environ.get("WARD_MANAGER_PORT", "21330")
    )
    parser.add_argument(
        "--wardd-port", type=int, default=os.environ.get("WARDD_PORT", "21329")
    )
    parser.add_argument(
        "--emulator-port", type=int, default=os.environ.get("TREZOR_UDP_PORT", "37744")
    )
    parser.add_argument("--terminal", choices=("gnome-terminal", "konsole", "xterm"))
    parser.add_argument("--label", default="WARD demo")
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument(
        "--delays",
        action="store_true",
        help="Pause one second at request/response forwarding steps",
    )
    parser.add_argument(
        "--full_log",
        "--full-log",
        action="store_true",
        help="Merge all component stdout/stderr into RUN_DIR/full.log",
    )
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Install Python bindings and build the Safe 5 emulator first",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Stop all components after one successful write/lookup",
    )
    parser.add_argument(
        "--gui",
        "--emulator-gui",
        action="store_true",
        help="Show the emulator display (the emulator is headless by default)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the four nix-shell processes without terminal windows",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print terminal commands without launching",
    )
    parser.add_argument(
        "--stop", type=Path, metavar="RUN_DIR", help="Stop an existing stack"
    )
    parser.add_argument("--component", choices=tuple(ROLES), help=argparse.SUPPRESS)
    parser.add_argument("--config", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--wait", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.stop:
        stop(load_config(args.stop / "config.json"))
        return 0
    if args.wait:
        config = load_config(args.wait)
        (Path(config["run_dir"]) / "emulator.ready").touch()
        while not stopped(config):
            time.sleep(0.2)
        return 0
    if args.component:
        if args.config is None:
            parser.error("--component requires --config")
        return component(args.config, args.component)

    terminal = args.terminal or next(
        (name for name in ("gnome-terminal", "konsole", "xterm") if shutil.which(name)),
        None,
    )
    if not args.headless and terminal is None:
        parser.error("Install gnome-terminal, konsole or xterm, or use --headless")
    if (
        args.gui
        and not args.dry_run
        and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    ):
        parser.error("--gui requires a graphical display (DISPLAY or WAYLAND_DISPLAY)")
    if (
        not args.headless
        and not args.dry_run
        and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    ):
        parser.error("No graphical display is available; use --headless")
    if not shutil.which("nix-shell"):
        parser.error("nix-shell is required")
    if not (args.suite / "packages/wardd/src/cli.ts").is_file():
        parser.error("--suite must point to the encrypted Suite checkout")
    try:
        reserve_ports(args.manager_port, args.wardd_port, args.emulator_port)
    except (OSError, ValueError) as error:
        parser.error(f"Cannot use the requested ports: {error}")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    root = Path(tempfile.mkdtemp(prefix="ward-stack-", dir="/tmp"))
    environment = {
        "WARD_DELAYS": "1" if args.delays else "0",
        "WARD_MANAGER_PORT": str(args.manager_port),
        "WARDD_PORT": str(args.wardd_port),
        "TREZOR_UDP_PORT": str(args.emulator_port),
        "WARD_MANAGER_URL": f"http://127.0.0.1:{args.manager_port}",
        "WARDD_URL": f"ws://127.0.0.1:{args.wardd_port}",
        "TREZOR_PATH": f"udp:127.0.0.1:{args.emulator_port}",
        "WARD_TOKEN_FILE": str(root / "evolu/token"),
        "WARD_DATA_DIR": str(root / "evolu"),
    }
    config = {
        **vars(args),
        "suite": str(args.suite.resolve()),
        "run_dir": str(root),
        "environment": environment,
    }
    config_path = root / "config.json"
    config_path.write_text(json.dumps(config, default=str, indent=2))
    if args.full_log:
        (root / "full.log").touch()
    exports = "".join(
        f"export {name}={shlex.quote(value)}\n" for name, value in environment.items()
    )
    (root / "env.sh").write_text(exports)
    if args.prepare:
        commands = [
            ["uv", "sync", "--locked"],
            [
                "env",
                "-u",
                "PYTHONPATH",
                "uv",
                "pip",
                "install",
                "--python",
                str(FIRMWARE / ".venv/bin/python"),
                str(FIRMWARE / "rust/ward-relay"),
                "-e",
                str(FIRMWARE.parent / "wallets/Jade"),
            ],
            [
                "uv",
                "run",
                "--no-sync",
                "xtask",
                "build",
                "firmware",
                "--emulator",
                "-m",
                "T3T1",
                "-p",
                "test-live",
            ],
        ]
        prepare = root / "prepare.sh"
        prepare.write_text(
            "set -eu\n" + "\n".join(shlex.join(command) for command in commands) + "\n"
        )
        if not args.dry_run:
            subprocess.run(
                [
                    "nix-shell",
                    str(FIRMWARE / "shell.nix"),
                    "--run",
                    shlex.join(["bash", str(prepare)]),
                ],
                cwd=FIRMWARE,
                check=True,
            )
    if not args.dry_run:
        if not (FIRMWARE / ".venv/bin/python").is_file():
            parser.error(
                "Create the firmware virtual environment first, or pass --prepare"
            )
        if not (FIRMWARE / "core/build/artifacts/T3T1/firmware-emu").is_file():
            parser.error("Build the T3T1 test-live emulator first, or pass --prepare")
        check = subprocess.run(
            [
                str(FIRMWARE / ".venv/bin/python"),
                "-c",
                "from jadepy.ward import WardAdapter",
            ],
            capture_output=True,
            text=True,
        )
        if check.returncode:
            parser.error(
                "Install the shared adapter and jadepy first, or pass --prepare"
            )

    print(
        f"Run directory: {root}\nPorts: WM={args.manager_port}, wardd={args.wardd_port}, device={args.emulator_port}",
        flush=True,
    )
    print(
        f"Stop from another terminal: {shlex.join([str(SCRIPT), '--stop', str(root)])}",
        flush=True,
    )
    if args.full_log:
        print(f"Combined log: {root / 'full.log'}", flush=True)
    for name in ("SIGINT", "SIGTERM", "SIGHUP"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *_: stop(config))
    processes = []
    try:
        for role, title in ROLES.items():
            runtime = shlex.join(
                [
                    str(FIRMWARE / ".venv/bin/python"),
                    str(SCRIPT),
                    "--component",
                    role,
                    "--config",
                    str(config_path),
                ]
            )
            wrapper = root / f"{role}.sh"
            wrapper.write_text("set -eu\n" + exports + f"exec {runtime}\n")
            shell = [
                "nix-shell",
                str(FIRMWARE / "shell.nix"),
                "--run",
                shlex.join(["bash", str(wrapper)]),
            ]
            launch = (
                shell
                if args.headless
                else terminal_command(terminal or "gnome-terminal", title, shell)
            )
            if args.dry_run:
                print(shlex.join(launch))
            else:
                processes.append(subprocess.Popen(launch, cwd=FIRMWARE))
        if args.dry_run:
            return 0
        while not stopped(config):
            if args.once and (root / "hwi.done").exists():
                break
            finished = [process for process in processes if process.poll() is not None]
            if finished:
                if any(process.returncode != 0 for process in finished):
                    (root / "terminal.failed").write_text(
                        "A terminal or nix-shell exited with an error; see its output"
                    )
                stop(config)
                break
            time.sleep(0.2)
    finally:
        if not args.dry_run:
            stop(config)
        for process in processes:
            try:
                process.wait(timeout=25)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
    failures = list(root.glob("*.failed"))
    for path in failures:
        print(path.read_text(), file=sys.stderr)
    print(f"Stack stopped. Logs and state remain in {root}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
