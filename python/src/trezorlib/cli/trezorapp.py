# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

import logging
import sys
import typing as t
from pathlib import Path

import click

from .. import trezorapp
from . import with_session

if t.TYPE_CHECKING:
    from ..transport.session import Session

LOG = logging.getLogger(__name__)


@click.group(name="trezorapp")
def cli() -> None:
    """External application commands - load and run external apps."""


@cli.command()
@click.argument(
    "app_path", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.argument(
    "proof_path", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.argument(
    "root_packet_path", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--min-version",
    type=str,
    help="Minimum required version of the app in the format 'major.minor'.",
)
@click.option(
    "--force-reload",
    is_flag=True,
    default=False,
    help="Force reload of the app even if it is already loaded.",
)
@with_session()
def load(
    session: "Session",
    min_version: str | None,
    app_path: Path,
    proof_path: Path,
    root_packet_path: Path,
    force_reload: bool,
) -> None:
    """Load an external application onto the device.

    Example:
        trezorctl trezorapp load --min-version 0.1 ethereum.bin
    """
    try:
        version = None
        if min_version is not None:
            parts = tuple(map(int, min_version.split(".")))
            if len(parts) < 1 or len(parts) > 4:
                raise ValueError(
                    "Version must be in the format 'major[.minor[.patch[.build]]]'"
                )
            version = t.cast(
                t.Tuple[int, int, int, int], parts + (0,) * (4 - len(parts))
            )

        app_binary = app_path.read_bytes()
        proof = proof_path.read_bytes()
        root_packet = root_packet_path.read_bytes()
        instance_id = trezorapp.load(
            session,
            binary=app_binary,
            proof=proof,
            root_packet=root_packet,
            min_version=version,
            force_reload=force_reload,
        )
        click.echo(f"Application ready with instance ID: {instance_id}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
