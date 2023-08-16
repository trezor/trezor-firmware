from typing import TYPE_CHECKING

import click

from .. import messages, solana, tools
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient

PATH_HELP = "BIP-32 path to key, e.g. m/44'/501'/0'"


@click.group(name="solana")
def cli() -> None:
    """Solana commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@with_client
def get_public_key(
    client: "TrezorClient",
    address: str,
) -> messages.SolanaPublicKey:
    """Get Solana public key."""
    address_n = tools.parse_path(address)
    client.init_device()
    return solana.get_public_key(client, address_n)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_address(
    client: "TrezorClient",
    address: str,
    show_display: bool,
) -> messages.SolanaAddress:
    """Get Solana public key."""
    address_n = tools.parse_path(address)
    client.init_device()
    return solana.get_address(client, address_n, show_display)


@cli.command()
@click.option("-n", "--signer-path", required=True, help=PATH_HELP)
@click.option("-t", "--serialized-tx", required=True)
@with_client
def sign_tx(
    client: "TrezorClient",
    signer_path: str,
    serialized_tx: str,
) -> messages.SolanaSignedTx:
    """Sign Solana transaction."""
    signer_path_n = tools.parse_path(signer_path)
    client.init_device()
    return solana.sign_tx(client, signer_path_n, bytes.fromhex(serialized_tx))


@cli.command()
@click.option("-n", "--signer-path", required=True, help=PATH_HELP)
@click.option("-m", "--serialized-message", required=True)
@with_client
def sign_off_chain_message(
    client: "TrezorClient",
    signer_path: str,
    serialized_message: str,
) -> messages.SolanaSignedTx:
    """Sign Solana off-chain message."""
    signer_path_n = tools.parse_path(signer_path)
    client.init_device()
    return solana.sign_off_chain_message(client, signer_path_n, bytes.fromhex(serialized_message))
