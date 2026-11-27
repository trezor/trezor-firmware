#!/usr/bin/env python3
"""Open the WARD development stack, one nix-shell terminal per component.

    tools/ward_stack.py [--headless] [--once] [--full-log] [--relay-debug] [--dry-run]

Components, each in its own terminal with its own log in the run directory:

    relay     the Evolu relay: the DATABASE wardd replicates through (`<run>/relay/`)
    wm        the WARD Manager (`packages/wardd/src/wmCli.ts`): orders each ward's transitions and
              attests its head; logs every enrolment, attestation and advance (`<run>/wm/wm.json`)
    wardd     the WARD daemon, verbose: every call, its outcome and the device messages it
              exchanged; its Evolu replica lives in `<run>/wardd/`, and it asks the WM over HTTP
    emulator  a debuglink T3T1 emulator seeded with the SLIP-14 test seed; its log keeps only the
              WARD lines (queueing, conflicts and how each was resolved) unless
              `--emulator-full-log`
    wardd2, emulator2
              A SECOND DEVICE of the same wallet with its own wardd, idle until the adapter starts
              it while the WM is down; its wardd fills its replica from the relay. That wardd runs
              with `--adversarial-tests`: the adapter has it serve the device an older state
    adapter   `tools/ward_stack_adapter.py`: one WARD session through wardd, step by step, then the
              two devices queue conflicting changes offline and the second resolves them, and
              finally the WM is restored from a backup and rolled forward by the first device

`--full-log` also merges every component into `<run>/full.log`, each line timestamped and tagged.
Stop the stack with `q` in the adapter's terminal, Ctrl-C here, or `--stop RUN_DIR` from anywhere.

THE WM CAN BE TAKEN DOWN without stopping the stack: Enter in its terminal (or creating
`<run>/wm.down`) stops it, Enter again (or removing the file) starts it. While it is down wardd
reports it unavailable and the device reads what it last adopted, or what wardd catches it up to
(the newest head a kept WM attestation names), with the "Manager-signed date: <date>" warning;
the adapter does exactly that in its last steps.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import secrets
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

FIRMWARE = Path(__file__).resolve().parent.parent
SCRIPT = Path(__file__).resolve()
ROLES = {
    "relay": "Evolu relay (database)",
    "wm": "WARD Manager",
    "wardd": "wardd",
    "emulator": "Trezor emulator",
    "wardd2": "wardd (second device)",
    "emulator2": "Trezor emulator (second device)",
    "adapter": "WARD adapter",
}

# What an emulator log keeps by default: the WARD app's own lines, WARD messages and screens by
# name, and the ready line. Everything else -- other apps, the event loop, paths -- is silenced.
_EMULATOR_KEEP = re.compile(r"apps\.ward|\bWard[A-Z]|\bward_|Emulator ready")


def find_python() -> Path:
    """The firmware venv's interpreter. A worktree has none of its own, so the main checkout's
    is used, with this tree's `python/src` first on PYTHONPATH."""
    if os.environ.get("WARD_STACK_PYTHON"):
        return Path(os.environ["WARD_STACK_PYTHON"])
    for root in (FIRMWARE, *FIRMWARE.parents):
        candidate = root / ".venv/bin/python"
        if candidate.is_file():
            return candidate
    return Path(sys.executable)


def find_suite() -> Path:
    if os.environ.get("WARDD_SUITE_DIR"):
        return Path(os.environ["WARDD_SUITE_DIR"])
    # a worktree sits in <firmware>/.worktrees/<name>; the Suite checkout is beside <firmware>
    workspace = FIRMWARE.parents[2] if FIRMWARE.parent.name == ".worktrees" else FIRMWARE.parent
    for path in (
        workspace / "trezor-suite-petrsusil/.worktrees/ward-draft",
        workspace / "trezor-suite-petrsusil",
        workspace / "trezor-suite",
    ):
        if (path / "packages/wardd/src/relayCli.ts").exists():
            return path
    return workspace / "trezor-suite"


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def stopped(config: dict[str, Any]) -> bool:
    return (Path(config["run_dir"]) / "stop").exists()


