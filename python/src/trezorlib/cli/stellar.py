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

import base64
import sys
from typing import TYPE_CHECKING

import click

from .. import stellar, tools
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient

try:
    from stellar_sdk import (
        parse_transaction_envelope_from_xdr,
        FeeBumpTransactionEnvelope,
    )
except ImportError:
    pass

PATH_HELP = "BIP32 path. Always use hardened paths and the m/44'/148'/ prefix"


@click.group(name="stellar")
def cli() -> None:
    """Stellar commands."""


@cli.command()
@click.option(
    "-n",
    "--address",
    required=False,
    help=PATH_HELP,
    default=stellar.DEFAULT_BIP32_PATH,
)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_address(client: "TrezorClient", address: str, show_display: bool) -> str:
    """Get Stellar public address."""
    address_n = tools.parse_path(address)
    return stellar.get_address(client, address_n, show_display)


@cli.command()
@click.option(
    "-n",
    "--address",
    required=False,
    help=PATH_HELP,
    default=stellar.DEFAULT_BIP32_PATH,
)
@click.option(
    "-n",
    "--network-passphrase",
    default=stellar.DEFAULT_NETWORK_PASSPHRASE,
    required=False,
    help="Network passphrase (blank for public network).",
)
@click.argument("b64envelope")
@with_client
def sign_transaction(
    client: "TrezorClient", b64envelope: str, address: str, network_passphrase: str
) -> bytes:
    """Sign a base64-encoded transaction envelope.

    For testnet transactions, use the following network passphrase:
    'Test SDF Network ; September 2015'
    """
    if not stellar.HAVE_STELLAR_SDK:
        click.echo("Stellar requirements not installed.")
        click.echo("Please run:")
        click.echo()
        click.echo("  pip install stellar-sdk")
        sys.exit(1)
    try:
        envelope = parse_transaction_envelope_from_xdr(b64envelope, network_passphrase)
    except Exception:
        click.echo(
            "Failed to parse XDR.\n"
            "Make sure to pass a valid TransactionEnvelope object.\n"
            "You can check whether the data you submitted is valid TransactionEnvelope object "
            "through XDRViewer - https://laboratory.stellar.org/#xdr-viewer\n"
        )
        sys.exit(1)

    if isinstance(envelope, FeeBumpTransactionEnvelope):
        click.echo("FeeBumpTransactionEnvelope is not supported")
        sys.exit(1)

    address_n = tools.parse_path(address)
    tx, operations = stellar.from_envelope(envelope)
    resp = stellar.sign_tx(client, tx, operations, address_n, network_passphrase)

    return base64.b64encode(resp.signature)
