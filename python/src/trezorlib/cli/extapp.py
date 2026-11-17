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

from .. import extapp
from . import with_session

if t.TYPE_CHECKING:
    from ..client import Session

LOG = logging.getLogger(__name__)


def _select_app(app_dir: Path, app_id: str) -> tuple[Path, bytes]:
    """Pick the '{app_id}_*.tapp' in `app_dir` with the highest header version.

    If any image satisfies `--min-version`, the newest one does. Images whose
    header ID is not `app_id` (misnamed, or e.g. 'foo_bar_*' for 'foo') are skipped.
    """
    candidates = []
    for path in sorted(app_dir.glob(f"{app_id}_*.tapp")):
        binary = path.read_bytes()
        header = extapp.AppImage.parse(binary).header
        if header.id != app_id:
            click.echo(f"Warning: skipping {path.name}, its app ID is '{header.id}'")
            continue
        candidates.append((header.version, path, binary))
    if not candidates:
        raise ValueError(f"No app found for id '{app_id}' in {app_dir}")

    _, path, binary = max(candidates, key=lambda c: c[0])
    if len(candidates) > 1:
        click.echo(
            f"Warning: multiple versions found for '{app_id}', picked {path.name}"
        )
    return path, binary


@click.group(name="extapp")
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
    "--match-fingerprint",
    is_flag=True,
    default=False,
    help="Reload the app unless the installed one has the same fingerprint (header hash).",
)
@with_session()
def load(
    session: "Session",
    min_version: str | None,
    app_id: str,
    app_dir: Path,
    match_fingerprint: bool,
) -> None:
    """Load an external application onto the device.

    APP_ID is the application id and APP_DIR the directory holding the app,
    its proof and the root packets. The app binary is expected to be named
    '{app_id}_{version}.tapp' and its proof '{app_id}_{version}.proof'.

    Example:
        trezorctl extapp load --min-version 0.1 ethereum.trezor.com ./apps
    """
    try:
        version = None
        if min_version is not None:
            parts = tuple(map(int, min_version.split(".")))
            if len(parts) < 1 or len(parts) > 4:
                raise ValueError(
                    "Version must be in the format 'major[.minor[.patch[.build]]]'"
                )
            version = t.cast(tuple[int, int, int, int], parts + (0,) * (4 - len(parts)))

        app_path, app_binary = _select_app(app_dir, app_id)
        proof = app_path.with_suffix(".proof").read_bytes()

        # Pick the root packet based on the app ring stored in the app header:
        # ring 0 -> rootpacket_0, rings 1 and 2 -> rootpacket_12.
        app_ring = extapp.AppImage.parse(app_binary).header.app_ring
        root_packet_name = (
            "rootpacket_0-timestamped-signed.tmr"
            if app_ring == 0
            else "rootpacket_12-timestamped-signed.tmr"
        )
        root_packet = (app_dir / root_packet_name).read_bytes()

        instance_id = extapp.load(
            session,
            binary=app_binary,
            proof=proof,
            root_packet=root_packet,
            min_version=version,
            match_fingerprint=match_fingerprint,
        )
        click.echo(f"Application ready with instance ID: {instance_id}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
