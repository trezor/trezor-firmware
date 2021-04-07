#!/usr/bin/env python3
import logging
import os
import platform
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import click

import trezorlib.debuglink
import trezorlib.device
from trezorlib._internal.emulator import CoreEmulator

try:
    import inotify.adapters
except Exception:
    inotify = None


HERE = Path(__file__).parent.resolve()
MICROPYTHON = HERE / "build" / "unix" / "trezor-emu-core"
SRC_DIR = HERE / "src"

PROFILING_WRAPPER = HERE / "prof" / "prof.py"

PROFILE_BASE = Path.home() / ".trezoremu"

TREZOR_STORAGE_FILES = (
    "trezor.flash",
    "trezor.sdcard",
)


def run_command_with_emulator(emulator, command):
    with emulator:
        # first start the subprocess
        process = subprocess.Popen(command)
        # After the subprocess is started, ignore SIGINT in parent
        # (so that we don't need to handle KeyboardInterrupts)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        # SIGINTs will be sent to all children by the OS, so we should be able to safely
        # wait for their exit.
        return process.wait()


def run_emulator(emulator):
    with emulator:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        return emulator.wait()


def watch_emulator(emulator):
    watch = inotify.adapters.InotifyTree(str(SRC_DIR))
    try:
        for _, type_names, _, _ in watch.event_gen(yield_nones=False):
            if "IN_CLOSE_WRITE" in type_names:
                emulator.restart()
    except KeyboardInterrupt:
        emulator.stop()
    return 0


def run_debugger(emulator):
    os.chdir(emulator.workdir)
    env = emulator.make_env()
    if platform.system() == "Darwin":
        env["PATH"] = "/usr/bin"
        os.execvpe(
            "lldb",
            ["lldb", "-f", emulator.executable, "--"] + emulator.make_args(),
            env,
        )
    else:
        os.execvpe(
            "gdb", ["gdb", "--args", emulator.executable] + emulator.make_args(), env
        )


def _from_env(name):
    return os.environ.get(name) == "1"


