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
@click.argument("app_id", type=str)
@click.argument(
    "app_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
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
    app_id: str,
    app_dir: Path,
    force_reload: bool,
) -> None:
    """Load an external application onto the device.

    APP_ID is the application id and APP_DIR the directory holding the app,
    its proof and the root packets. The app binary is expected to be named
    '{app_id}_{version}.tapp' and its proof '{app_id}_{version}.proof'.

    Example:
        trezorctl trezorapp load --min-version 0.1 ethereum.trezor.com ./apps
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

        # Locate the app by its id only, matching '{app_id}_*.tapp' in the given directory.
        candidates = sorted(app_dir.glob(f"{app_id}_*.tapp"))
        if not candidates:
            raise ValueError(f"No app found for id '{app_id}' in {app_dir}")
        app_path = candidates[0]
        if len(candidates) > 1:
            click.echo(
                f"Warning: multiple versions found for '{app_id}', picked {app_path.name}"
            )
        proof_path = app_path.with_suffix(".proof")

        app_binary = app_path.read_bytes()
        proof = proof_path.read_bytes()

        # Pick the root packet based on the app ring stored in the app header:
        # ring 0 -> rootpacket_0, rings 1 and 2 -> rootpacket_12.
        app_ring = trezorapp.AppImage.parse(app_binary).header.app_ring
        root_packet_name = "rootpacket_0.tmr" if app_ring == 0 else "rootpacket_12.tmr"
        root_packet = (app_dir / root_packet_name).read_bytes()

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
