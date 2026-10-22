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
from trezorlib._internal.prodtest_emulator import (
    ProdtestEmulator,
    get_prodtest_emulator,
)

HERE = Path(__file__).resolve().parent
TROPIC_MODEL_CONFIG = (
    HERE.parent / "tests" / "tropic_model" / "firmware_config" / "current.yml"
)

PROFILE_BASE = Path.home() / ".trezoremu"


@click.command(
    context_settings=dict(ignore_unknown_options=True, allow_interspersed_args=False)
)
@click.option(
    "-m",
    "--model",
    envvar="TREZOR_MODEL",
    default=None,
    help="Trezor model name (or set TREZOR_MODEL); defaults to the latest build",
)
@click.option(
    "-c",
    "--command",
    "run_command",
    is_flag=True,
    help="Run command while emulator is running",
)
@click.option("-e", "--erase", is_flag=True, help="Erase profile before running")
@click.option("-h", "--headless", is_flag=True, help="Headless mode (no display)")
@click.option(
    "-p",
    "--profile",
    metavar="NAME",
    help="Profile name or path (persistent; overrides --temporary-profile)",
)
@click.option(
    "-t",
    "--temporary-profile/--no-temporary-profile",
    default=True,
    help="Create an empty temporary profile",
)
@click.option(
    "--tropic-emulator/--no-tropic-emulator",
    default=None,
    help="Start a TROPIC01 model",
)
@click.option(
    "--tropic-emulator-config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=TROPIC_MODEL_CONFIG,
    help="TROPIC01 model configuration file",
)
@click.option(
    "--tropic-model-port",
    type=int,
    default=None,
    help="Port of the TROPIC01 model. Defaults to a free port for the auto-started model, or to 28992 for an externally managed one (--no-tropic-emulator).",
)
@click.argument("command", nargs=-1, type=click.UNPROCESSED)
def cli(
    model: str | None,
    run_command: bool,
    erase: bool,
    headless: bool,
    profile: str | None,
    temporary_profile: bool,
    tropic_emulator: bool | None,
    tropic_emulator_config: Path,
    tropic_model_port: int | None,
    command: list[str],
) -> None:
    """Run the prodtest emulator.

    If -c is specified, extra arguments are treated as a command that is
    executed with the running emulator. Without a command, the emulator runs
    until interrupted.

    By default the emulator runs in an empty temporary profile, which is
    removed on exit. Use -p for a persistent profile instead.

    ./prodtest_emu.py -m t3w1 -c pytest ../tests/prodtest_tests
    TREZOR_MODEL=t3w1 ./prodtest_emu.py
    """
    if command and not run_command:
        raise click.ClickException("Extra arguments found. Did you mean to use -c?")

    logger = logging.getLogger("trezorlib._internal")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    tempdir = None
    if profile:
        if "/" in profile:
            profile_dir = Path(profile)
        else:
            profile_dir = PROFILE_BASE / profile
        profile_dir.mkdir(parents=True, exist_ok=True)
    elif temporary_profile:
        tempdir = tempfile.TemporaryDirectory(prefix="prodtest_emu_")
        profile_dir = Path(tempdir.name)
    elif "TREZOR_PROFILE_DIR" in os.environ:
        profile_dir = Path(os.environ["TREZOR_PROFILE_DIR"])
    else:
        raise click.ClickException(
            "No profile: use -p or TREZOR_PROFILE_DIR with --no-temporary-profile."
        )

    if erase:
        (profile_dir / ProdtestEmulator.STORAGE_FILENAME).unlink(missing_ok=True)

    emulator = get_prodtest_emulator(
        model=model,
        profile_dir=str(profile_dir),
        headless=headless,
        tropic_model_port=tropic_model_port,
    )

    tropic_model = None
    tropic_emulator_needed = tropic_emulator
    if tropic_emulator_needed is None:
        tropic_emulator_needed = emulator.properties().get("tropic", False)
    if tropic_emulator_needed:
        tropic_model = TropicModel(
            profile_dir=str(profile_dir),
            configfile=tropic_emulator_config,
            port=tropic_model_port,
        )
        try:
            tropic_model.start()
        except Exception as exc:
            raise click.ClickException(
                f"Failed to start the TROPIC01 model: {exc.__class__.__name__}: {exc}. "
                "Use --no-tropic-emulator to point the emulator at an external model."
            )
        emulator.tropic_model_port = tropic_model.port

    with emulator:
        emulator.start()
        click.echo(f"VCP_PORT={emulator.vcp_port}")
        if tropic_emulator is not None or tropic_emulator_needed:
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
            click.echo(
                f"Error stopping Tropic01 model: {exc.__class__.__name__}: {exc}",
                err=True,
            )

    if tempdir is not None:
        tempdir.cleanup()
    sys.exit(returncode)


if __name__ == "__main__":
    cli()
