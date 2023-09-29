import click

from .. import solana, messages, tools
from . import with_client

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
) -> messages.SolanaPublicKey:
    """Get Solana public key."""
    address_n = tools.parse_path(address)
    client.init_device()
    return solana.get_address(client, address_n, show_display)
