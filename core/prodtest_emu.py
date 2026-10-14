#!/usr/bin/env python3
from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

import click

from trezorlib._internal.emulator import TropicModel
from trezorlib._internal.prodtest_emulator import get_prodtest_emulator

HERE = Path(__file__).resolve().parent
TROPIC_MODEL_CONFIG = (
    HERE.parent / "tests" / "tropic_model" / "firmware_config" / "current.yml"
)


@click.command(
    context_settings=dict(ignore_unknown_options=True, allow_interspersed_args=False)
)
# fmt: off
@click.option("-m", "--model", envvar="TREZOR_MODEL", default=None, help="Trezor model name (or set TREZOR_MODEL); defaults to the latest build")
@click.option("-c", "--command", "run_command", is_flag=True, help="Run command while emulator is running")
@click.option("-h", "--headless", is_flag=True, help="Headless mode (no display)")
@click.option("--tropic-emulator/--no-tropic-emulator", default=True, help="Start a TROPIC01 model")
@click.option("--tropic-emulator-config", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=TROPIC_MODEL_CONFIG, help="TROPIC01 model configuration file")
@click.option("--tropic-model-port", type=int, default=None, help="Port of the TROPIC01 model. Defaults to a free port for the auto-started model, or to 28992 for an externally managed one (--no-tropic-emulator).")
# fmt: on
@click.argument("command", nargs=-1, type=click.UNPROCESSED)
def cli(
    model: str | None,
    run_command: bool,
    headless: bool,
    tropic_emulator: bool,
    tropic_emulator_config: Path,
    tropic_model_port: int | None,
    command: list[str],
) -> None:
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

    tropic_model = None
    with tempfile.TemporaryDirectory(prefix="prodtest_emu_") as profile_dir:
        if tropic_emulator:
            tropic_model = TropicModel(
                profile_dir=profile_dir,
                configfile=tropic_emulator_config,
                port=tropic_model_port,
            )
            try:
                tropic_model.start()
                tropic_model_port = tropic_model.port
            except Exception as exc:
                click.echo(f"Failed to start Tropic01 model: {exc.__class__.__name__}: {exc}", err=True)

        emulator = get_prodtest_emulator(
            model=model,
            profile_dir=profile_dir,
            headless=headless,
            tropic_model_port=tropic_model_port,
        )
        with emulator:
            emulator.start()
            click.echo(f"VCP_PORT={emulator.vcp_port}")
            click.echo(f"TROPIC_MODEL_PORT={emulator.tropic_model_port}")
            os.environ["TROPIC_MODEL_PORT"] = str(emulator.tropic_model_port)
            if run_command:
                process = subprocess.Popen(command)
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                returncode = process.wait()
            else:
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                returncode = emulator.wait()

        if tropic_model:
            try:
                tropic_model.stop()
            except Exception as exc:
                click.echo(f"Error stopping Tropic01 model: {exc.__class__.__name__}: {exc}", err=True)

    sys.exit(returncode)


if __name__ == "__main__":
    cli()
