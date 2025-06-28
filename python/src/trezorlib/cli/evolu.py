# This file is part of the Trezor project.
#
# Copyright (C) 2012-2025 SatoshiLabs and contributors
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

import typing as t

import click

from .. import evolu, messages
from . import with_client

if t.TYPE_CHECKING:
    from ..client import TrezorClient


@click.group(name="evolu")
def cli() -> None:
    """Evolu commands."""


@cli.command()
@with_client
def get_keys(
    client: "TrezorClient",
) -> dict[str, str]:
    """Return the SLIP-21 Evolu keys."""

    keys: messages.EvoluKeys = evolu.get_evolu_keys(
        client,
    )
    return {
        "owner_id": keys.owner_id.hex(),
        "write_key": keys.write_key.hex(),
        "encryption_key": keys.encryption_key.hex(),
    }