def stop(config: dict[str, Any]) -> None:
    (Path(config["run_dir"]) / "stop").touch()


def wait_for(
    config: dict[str, Any],
    ready: Any,
    process: subprocess.Popen | None = None,
    timeout: float | None = None,
) -> None:
    """Wait until `ready()`; `timeout=0` waits for as long as the stack runs."""
    timeout = config["timeout"] if timeout is None else timeout
    deadline = time.monotonic() + timeout if timeout else float("inf")
    while not stopped(config):
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"Service exited with status {process.returncode}")
        try:
            if ready():
                return
        except (OSError, ValueError):
            pass
        if time.monotonic() >= deadline:
            raise TimeoutError("Timed out waiting for the stack; see the component logs")
        time.sleep(0.2)
    raise InterruptedError("Stack stopped")


def listening(port: int) -> bool:
    with socket.create_connection(("127.0.0.1", port), timeout=1):
        return True


def command(config: dict[str, Any], role: str, config_path: Path) -> tuple[list[str], Path]:
    python = config["python"]
    root = Path(config["run_dir"])
    wardd_dir = Path(config["suite"]) / "packages/wardd"
    if role == "relay":
        return [
            "node",
            "--import",
            "tsx",
            "src/relayCli.ts",
            "--port",
            str(config["relay_port"]),
            "--data-dir",
            str(root / "relay"),
            *(["--verbose"] if config.get("relay_debug") else []),
        ], wardd_dir
    if role == "wm":
        return [
            "node",
            "--import",
            "tsx",
            "src/wmCli.ts",
            "--port",
            str(config["wm_port"]),
            "--data-dir",
            str(root / "wm"),
        ], wardd_dir
    if role in ("wardd", "wardd2"):
        return [
            "node",
            "--import",
            "tsx",
            "src/cli.ts",
            "--port",
            str(config[f"{role}_port"]),
            "--data-dir",
            str(root / role),
            "--token-file",
            str(root / "token"),
            "--relay",
            f"ws://127.0.0.1:{config['relay_port']}",
            "--wm",
            f"http://127.0.0.1:{config['wm_port']}",
            "--verbose",
            # the second device's wardd plays the HOSTILE HOST in the adapter's adversarial tests
            *(["--adversarial-tests"] if role == "wardd2" else []),
        ], wardd_dir
    if role in ("emulator", "emulator2"):
        # not `-q`: the firmware's WARD log lines are what this terminal is for
        return [
            python,
            str(FIRMWARE / "core/emu.py"),
            "--executable",
            str(config["emulator_executable"]),
            *([] if config.get("gui", False) else ["-h"]),
            "-s",
            "-p",
            str(root / role),
            "-P",
            str(config[f"{role}_port"]),
            "-c",
            python,
            str(SCRIPT),
            "--wait",
            str(config_path),
            "--wait-role",
            role,
        ], FIRMWARE
    return [python, str(FIRMWARE / "tools/ward_stack_adapter.py")], FIRMWARE


def combined_log(path: Path, source: str, line: str) -> None:
    with path.open("a", encoding="utf-8") as logfile:
        fcntl.flock(logfile, fcntl.LOCK_EX)
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        logfile.write(f"{timestamp} [{source}] {line.rstrip(chr(10))}\n")
        logfile.flush()
        fcntl.flock(logfile, fcntl.LOCK_UN)


def copy_log(
    process: subprocess.Popen,
    path: Path,
    prefix: str,
    combined: Path | None = None,
    source: str = "component",
    keep: "re.Pattern[str] | None" = None,
) -> None:
    assert process.stdout is not None
    with path.open("a") as logfile:
        for line in process.stdout:
            if keep is not None and not keep.search(line):
                continue
            logfile.write(line)
            logfile.flush()
            if combined is not None:
                combined_log(combined, source, line)
            try:
                print(f"{prefix}{line}", end="", flush=True)
            except (BrokenPipeError, OSError):
                pass


