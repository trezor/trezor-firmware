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

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional, TextIO

import click

from .. import definitions, messages, solana, tools
from . import with_session

if TYPE_CHECKING:
    from ..client import Session

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


DEFAULT_APP_DOMAIN = b"\x00" * solana.OffchainMessageV0.APP_LEN


@cli.command()
@click.argument("message", type=str)
@click.option("-n", "--address", default=DEFAULT_PATH, help=PATH_HELP)
@click.option("-t", "--text", is_flag=True, help="Interpret message as text")
@click.option("-a", "--app", type=str, help="Application domain (base58, 32 B)")
@click.option(
    "-s",
    "--signer",
    type=str,
    multiple=True,
    help="Public key of an additional signer (base58)",
)
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def sign_message(
    session: "Session",
    address: str,
    message: str,
    text: bool,
    app: str | None,
    signer: tuple[str, ...],
    chunkify: bool,
) -> str:
    """Sign a Solana off-chain message.

    There are two ways to specify the MESSAGE argument:

    1. Raw mode (Default)

    sign-message [--address PATH] MESSAGE

    The provided MESSAGE is treated as a hex string representing a
    pre-formatted off-chain message. Only the --address option is
    allowed in this mode [1]. The specified address must correspond
    to one of the public keys in the message.

    2. Format mode

    sign-message [--address PATH] [--app APP] [--signer SIGNER]... --text MESSAGE

    The provided MESSAGE is treated as a plain text string. The
    formatted message will be constructed based on the supplied
    arguments. The --signer option can be used multiple times. The
    final list of signers will consist of the public key derived
    from --address, plus any public keys provided via --signer.

    Also see: https://docs.anza.xyz/proposals/off-chain-message-signing

    [1] The --chunkify flag is always applicable.
    """

    address_n = tools.parse_path(address)

    if text:
        app_bytes = tools.b58decode(app) if app else DEFAULT_APP_DOMAIN

        signers = [solana.get_public_key(session, address_n, show_display=False)]
        signers.extend(tools.b58decode(s) for s in signer)

        offchain_msg = solana.OffchainMessageV0(app_bytes, signers, message).to_bytes()
    else:
        if app or signer:
            raise click.UsageError("Only the --address option can be used in raw mode")

        offchain_msg = bytes.fromhex(message)

    click.echo(f"Message: {offchain_msg.hex()}")

    signature = solana.sign_message(session, address_n, offchain_msg, chunkify=chunkify)
    return signature.hex()


@cli.command()
@click.argument("message", type=str)
@click.option("-s", "--signature", type=str, multiple=True, help="Signature (hex)")
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def verify_message(
    session: "Session",
    message: str,
    signature: tuple[str, ...],
    chunkify: bool,
) -> bool:
    """Verify a signed Solana off-chain message.

    This command operates in two modes depending on whether the
    --signature option is provided; in either case, the provided MESSAGE
    must be a hex string:

    If the --signature option is not used, the provided MESSAGE must
    be wrapped in an envelope containing signatures from all signers
    specified in the message header.

    If the --signature option is used, the provided MESSAGE must be a
    pre-formatted off-chain message without an envelope. You must provide
    all signatures in the correct order as specified by the message header
    (by using the --signature option multiple times if necessary). The
    envelope will be constructed automatically.

    Also see: https://docs.anza.xyz/proposals/off-chain-message-signing#envelope
    """

    if signature:
        signatures = [bytes.fromhex(s) for s in signature]
        msg_bytes = bytes.fromhex(message)
        envelope = solana.Envelope(signatures, msg_bytes).to_bytes()
    else:
        envelope = bytes.fromhex(message)

    return solana.verify_message(session, envelope, chunkify=chunkify)
