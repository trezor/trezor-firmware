# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

import click

from .. import debuglink, mapping, messages, protobuf
from ..messages import DebugLinkShowTextStyle as S
from . import with_client


@click.group(name="debug")
def cli():
    """Miscellaneous debug features."""


STYLES = {
    "@@NORMAL": S.NORMAL,
    "@@BOLD": S.BOLD,
    "@@MONO": S.MONO,
    "@@MONO_BOLD": S.MONO_BOLD,
    "@@BR": S.BR,
    "@@BR_HALF": S.BR_HALF,
}


@cli.command()
@click.option("-i", "--icon", help="Header icon name")
@click.option("-c", "--color", help="Header icon color")
@click.option("-h", "--header", help="Header text", default="Showing text")
@click.argument("body")
@with_client
def show_text(client, icon, color, header, body):
    """Show text on Trezor display.

    For usage instructions, see:
    https://github.com/trezor/trezor-firmware/blob/master/docs/python/show-text.md
    """
    body = body.split()
    body_text = []
    words = []

    def _flush():
        if words:
            body_text.append((None, " ".join(words)))
        words.clear()

    for word in body:
        if word in STYLES:
            _flush()
            body_text.append((STYLES[word], None))
        elif word.startswith("%%"):
            _flush()
            body_text.append((S.SET_COLOR, word[2:]))
        else:
            words.append(word)

    _flush()

    return debuglink.show_text(client, header, body_text, icon=icon, icon_color=color)


@cli.command()
@click.argument("message_name_or_type")
@click.argument("hex_data")
@click.pass_obj
def send_bytes(obj, message_name_or_type, hex_data):
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

    click.echo("Response type: {}".format(response_type))
    click.echo("Response data: {}".format(response_data.hex()))

    try:
        msg = mapping.decode(response_type, response_data)
        click.echo("Parsed message:")
        click.echo(protobuf.format_message(msg))
    except Exception as e:
        click.echo("Could not parse response: {}".format(e))