# What each component waits for before it starts.
_PREREQUISITES = {
    "relay": (),
    "wm": (),
    "wardd": ("relay", "wm"),
    "emulator": (),
    # `second.ready` is the adapter's: it starts the second device once the WM is down
    "wardd2": ("relay", "wm", "second"),
    "emulator2": ("second",),
    "adapter": ("relay", "wm", "wardd", "emulator"),
}


def wm_down_requested(root: Path) -> bool:
    """Whether the WM should be down: `<run>/wm.down` exists. Enter in an interactive WM
    terminal toggles that file, so the adapter and the user drive the same switch."""
    if sys.stdin.isatty() and select.select([sys.stdin], [], [], 0)[0]:
        line = sys.stdin.readline()
        if not line or line.strip().lower() == "q":
            (root / "stop").touch()  # as `stop()`: q here stops the whole stack too
        elif (root / "wm.down").exists():
            (root / "wm.down").unlink()
        else:
            (root / "wm.down").touch()
    return (root / "wm.down").exists()


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
        second = "second" in _PREREQUISITES[role]
        if second:
            print("Idle until the adapter starts the second device (with the WM down).", flush=True)
        wait_for(
            config,
            lambda: all((root / f"{name}.ready").exists() for name in _PREREQUISITES[role]),
            timeout=0 if second else None,
        )
        args, directory = command(config, role, config_path)
        print(f"{role}: {shlex.join(args)}", flush=True)
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
                    None
                    if role not in ("emulator", "emulator2") or config.get("emulator_full_log")
                    else _EMULATOR_KEEP,
                ),
                daemon=True,
            )
            output.start()
            if role == "relay":
                wait_for(config, lambda: listening(config["relay_port"]), process)
                (root / "relay.ready").touch()
            elif role == "wm":
                wait_for(config, lambda: listening(config["wm_port"]), process)
                (root / "wm.stopped").unlink(missing_ok=True)
                (root / "wm.ready").touch()
                if sys.stdin.isatty():
                    print("Enter stops the WARD Manager (and starts it again).", flush=True)
            elif role in ("wardd", "wardd2"):
                wait_for(config, lambda: listening(config[f"{role}_port"]), process)
                (root / f"{role}.ready").touch()
            while process.poll() is None and not stopped(config):
                if role == "wm" and wm_down_requested(root):
                    break
                time.sleep(0.2)
            if stopped(config):
                break
            if role == "wm" and process.poll() is None:
                # TAKEN DOWN ON REQUEST: stop it, say so, and wait to be asked back
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=15)
                output.join(timeout=2)
                (root / "wm.stopped").touch()
                print(
                    "WARD Manager stopped: wardd reports it unavailable, and reads show"
                    " 'Manager-signed date: <date>'. Enter (or removing wm.down)"
                    " starts it again.",
                    flush=True,
                )
                while not stopped(config) and wm_down_requested(root):
                    time.sleep(0.2)
                continue
            result = process.wait()
            output.join(timeout=2)
            if role != "adapter":
                raise RuntimeError(f"{role} stopped unexpectedly (status {result})")
            (root / "adapter.done").write_text(str(result))
            if result != 0:
                raise RuntimeError(f"the adapter failed (status {result}); see adapter.log")
            if config["once"]:
                break
            print("Session passed. Enter reruns it; q stops the whole stack.", flush=True)
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
            if role in ("emulator", "emulator2"):
                # emu.py -c ends its waiting command and cleans up its own firmware process
                stop(config)
            else:
                process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                if role in ("emulator", "emulator2"):
                    pidfile = root / role / "trezor.pid"
                    if pidfile.exists():
                        try:
                            os.kill(int(pidfile.read_text()), signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                    process.wait(timeout=10)
                else:
                    process.kill()
                    process.wait(timeout=5)
        if output is not None:
            output.join(timeout=2)
    return result


def reserve_ports(
    relay: int,
    wardd: int,
    emulator: int,
    wm: int | None = None,
    wardd2: int | None = None,
    emulator2: int | None = None,
) -> None:
    """Refuse ports that are taken, out of range, or the default emulator block."""
    tcp = [relay, wardd] + [p for p in (wm, wardd2) if p is not None]
    if not all(1 <= port <= 65535 for port in tcp):
        raise ValueError("TCP ports must be between 1 and 65535")
    if len(set(tcp)) != len(tcp):
        raise ValueError("the relay, the WM and each wardd need distinct ports")
    emulators = [emulator] + ([] if emulator2 is None else [emulator2])
    if not all(30000 < port <= 65536 - 8 for port in emulators):
        raise ValueError("TREZOR_UDP_PORT must be between 30001 and 65528")
    if emulator2 is not None and abs(emulator2 - emulator) < 8:
        raise ValueError("the two emulators need port blocks at least 8 apart")
    sockets = []
    try:
        for kind, port in [
            *[(socket.SOCK_STREAM, port) for port in tcp],
            *[(socket.SOCK_DGRAM, e + offset) for e in emulators for offset in range(8)],
        ]:
            sock = socket.socket(socket.AF_INET, kind)
            sockets.append(sock)
            sock.bind(("127.0.0.1", port))
    finally:
        for sock in sockets:
            sock.close()


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
        "--relay-port", type=int, default=os.environ.get("WARD_RELAY_PORT", "21340")
    )
    parser.add_argument("--wm-port", type=int, default=os.environ.get("WARD_WM_PORT", "21330"))
    parser.add_argument("--wardd-port", type=int, default=os.environ.get("WARDD_PORT", "21329"))
    parser.add_argument(
        "--wardd2-port", type=int, default=os.environ.get("WARDD2_PORT", "21331")
    )
    parser.add_argument(
        "--emulator-port", type=int, default=os.environ.get("TREZOR_UDP_PORT", "37744")
    )
    parser.add_argument(
        "--emulator2-port", type=int, default=os.environ.get("TREZOR_UDP_PORT2", "37752")
    )
    parser.add_argument(
        "--emulator-full-log",
        action="store_true",
        help="Keep every emulator line, not only the WARD ones",
    )
    parser.add_argument("--terminal", choices=("gnome-terminal", "konsole", "xterm"))
    parser.add_argument("--model", choices=("T3T1",), default="T3T1")
    parser.add_argument("--emulator-executable", type=Path)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument(
        "--confirm-delay",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="Leave each confirmation screen up this long before the adapter confirms it",
    )
    parser.add_argument(
        "--full_log",
        "--full-log",
        action="store_true",
        help="Merge all component output into RUN_DIR/full.log",
    )
    parser.add_argument(
        "--relay-debug",
        action="store_true",
        help="Log every relay sync exchange and SQL statement (very verbose)",
    )
    parser.add_argument(
        "--once", action="store_true", help="Stop all components after one passing session"
    )
    display = parser.add_mutually_exclusive_group()
    display.add_argument("--gui", action="store_true", help="Show the emulator display (default)")
    display.add_argument(
        "--headless",
        action="store_true",
        help="Hide the emulator display and run components without terminal windows",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the commands only")
    parser.add_argument("--stop", type=Path, metavar="RUN_DIR", help="Stop an existing stack")
    parser.add_argument("--component", help=argparse.SUPPRESS)
    parser.add_argument("--config", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--wait", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--wait-role", default="emulator", help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.gui = not args.headless
    if args.confirm_delay < 0:
        parser.error("--confirm-delay must be a nonnegative number of seconds")
    if args.emulator_executable is None:
        args.emulator_executable = FIRMWARE / f"core/build-xtask/artifacts/{args.model}/firmware-emu"
    if args.stop:
        stop(load_config(args.stop / "config.json"))
        return 0
    if args.wait:
        config = load_config(args.wait)
        (Path(config["run_dir"]) / f"{args.wait_role}.ready").touch()
        while not stopped(config):
            time.sleep(0.2)
        return 0
    if args.component:
        if args.config is None or args.component not in ROLES:
            parser.error("Unknown component")
        return component(args.config, args.component)

    terminal = args.terminal or next(
        (name for name in ("gnome-terminal", "konsole", "xterm") if shutil.which(name)), None
    )
    if not args.headless and terminal is None:
        parser.error("Install gnome-terminal, konsole or xterm, or use --headless")
    if (
        not args.headless
        and not args.dry_run
        and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    ):
        parser.error("No graphical display is available; use --headless")
    if not shutil.which("nix-shell"):
        parser.error("nix-shell is required")
    if not (args.suite / "packages/wardd/src/relayCli.ts").is_file():
        parser.error("--suite must point to a ward-draft Suite checkout (packages/wardd)")
    try:
        reserve_ports(
            args.relay_port,
            args.wardd_port,
            args.emulator_port,
            args.wm_port,
            args.wardd2_port,
            args.emulator2_port,
        )
    except (OSError, ValueError) as error:
        parser.error(f"Cannot use the requested ports: {error}")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    python = find_python()
    if not args.dry_run and not args.emulator_executable.is_file():
        parser.error(
            "Build the emulator first: xtask build firmware --emulator -m T3T1 -p test --frozen false"
        )

    root = Path(tempfile.mkdtemp(prefix="ward-stack-"))
    environment = {
        "TREZOR_FIRMWARE": str(FIRMWARE),
        "PYTHONPATH": str(FIRMWARE / "python/src"),
        "WARD_CONFIRM_DELAY": str(args.confirm_delay),
        "WARD_RELAY_PORT": str(args.relay_port),
        "WARD_RELAY_URL": f"ws://127.0.0.1:{args.relay_port}",
        "WARD_WM_PORT": str(args.wm_port),
        "WARD_WM_URL": f"http://127.0.0.1:{args.wm_port}",
        "WARD_STACK_RUN_DIR": str(root),
        "WARDD_PORT": str(args.wardd_port),
        "WARDD_URL": f"ws://127.0.0.1:{args.wardd_port}",
        "WARD_TOKEN_FILE": str(root / "token"),
        "TREZOR_UDP_PORT": str(args.emulator_port),
        "TREZOR_PATH": f"udp:127.0.0.1:{args.emulator_port}",
        "WARDD2_PORT": str(args.wardd2_port),
        "WARDD2_URL": f"ws://127.0.0.1:{args.wardd2_port}",
        "TREZOR_UDP_PORT2": str(args.emulator2_port),
        "WARDD_SUITE_DIR": str(args.suite.resolve()),
    }
    config = {
        **vars(args),
        "python": str(python),
        "suite": str(args.suite.resolve()),
        "emulator_executable": str(args.emulator_executable.resolve()),
        "run_dir": str(root),
        "environment": environment,
    }
    config_path = root / "config.json"
    config_path.write_text(json.dumps(config, default=str, indent=2))
    # the pairing token wardd checks and the adapter presents; readable by this user only
    token = root / "token"
    token.write_text(secrets.token_hex(32))
    token.chmod(0o600)
    if args.full_log:
        (root / "full.log").touch()
    exports = "".join(f"export {name}={shlex.quote(value)}\n" for name, value in environment.items())
    (root / "env.sh").write_text(exports)

    print(
        f"Run directory: {root}\n"
        f"Ports: relay={args.relay_port}, wm={args.wm_port}, wardd={args.wardd_port},"
        f" device={args.emulator_port}, wardd2={args.wardd2_port},"
        f" device2={args.emulator2_port}\n"
        f"Logs: {', '.join(f'{role}.log' for role in ROLES)}"
        + (", full.log" if args.full_log else ""),
        flush=True,
    )
    print(f"Stop from another terminal: {shlex.join([str(SCRIPT), '--stop', str(root)])}", flush=True)
    for name in ("SIGINT", "SIGTERM", "SIGHUP"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *_: stop(config))
    processes = []
    try:
        for role, title in ROLES.items():
            runtime = shlex.join(
                [str(python), str(SCRIPT), "--component", role, "--config", str(config_path)]
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
                shell if args.headless else terminal_command(terminal or "gnome-terminal", title, shell)
            )
            if args.dry_run:
                print(shlex.join(launch))
            else:
                processes.append(subprocess.Popen(launch, cwd=FIRMWARE))
        if args.dry_run:
            return 0
        while not stopped(config):
            if args.once and (root / "adapter.done").exists():
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
