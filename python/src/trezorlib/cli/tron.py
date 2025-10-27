from typing import TYPE_CHECKING

import click

from .. import tools, tron
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient

PATH_HELP = "BIP-32 path to key, e.g. m/44h/195h/0h/0/0"


@click.group(name="tron")
def cli() -> None:
    """Tron commands."""


@cli.command()
@click.option(
    "-n",
    "--address",
    required=False,
    help=PATH_HELP,
    default=tron.DEFAULT_BIP32_PATH,
)
@click.option("-d", "--show-display", is_flag=True)
@click.option("-C", "--chunkify", is_flag=True)
@with_client
def get_address(
    client: "TrezorClient", address: str, show_display: bool, chunkify: bool
) -> str:
    """Get Tron address"""
    address_n = tools.parse_path(address)
    return tron.get_address(client, address_n, show_display, chunkify)


@cli.command()
@click.option(
    "-n",
    "--address",
    required=False,
    help=PATH_HELP,
    default=tron.DEFAULT_BIP32_PATH,
)
@click.argument("raw_data_hex", type=str)
@with_client
def sign_tx(client: "TrezorClient", raw_data_hex: str, address: str) -> str:
    """Sign a raw transaction."""

    raw_data = bytes.fromhex(raw_data_hex)
    tx, contract = tron.from_raw_data(raw_data)
    address_n = tools.parse_path(address)
    signed_tx = tron.sign_tx(client, tx, contract, address_n)

    return signed_tx.signature.hex()
