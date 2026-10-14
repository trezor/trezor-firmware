#!/usr/bin/env python3
from __future__ import annotations

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
@click.option("-m", "--model", envvar="TREZOR_MODEL", required=True, help="Trezor model name (or set TREZOR_MODEL)")
# fmt: on
@click.argument("command", nargs=-1, type=click.UNPROCESSED)
def cli(model: str, command: list[str]) -> None:
    """Run a command with the prodtest emulator.

    \b
    ./prodtest_emu.py -m t3w1 pytest ../tests/prodtest_tests
    TREZOR_MODEL=t3w1 ./prodtest_emu.py pytest ../tests/prodtest_tests
    """
    with tempfile.TemporaryDirectory(prefix="prodtest_emu_") as profile_dir:
        emulator = get_prodtest_emulator(model=model, profile_dir=profile_dir)
        with emulator:
            emulator.start()
            process = subprocess.Popen(command)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            returncode = process.wait()

    sys.exit(returncode)


if __name__ == "__main__":
    cli()
