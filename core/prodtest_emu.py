#!/usr/bin/env python3
from __future__ import annotations

import logging
import signal
import subprocess
import sys
import tempfile

import click

from trezorlib._internal.prodtest_emulator import get_prodtest_emulator


@click.command(
    context_settings=dict(ignore_unknown_options=True, allow_interspersed_args=False)
)
# fmt: off
@click.option("-m", "--model", envvar="TREZOR_MODEL", default=None, help="Trezor model name (or set TREZOR_MODEL); defaults to the latest build")
@click.option("-c", "--command", "run_command", is_flag=True, help="Run command while emulator is running")
@click.option("-h", "--headless", is_flag=True, help="Headless mode (no display)")
# fmt: on
@click.argument("command", nargs=-1, type=click.UNPROCESSED)
def cli(model: str, run_command: bool, headless: bool, command: list[str]) -> None:
    """Run the prodtest emulator.

    If -c is specified, extra arguments are treated as a command that is
    executed with the running emulator. Without a command, the emulator runs
    until interrupted.

    \b
    ./prodtest_emu.py -m t3w1 -c pytest ../tests/prodtest_tests
    TREZOR_MODEL=t3w1 ./prodtest_emu.py
    """
    if command and not run_command:
        raise click.ClickException("Extra arguments found. Did you mean to use -c?")

    logger = logging.getLogger("trezorlib._internal")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    with tempfile.TemporaryDirectory(prefix="prodtest_emu_") as profile_dir:
        emulator = get_prodtest_emulator(
            model=model, profile_dir=profile_dir, headless=headless
        )
        with emulator:
            emulator.start()
            click.echo(f"VCP_PORT={emulator.vcp_port}")
            if run_command:
                process = subprocess.Popen(command)
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                returncode = process.wait()
            else:
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                returncode = emulator.wait()

    sys.exit(returncode)


if __name__ == "__main__":
    cli()
