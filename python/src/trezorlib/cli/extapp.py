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
    from ..transport.session import Session

LOG = logging.getLogger(__name__)


@click.group(name="extapp")
def cli() -> None:
    """External application commands - load and run external apps."""


@cli.command()
@click.argument(
    "tapp_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
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
    tapp_file: Path,
    match_fingerprint: bool,
) -> None:
    """Load an external application onto the device.

    TAPP_FILE is the serialized app produced by the app build. Its proof is
    expected next to it with a '.proof' suffix, and the root packets in the
    'root-packets' directory at the root of the serialized artifacts tree
    ('<root>/<app_id>/<version>/<app>.tapp').

    Example:
        trezorctl extapp load --min-version 0.1 serialized/ethereum.trezor.com/0.1.0.0/ethereum.trezor.com_0.1.0.0_sdk0.1_armv8m_abi1_T3W1_en.tapp
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

        instance_id = extapp.load_tapp(
            session,
            tapp_file,
            min_version=version,
            match_fingerprint=match_fingerprint,
        )
        click.echo(f"Application ready with instance ID: {instance_id}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
