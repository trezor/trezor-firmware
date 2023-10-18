# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

from typing import TYPE_CHECKING, Tuple

import click

from .. import misc, tools
from . import ChoiceType, with_client

if TYPE_CHECKING:
    from ..client import TrezorClient


PROMPT_TYPE = ChoiceType(
    {
        "always": (True, True),
        "never": (False, False),
        "decrypt": (False, True),
        "encrypt": (True, False),
    }
)


@click.group(name="crypto")
def cli() -> None:
    """Miscellaneous cryptography features."""


@cli.command()
@click.argument("size", type=int)
@with_client
def get_entropy(client: "TrezorClient", size: int) -> str:
    """Get random bytes from device."""
    return misc.get_entropy(client, size).hex()


@cli.command()
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/10016h/0")
@click.option(
    "-p", "--prompt", type=PROMPT_TYPE, default="always", help="Prompt for passphrase"
)
@click.argument("key")
@click.argument("value")
@with_client
def encrypt_keyvalue(
    client: "TrezorClient",
    address: str,
    key: str,
    value: str,
    prompt: Tuple[bool, bool],
) -> str:
    """Encrypt value by given key and path.

    The `prompt` option controls whether the device will prompt for confirmation on
    encrypting and decrypting the value. The default is to prompt for both encryption
    and decryption.

    You must provide the same `prompt` option to the `decrypt-keyvalue` command,
    otherwise the decryption will fail.
    """
    ask_on_encrypt, ask_on_decrypt = prompt
    address_n = tools.parse_path(address)
    return misc.encrypt_keyvalue(
        client,
        address_n,
        key,
        value.encode(),
        ask_on_encrypt=ask_on_encrypt,
        ask_on_decrypt=ask_on_decrypt,
    ).hex()


@cli.command()
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/10016h/0")
@click.option(
    "-p", "--prompt", type=PROMPT_TYPE, default="always", help="Prompt for passphrase"
)
@click.argument("key")
@click.argument("value")
@with_client
def decrypt_keyvalue(
    client: "TrezorClient",
    address: str,
    key: str,
    value: str,
    prompt: Tuple[bool, bool],
) -> bytes:
    """Decrypt value by given key and path.

    The `prompt` option controls whether the device will prompt for confirmation on
    encrypting and decrypting the value. The default is to prompt for both encryption
    and decryption.

    You must use the same `prompt` value that you used for encryption, otherwise the
    decryption will fail. I.e., it is not possible to encrypt with "--prompt=decrypt"
    and decrypt with "--prompt=never".
    """
    ask_on_encrypt, ask_on_decrypt = prompt
    address_n = tools.parse_path(address)
    return misc.decrypt_keyvalue(
        client,
        address_n,
        key,
        bytes.fromhex(value),
        ask_on_encrypt=ask_on_encrypt,
        ask_on_decrypt=ask_on_decrypt,
    )
