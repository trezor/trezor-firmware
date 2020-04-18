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

from .. import debuglink
from ..messages import DebugLinkShowTextStyle as S


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
@click.pass_obj
def show_text(connect, icon, color, header, body):
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

    return debuglink.show_text(
        connect(), header, body_text, icon=icon, icon_color=color
    )
