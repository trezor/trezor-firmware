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

from .. import zcash, messages, tools
from . import with_client

@click.group(name="zcash")
def cli():
    """Zcash commands."""

def is_ascii(s):
    return all(ord(c) < 128 for c in s)

@cli.command()
@click.option("-i", "--ins",  required=False, default="hello", help="Diagnostic instruction.")
@click.option("-d", "--data", required=False, default="", help="Diagnostic input data.")
@click.option("-a", "--ascii", is_flag=True, help="Parse data as ascii string.")
@with_client
def diag(client, ins, data, ascii):
    """Get Zcash diagnotic message."""
    if ascii:
        data = data.encode("ascii")
    else:
        data = bytes.fromhex(data)

    response = zcash.diag(client, ins.encode("ascii"), data)

    try:
        return response.decode("ascii")
    except:
        return response.hex()

@cli.command()
@click.option("-z", "--z-address", help="ZIP-32 path of an Orchard shielded address.")
@with_client
def get_fvk(client, z_address):
    """Get Zcash Orchard Full Incoming Key."""
    fvk = zcash.get_fvk(client, tools.parse_path(z_address))
    return fvk.hex()

@cli.command()
@click.option("-z", "--z-address", help="ZIP-32 path of an Orchard shielded address.")
@with_client
def get_ivk(client, z_address):
    """Get Zcash Orchard Incoming Viewing Key."""
    ivk = zcash.get_ivk(client, tools.parse_path(z_address))
    return ivk.hex()

@cli.command(help="""Example:\n
trezorctl zcash get-address -d -t m/44h/133h/0h/0/0 -z m/32h/133h/0h -j 0
""")
@click.option("-t", "--t-address", help="BIP-32 path of a P2PKH transparent address.")
@click.option("-z", "--z-address", help="ZIP-32 path of an Orchard shielded address.")
@click.option("-j", "--diversifier-index", default=0, type=int, help="diversifier index of the shielded address.")
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_address(client, t_address, z_address, diversifier_index, show_display):
    """Get Zcash address."""
    if not t_address and not z_address:
        return """Specify address path using -t (transparent) and -z (shielded) arguments.\nYou can use both to get Zcash unified address."""

    kwargs = dict()
    kwargs["show_display"] = show_display
    if t_address:
        kwargs["t_address_n"] = tools.parse_path(t_address)
    if z_address:
        kwargs["z_address_n"] = tools.parse_path(z_address)
        kwargs["diversifier_index"] = diversifier_index

    try:
        return zcash.get_address(client, **kwargs)
    except ValueError as e:
        return str(e)  