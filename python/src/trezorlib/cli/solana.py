import json
from typing import TYPE_CHECKING, Optional, TextIO

import click

from .. import messages, solana, tools
from . import with_session

if TYPE_CHECKING:
    from ..transport.session import Session

PATH_HELP = "BIP-32 path to key, e.g. m/44h/501h/0h/0h"
DEFAULT_PATH = "m/44h/501h/0h/0h"


@click.group(name="solana")
def cli() -> None:
    """Solana commands."""


@cli.command()
@click.option("-n", "--address", default=DEFAULT_PATH, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_session
def get_public_key(
    session: "Session",
    address: str,
    show_display: bool,
) -> bytes:
    """Get Solana public key."""
    address_n = tools.parse_path(address)
    return solana.get_public_key(session, address_n, show_display)


@cli.command()
@click.option("-n", "--address", default=DEFAULT_PATH, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def get_address(
    session: "Session",
    address: str,
    show_display: bool,
    chunkify: bool,
) -> str:
    """Get Solana address."""
    address_n = tools.parse_path(address)
    return solana.get_address(session, address_n, show_display, chunkify)


@cli.command()
@click.argument("serialized_tx", type=str)
@click.option("-n", "--address", default=DEFAULT_PATH, help=PATH_HELP)
@click.option("-a", "--additional-information-file", type=click.File("r"))
@with_session
def sign_tx(
    session: "Session",
    address: str,
    serialized_tx: str,
    additional_information_file: Optional[TextIO],
) -> bytes:
    """Sign Solana transaction."""
    address_n = tools.parse_path(address)

    additional_information = None
    if additional_information_file:
        raw_additional_information = json.load(additional_information_file)
        additional_information = messages.SolanaTxAdditionalInfo(
            token_accounts_infos=[
                messages.SolanaTxTokenAccountInfo(
                    base_address=token_account["base_address"],
                    token_program=token_account["token_program"],
                    token_mint=token_account["token_mint"],
                    token_account=token_account["token_account"],
                )
                for token_account in raw_additional_information["token_accounts_infos"]
            ]
        )

    return solana.sign_tx(
        session,
        address_n,
        bytes.fromhex(serialized_tx),
        additional_information,
    )
