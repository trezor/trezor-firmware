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

from typing import TYPE_CHECKING

import click

from .. import mapping, messages, protobuf

if TYPE_CHECKING:
    from . import TrezorConnection


@click.group(name="debug")
def cli() -> None:
    """Miscellaneous debug features."""


@cli.command()
@click.argument("message_name_or_type")
@click.argument("hex_data")
@click.pass_obj
def send_bytes(
    obj: "TrezorConnection", message_name_or_type: str, hex_data: str
) -> None:
    """Send raw bytes to Trezor.

    Message type and message data must be specified separately, due to how message
    chunking works on the transport level. Message length is calculated and sent
    automatically, and it is currently impossible to explicitly specify invalid length.

    MESSAGE_NAME_OR_TYPE can either be a number, or a name from the MessageType enum,
    in which case the value of that enum is used.
    """
    if message_name_or_type.isdigit():
        message_type = int(message_name_or_type)
    else:
        message_type = getattr(messages.MessageType, message_name_or_type)

    if not isinstance(message_type, int):
        raise click.ClickException("Invalid message type.")

    try:
        message_data = bytes.fromhex(hex_data)
    except Exception as e:
        raise click.ClickException("Invalid hex data.") from e

    transport = obj.get_transport()
    transport.begin_session()
    transport.write(message_type, message_data)

    response_type, response_data = transport.read()
    transport.end_session()

    click.echo(f"Response type: {response_type}")
    click.echo(f"Response data: {response_data.hex()}")

    try:
        msg = mapping.DEFAULT_MAPPING.decode(response_type, response_data)
        click.echo("Parsed message:")
        click.echo(protobuf.format_message(msg))
    except Exception as e:
        click.echo(f"Could not parse response: {e}")
