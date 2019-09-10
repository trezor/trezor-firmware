# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

import click

from .. import misc, tools


@click.group(name="crypto")
def cli():
    """Miscellaneous cryptography features."""


@cli.command()
@click.argument("size", type=int)
@click.pass_obj
def get_entropy(connect, size):
    """Get random bytes from device."""
    return misc.get_entropy(connect(), size).hex()


@cli.command()
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/10016'/0")
@click.argument("key")
@click.argument("value")
@click.pass_obj
def encrypt_keyvalue(connect, address, key, value):
    """Encrypt value by given key and path."""
    client = connect()
    address_n = tools.parse_path(address)
    res = misc.encrypt_keyvalue(client, address_n, key, value.encode())
    return res.hex()


@cli.command()
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/10016'/0")
@click.argument("key")
@click.argument("value")
@click.pass_obj
def decrypt_keyvalue(connect, address, key, value):
    """Decrypt value by given key and path."""
    client = connect()
    address_n = tools.parse_path(address)
    return misc.decrypt_keyvalue(client, address_n, key, bytes.fromhex(value))
