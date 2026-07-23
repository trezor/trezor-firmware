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

import base64
import sys
from typing import TYPE_CHECKING, Optional

import click

from .. import stellar, tools
from . import with_session

if TYPE_CHECKING:
    from ..client import Session

try:
    from stellar_sdk import (
        FeeBumpTransactionEnvelope,
        parse_transaction_envelope_from_xdr,
    )
    from stellar_sdk import xdr as stellar_xdr
except ImportError:
    pass

PATH_HELP = "BIP32 path. Always use hardened paths and the m/44h/148h/ prefix"


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
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def get_address(
    session: "Session", address: str, show_display: bool, chunkify: bool
) -> str:
    """Get Stellar public address."""
    address_n = tools.parse_path(address)
    return stellar.get_address(session, address_n, show_display, chunkify)


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
@with_session
def sign_transaction(
    session: "Session", b64envelope: str, address: str, network_passphrase: str
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
    tx, operations, tx_ext = stellar.from_envelope(envelope)
    resp = stellar.sign_tx(
        session, tx, operations, tx_ext, address_n, network_passphrase
    )

    return base64.b64encode(resp.signature)


@cli.command()
@click.option(
    "-n",
    "--address",
    required=False,
    help=PATH_HELP,
    default=stellar.DEFAULT_BIP32_PATH,
)
@click.option(
    "-p",
    "--network-passphrase",
    default=stellar.DEFAULT_NETWORK_PASSPHRASE,
    required=False,
    help="Network passphrase (blank for public network).",
)
@click.option(
    "-l",
    "--valid-until-ledger",
    type=int,
    default=None,
    help="Override the entry's signature_expiration_ledger "
    "(the last ledger sequence at which the authorization is valid).",
)
@click.argument("b64entry")
@with_session
def sign_soroban_authorization(
    session: "Session",
    b64entry: str,
    address: str,
    network_passphrase: str,
    valid_until_ledger: Optional[int],
) -> bytes:
    """Sign a base64-encoded Soroban authorization entry.

    Takes an unsigned SorobanAuthorizationEntry XDR with
    SOROBAN_CREDENTIALS_ADDRESS_V2 credentials (Protocol 27) and returns the
    base64-encoded signature of its authorization payload. The signed payload
    commits to the entry's signature_expiration_ledger; it must already be
    set to the intended value, or overridden with --valid-until-ledger.
    """
    if not stellar.HAVE_STELLAR_SDK:
        click.echo("Stellar requirements not installed.")
        click.echo("Please run:")
        click.echo()
        click.echo("  pip install stellar-sdk")
        sys.exit(1)
    if not stellar.HAVE_STELLAR_SDK_PROTOCOL_27:
        click.echo("Signing authorization entries requires Protocol 27 support.")
        click.echo("Please run:")
        click.echo()
        click.echo("  pip install 'stellar-sdk>=15'")
        sys.exit(1)
    try:
        entry_xdr = stellar_xdr.SorobanAuthorizationEntry.from_xdr(b64entry)
    except Exception as e:
        click.echo(
            f"Failed to parse XDR: {e}\n"
            "Make sure to pass a valid SorobanAuthorizationEntry object.\n"
        )
        sys.exit(1)

    if (
        entry_xdr.credentials.type
        != stellar_xdr.SorobanCredentialsType.SOROBAN_CREDENTIALS_ADDRESS_V2
    ):
        click.echo(
            f"Unsupported SorobanCredentials type: {entry_xdr.credentials.type}."
        )
        click.echo("Only SOROBAN_CREDENTIALS_ADDRESS_V2 entries can be signed.")
        sys.exit(1)

    address_n = tools.parse_path(address)
    authorization = stellar.from_authorization_entry(entry_xdr)
    if valid_until_ledger is not None:
        authorization.signature_expiration_ledger = valid_until_ledger
    resp = stellar.sign_soroban_authorization(
        session,
        address_n,
        network_passphrase,
        authorization,
    )
    return base64.b64encode(resp.signature)
