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

from typing import TYPE_CHECKING, Union

import click

from .. import mapping, messages, protobuf
from ..client import TrezorClient
from ..debuglink import TrezorClientDebugLink
from ..debuglink import optiga_set_sec_max as debuglink_optiga_set_sec_max
from ..debuglink import prodtest_t1 as debuglink_prodtest_t1
from ..debuglink import record_screen
from . import with_client

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


@cli.command()
@click.argument("directory", required=False)
@click.option("-s", "--stop", is_flag=True, help="Stop the recording")
@click.pass_obj
def record(obj: "TrezorConnection", directory: Union[str, None], stop: bool) -> None:
    """Record screen changes into a specified directory.

    Recording can be stopped with `-s / --stop` option.
    """
    record_screen_from_connection(obj, None if stop else directory)


def record_screen_from_connection(
    obj: "TrezorConnection", directory: Union[str, None]
) -> None:
    """Record screen helper to transform TrezorConnection into TrezorClientDebugLink."""
    transport = obj.get_transport()
    debug_client = TrezorClientDebugLink(transport, auto_interact=False)
    debug_client.open()
    record_screen(debug_client, directory, report_func=click.echo)
    debug_client.close()


@cli.command()
@with_client
def prodtest_t1(client: "TrezorClient") -> None:
    """Perform a prodtest on Model One.

    Only available on PRODTEST firmware and on T1B1. Formerly named self-test.
    """
    debuglink_prodtest_t1(client)


@cli.command()
@with_client
def optiga_set_sec_max(client: "TrezorClient") -> None:
    """Set Optiga's security event counter to maximum."""
    debuglink_optiga_set_sec_max(client)