@click.command(
    context_settings=dict(ignore_unknown_options=True, allow_interspersed_args=False)
)
# fmt: off
@click.option("-a", "--disable-animation/--enable-animation", default=_from_env("TREZOR_DISABLE_ANIMATION"), help="Disable animation")
@click.option("-c", "--command", "run_command", is_flag=True, help="Run command while emulator is running")
@click.option("-d", "--production/--no-production", default=_from_env("PYOPT"), help="Production mode (debuglink disabled)")
@click.option("-D", "--debugger", is_flag=True, help="Run emulator in debugger (gdb/lldb)")
@click.option("-e", "--erase", is_flag=True, help="Erase profile before running")
@click.option("--executable", type=click.Path(exists=True, dir_okay=False), default=os.environ.get("MICROPYTHON"), help="Alternate emulator executable")
@click.option("-g", "--profiling/--no-profiling", default=_from_env("TREZOR_PROFILING"), help="Run with profiler wrapper")
@click.option("-G", "--alloc-profiling/--no-alloc-profiling", default=_from_env("TREZOR_MEMPERF"), help="Profile memory allocation (requires special micropython build)")
@click.option("-h", "--headless", is_flag=True, help="Headless mode (no display)")
@click.option("--heap-size", metavar="SIZE", default="20M", help="Configure heap size")
@click.option("--main", help="Path to python main file")
@click.option("--mnemonic", "mnemonics", multiple=True, help="Initialize device with given mnemonic. Specify multiple times for Shamir shares.")
@click.option("--log-memory/--no-log-memory", default=_from_env("TREZOR_LOG_MEMORY"), help="Print memory usage after workflows")
@click.option("-o", "--output", type=click.File("w"), default="-", help="Redirect emulator output to file")
@click.option("-p", "--profile", metavar="NAME", help="Profile name or path")
@click.option("-P", "--port", metavar="PORT", type=int, default=int(os.environ.get("TREZOR_UDP_PORT", 0)) or None, help="UDP port number")
@click.option("-q", "--quiet", is_flag=True, help="Silence emulator output")
@click.option("-s", "--slip0014", is_flag=True, help="Initialize device with SLIP-14 seed (all all all...)")
@click.option("-t", "--temporary-profile", is_flag=True, help="Create an empty temporary profile")
@click.option("-w", "--watch", is_flag=True, help="Restart emulator if sources change")
@click.option("-X", "--extra-arg", "extra_args", multiple=True, help="Extra argument to pass to micropython")
# fmt: on
@click.argument("command", nargs=-1, type=click.UNPROCESSED)
def cli(
    disable_animation,
    run_command,
    production,
    debugger,
    erase,
    executable,
    profiling,
    alloc_profiling,
    headless,
    heap_size,
    main,
    mnemonics,
    log_memory,
    profile,
    port,
    output,
    quiet,
    slip0014,
    temporary_profile,
    watch,
    extra_args,
    command,
):
    """Run the trezor-core emulator.

    If -c is specified, extra arguments are treated as a command that is executed with
    the running emulator. This command can access the following environment variables:

    \b
    TREZOR_PROFILE_DIR - path to storage directory
    TREZOR_PATH - trezorlib connection string
    TREZOR_UDP_PORT - UDP port on which the emulator listens
    TREZOR_FIDO2_UDP_PORT - UDP port for FIDO2

    By default, emulator output goes to stdout. If silenced with -q, it is redirected
    to $TREZOR_PROFILE_DIR/trezor.log. You can also specify a custom path with -o.
    """
    if executable:
        executable = Path(executable)
    else:
        executable = MICROPYTHON

    if command and not run_command:
        raise click.ClickException("Extra arguments found. Did you mean to use -c?")

    if watch and (command or debugger):
        raise click.ClickException("Cannot use -w together with -c or -D")

    if watch and inotify is None:
        raise click.ClickException("inotify module is missing, install with pip")

    if main and (profiling or alloc_profiling):
        raise click.ClickException("Cannot use --main and -g together")

    if slip0014 and mnemonics:
        raise click.ClickException("Cannot use -s and --mnemonic together")

    if slip0014:
        mnemonics = [" ".join(["all"] * 12)]

    if mnemonics and debugger:
        raise click.ClickException("Cannot load mnemonics when running in debugger")

    if mnemonics and production:
        raise click.ClickException("Cannot load mnemonics in production mode")

    if profiling or alloc_profiling:
        main_args = [str(PROFILING_WRAPPER)]
    elif main:
        main_args = [main]
    else:
        main_args = ["-m", "main"]

    if profile and temporary_profile:
        raise click.ClickException("Cannot use -p and -t together")

    tempdir = None
    if profile:
        if "/" in profile:
            profile_dir = Path(profile)
        else:
            profile_dir = PROFILE_BASE / profile

    elif temporary_profile:
        tempdir = tempfile.TemporaryDirectory(prefix="trezor-emulator-")
        profile_dir = Path(tempdir.name)

    elif "TREZOR_PROFILE_DIR" in os.environ:
        profile_dir = Path(os.environ["TREZOR_PROFILE_DIR"])

    else:
        profile_dir = Path("/var/tmp")

    if erase:
        for entry in TREZOR_STORAGE_FILES:
            (profile_dir / entry).unlink(missing_ok=True)

    if quiet:
        output = None

    logger = logging.getLogger("trezorlib._internal.emulator")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    emulator = CoreEmulator(
        executable,
        profile_dir,
        logfile=output,
        port=port,
        headless=headless,
        debug=not production,
        extra_args=extra_args,
        main_args=main_args,
        heap_size=heap_size,
        disable_animation=disable_animation,
        workdir=SRC_DIR,
    )

    emulator_env = dict(
        TREZOR_PATH=f"udp:127.0.0.1:{emulator.port}",
        TREZOR_PROFILE_DIR=str(profile_dir.resolve()),
        TREZOR_UDP_PORT=str(emulator.port),
        TREZOR_FIDO2_UDP_PORT=str(emulator.port + 2),
        TREZOR_SRC=str(SRC_DIR),
    )
    os.environ.update(emulator_env)
    for k, v in emulator_env.items():
        click.echo(f"{k}={v}")

    if log_memory:
        os.environ["TREZOR_LOG_MEMORY"] = "1"

    if alloc_profiling:
        os.environ["TREZOR_MEMPERF"] = "1"

    if debugger:
        run_debugger(emulator)
        raise RuntimeError("run_debugger should not return")

    emulator.start()

    if mnemonics:
        if slip0014:
            label = "SLIP-0014"
        elif profile:
            label = profile_dir.name
        else:
            label = "Emulator"

        trezorlib.device.wipe(emulator.client)
        trezorlib.debuglink.load_device(
            emulator.client,
            mnemonics,
            pin=None,
            passphrase_protection=False,
            label=label,
        )

    if run_command:
        ret = run_command_with_emulator(emulator, command)
    elif watch:
        ret = watch_emulator(emulator)
    else:
        ret = run_emulator(emulator)

    if tempdir is not None:
        tempdir.cleanup()
    sys.exit(ret)


if __name__ == "__main__":
    cli()
