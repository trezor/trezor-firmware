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

from trezorlib.messages import DebugLinkShowTextIcon

from .. import debuglink
from . import ChoiceType

ICONS = {
    key: getattr(DebugLinkShowTextIcon, key)
    for key in dir(DebugLinkShowTextIcon)
    if not key.startswith("__")
}


@click.group(name="debug")
def cli():
    """Miscellaneous debug features."""


@cli.command()
@click.option("-i", "--icon", type=ChoiceType(ICONS))
@click.argument("header_text")
@click.argument("body_text")
@click.pass_obj
def show_text(connect, header_text, body_text, icon):
    """Show text (header_text and body_text) on Trezor display together with chosen icon."""
    return debuglink.show_text(connect(), header_text, body_text, icon)
