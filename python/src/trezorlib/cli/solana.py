from typing import TYPE_CHECKING

import click

from .. import messages, solana, tools
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient

PATH_HELP = "BIP-32 path to key, e.g. m/44h/501h/0h/0h"
DEFAULT_PATH = "m/44h/501h/0h/0h"


@click.group(name="solana")
def cli() -> None:
    """Solana commands."""


@cli.command()
@click.option("-n", "--address", default=DEFAULT_PATH, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_public_key(
    client: "TrezorClient",
    address: str,
    show_display: bool,
) -> messages.SolanaPublicKey:
    """Get Solana public key."""
    address_n = tools.parse_path(address)
    return solana.get_public_key(client, address_n, show_display)


@cli.command()
@click.option("-n", "--address", default=DEFAULT_PATH, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.option("-C", "--chunkify", is_flag=True)
@with_client
def get_address(
    client: "TrezorClient",
    address: str,
    show_display: bool,
    chunkify: bool,
) -> messages.SolanaAddress:
    """Get Solana address."""
    address_n = tools.parse_path(address)
    return solana.get_address(client, address_n, show_display, chunkify)


@cli.command()
@click.argument("serialized_tx", type=str)
@click.option("-n", "--address", default=DEFAULT_PATH, help=PATH_HELP)
@with_client
def sign_tx(
    client: "TrezorClient",
    address: str,
    serialized_tx: str,
) -> messages.SolanaTxSignature:
    """Sign Solana transaction."""
    address_n = tools.parse_path(address)
    return solana.sign_tx(client, address_n, bytes.fromhex(serialized_tx))
