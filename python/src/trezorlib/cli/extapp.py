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
    "app_path", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@with_session()
def load(session: "Session", app_path: Path) -> None:
    """Load an external application onto the device.

    Example:
        trezorctl extapp load ./sdk/apps/funnycoin-rust/target/debug/libfunnycoin_rust.so
    """
    try:
        app_bytes = app_path.read_bytes()
        app_hash = extapp.load(session, app_bytes)
        click.echo(f"Loaded app hash: {app_hash:064x}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
