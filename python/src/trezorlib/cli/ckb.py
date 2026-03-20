"""CKB (Nervos Network) CLI commands."""

import click
from typing import TYPE_CHECKING

from .. import ckb, tools
from . import with_session

if TYPE_CHECKING:
    from ..transport.session import Session


PATH_HELP = "BIP-32 path, e.g. m/44'/309'/0'/0/0"


@click.group(name="ckb")
def cli() -> None:
    """CKB (Nervos Network) commands."""


@cli.command()
@click.option(
    "-n", "--address", default=ckb.DEFAULT_BIP32_PATH, help=PATH_HELP
)
@click.option("-d", "--show-display", is_flag=True)
@click.option(
    "--coin",
    type=click.Choice(["Mainnet", "Testnet"]),
    required=True,
    help="Network: Mainnet or Testnet",
)
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def get_address(
    session: "Session",
    address: str,
    show_display: bool,
    coin: str,
    chunkify: bool,
) -> str:
    """Get CKB address for specified path."""
    address_n = tools.parse_path(address)
    return ckb.get_address(
        session,
        address_n,
        show_display=show_display,
        network=coin,
        chunkify=chunkify,
    )
