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

from typing import TYPE_CHECKING, Union

import click

from .. import misc, tools
from . import ChoiceType, with_session

if TYPE_CHECKING:
    from ..client import Session


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
@with_session
def get_entropy(session: "Session", size: int) -> str:
    """Get random bytes from device."""
    return misc.get_entropy(session, size).hex()


@cli.command()
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/10016h/0")
@click.option(
    "-p", "--prompt", type=PROMPT_TYPE, default="always", help="Prompt for passphrase"
)
@click.argument("key")
@click.argument("value")
@with_session
def encrypt_keyvalue(
    session: "Session",
    address: str,
    key: str,
    value: str,
    prompt: tuple[bool, bool],
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
        session,
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
@with_session
def decrypt_keyvalue(
    session: "Session",
    address: str,
    key: str,
    value: str,
    prompt: tuple[bool, bool],
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
        session,
        address_n,
        key,
        bytes.fromhex(value),
        ask_on_encrypt=ask_on_encrypt,
        ask_on_decrypt=ask_on_decrypt,
    )


@cli.command()
@click.option(
    "-n",
    "--address",
    required=True,
    help="BIP-85 derivation path, e.g. m/83696968h/39h/0h/12h/0h",
)
@click.option(
    "-d", "--show-display", is_flag=True, help="Show the derived secret on the device"
)
@click.option(
    "-D",
    "--on-device-only",
    is_flag=True,
    help="Only show the derived secret on the device, do not send it to the host",
)
@with_session
def get_bip85_entropy(
    session: "Session", address: str, show_display: bool, on_device_only: bool
) -> Union[dict[str, str], str]:
    """Derive deterministic entropy according to BIP-85.

    The full BIP-85 derivation path selects the application and its parameters:

    \b
    m/83696968h/39h/0h/{words}h/{index}h      BIP-39 mnemonic (12, 15, 18, 21 or 24 words)
    m/83696968h/2h/{index}h                   HD-Seed WIF
    m/83696968h/32h/{index}h                  Extended private key (xprv)
    m/83696968h/128169h/{bytes}h/{index}h     Raw entropy (16 to 64 bytes)
    m/83696968h/707764h/{length}h/{index}h    Base64 password (20 to 86 characters)
    m/83696968h/707785h/{length}h/{index}h    Base85 password (10 to 80 characters)

    For other applications the raw 64 bytes of BIP-85 entropy are returned.

    The derived secret gives full access to the child wallet or password. Use
    `--on-device-only` to view the secret on the device without it ever leaving
    the device.
    """
    address_n = tools.parse_path(address)
    result = misc.get_bip85_entropy(
        session, address_n, show_display=show_display, on_device_only=on_device_only
    )
    if on_device_only:
        return "The derived secret was shown on the device."

    output = {"entropy": (result.entropy or b"").hex()}
    if result.secret is not None:
        output["secret"] = result.secret
    return output
