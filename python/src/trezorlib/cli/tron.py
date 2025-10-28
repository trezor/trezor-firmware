from typing import TYPE_CHECKING

import click

from .. import tools, tron
from . import with_session

if TYPE_CHECKING:
    from ..transport.session import Session

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
@with_session
def get_address(
    session: "Session", address: str, show_display: bool, chunkify: bool
) -> str:
    """Get Tron address"""
    address_n = tools.parse_path(address)
    return tron.get_address(session, address_n, show_display, chunkify)
