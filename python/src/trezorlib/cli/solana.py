from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional, TextIO

import click

from .. import definitions, messages, solana, tools
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


def _get_token(token: str | None) -> bytes | None:
    if token is None:
        return None
    token_file = Path(token)
    if token_file.is_file():
        return token_file.read_bytes()
    try:
        return bytes.fromhex(token)
    except ValueError:
        source = definitions.UrlSource()
        return source.get_solana_token(token)


@cli.command()
@click.argument("serialized_tx", type=str)
@click.option("-n", "--address", default=DEFAULT_PATH, help=PATH_HELP)
@click.option("-a", "--additional-info", type=click.File("r"))
@click.option("-t", "--token", type=str)
@with_session
def sign_tx(
    session: "Session",
    address: str,
    serialized_tx: str,
    additional_info: Optional[TextIO],
    token: str | None,
) -> str:
    """Sign Solana transaction.

    The transaction is specified as a hex string.

    The `--token` option can be used to provide a signed token definition. One of the
    following can be provided:

    \b
    - path to a local file with a signed token definition
    - token definition encoded as a hex string
    - base58-encoded token mint account, which will be fetched from the data.trezor.io

    Alternately, the token can be included in the additional information as a hex string.
    """
    address_n = tools.parse_path(address)

    token_account_infos_json = ()
    if additional_info:
        decoded = json.load(additional_info)
        token_account_infos_json = decoded.get("token_accounts_infos", ())
        if token is None:
            token = decoded.get("token")

    additional_info_msg = messages.SolanaTxAdditionalInfo(
        token_accounts_infos=[
            messages.SolanaTxTokenAccountInfo(
                base_address=token_account["base_address"],
                token_program=token_account["token_program"],
                token_mint=token_account["token_mint"],
                token_account=token_account["token_account"],
            )
            for token_account in token_account_infos_json
        ],
        encoded_token=_get_token(token),
    )

    signature = solana.sign_tx(
        session,
        address_n,
        bytes.fromhex(serialized_tx),
        additional_info_msg,
    )
    return signature.hex()
