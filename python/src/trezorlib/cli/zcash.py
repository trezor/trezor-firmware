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

from .. import zcash, tools
from . import ChoiceType, with_client

NETWORKS = {
    "mainnet": "Zcash",
    "testnet": "Zcash Testnet",
}


@click.group(name="zcash")
def cli():
    """Zcash commands."""


@cli.command()
@click.option("-z", "--z-address", help="ZIP-32 Orchard derivation path.")
@click.option("-w", "--network", type=ChoiceType(NETWORKS), default="mainnet")
@click.option('-f', '--full', is_flag=True, help="Return **Full** Vieving Key.")
@with_client
def get_viewing_key(client, z_address, network, full):
    """
    Get Zcash Unified Incoming Key.

    Use --full flag to return **Full** Viewing Key.
    **Incoming** Viewing Key is returned otherwise.

    Example:
    --------
    $ trezorctl zcash get-viewing-key -f -z m/32h/133h/0h
    """
    return zcash.get_viewing_key(client, tools.parse_path(z_address), network, full)


@cli.command()
@click.option("-t", "--t-address", help="BIP-32 path of a P2PKH transparent address.")
@click.option("-z", "--z-address", help="ZIP-32 Orchard derivation path.")
@click.option("-j", "--diversifier-index", default=0, type=int, help="diversifier index of the shielded address.")
@click.option("-d", "--show-display", is_flag=True)
@click.option("-w", "--network", type=ChoiceType(NETWORKS), default="mainnet")
@with_client
def get_address(client, t_address, z_address, diversifier_index, show_display, network):
    """
    Get Zcash address.

    Example:
    --------
    $ trezorctl zcash get-address -d -t m/44h/133h/0h/0/0 -z m/32h/133h/0h -j 0
    """
    if not t_address and not z_address:
        raise click.ClickException((
            "Specify address path using -t (transparent) and -z (shielded) arguments.\n"
            "You can use both to get Zcash unified address."
        ))

    kwargs = {}
    kwargs["show_display"] = show_display
    if t_address:
        kwargs["t_address_n"] = tools.parse_path(t_address)
    if z_address:
        kwargs["z_address_n"] = tools.parse_path(z_address)
        kwargs["diversifier_index"] = diversifier_index

    kwargs["coin_name"] = network

    try:
        return zcash.get_address(client, **kwargs)
    except ValueError as e:
        return str(e)
