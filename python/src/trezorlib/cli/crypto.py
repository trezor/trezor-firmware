# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

from typing import TYPE_CHECKING

import click

from .. import misc, tools
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient


@click.group(name="crypto")
def cli() -> None:
    """Miscellaneous cryptography features."""


@cli.command()
@click.argument("size", type=int)
@with_client
def get_entropy(client: "TrezorClient", size: int) -> str:
    """Get random bytes from device."""
    return misc.get_entropy(client, size).hex()


@cli.command()
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/10016'/0")
@click.argument("key")
@click.argument("value")
@with_client
def encrypt_keyvalue(client: "TrezorClient", address: str, key: str, value: str) -> str:
    """Encrypt value by given key and path."""
    address_n = tools.parse_path(address)
    return misc.encrypt_keyvalue(client, address_n, key, value.encode()).hex()


@cli.command()
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/10016'/0")
@click.argument("key")
@click.argument("value")
@with_client
def decrypt_keyvalue(
    client: "TrezorClient", address: str, key: str, value: str
) -> bytes:
    """Decrypt value by given key and path."""
    address_n = tools.parse_path(address)
    return misc.decrypt_keyvalue(client, address_n, key, bytes.fromhex(value))
