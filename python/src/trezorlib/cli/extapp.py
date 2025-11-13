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
        app_hash = extapp.load(session, app_path)
        click.echo(f"Loaded app hash: {app_hash.hex()}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("app_hash", type=str)
@click.argument("fn_id", type=int)
@click.argument("data", type=str, default="")
@with_session()
def run(session: "Session", app_hash: str, fn_id: int, data: str) -> None:
    """Run an external application - starts IPC responder on device.

    APP_HASH: Hash of the loaded app (hex string)
    FN_ID: Function ID to invoke (integer)
    DATA: Function arguments as hex string

    Example:
        trezorctl extapp run abc123... 0 0102030405
    """
    try:
        hash_bytes = bytes.fromhex(app_hash)
        data_bytes = bytes.fromhex(data) if data else b""
        result = extapp.run(session, hash_bytes, fn_id, data_bytes)
        msg = getattr(result, "message", None) or ""
        result_data = getattr(result, "data", None)
        click.echo(f"Result: {msg}")
        if result_data:
            click.echo(f"Data: {result_data.hex()}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
