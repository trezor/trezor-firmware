# This file is part of the Trezor project.
#
# Copyright (C) 2012-2026 SatoshiLabs and contributors
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

"""Screen interaction shared by the bootloader tests.

The bootloader's confirmation screens (wipe, install, unlock) put the
confirming button bottom-right on touch layouts and on the right physical
button on Caesar. Until DebugLinkState carries layout tokens, the positions
are fixed per layout from recordings.
"""

from __future__ import annotations

import typing as t

from trezorlib.debuglink import LayoutType

if t.TYPE_CHECKING:
    from trezorlib._internal.bootloader_emulator import BootloaderTestContext


def confirm(ctx: "BootloaderTestContext", *, info_page: bool = False) -> None:
    """Press the confirming button of a bootloader confirmation screen.

    `info_page` says whether the screen offers an info page (the install
    confirmation does, the wipe confirmation does not). On Caesar the right
    button then opens that page and both buttons together confirm.
    """
    layout = ctx.layout_type
    if layout in (LayoutType.Bolt, LayoutType.Delizia):
        ctx.debug.click((180, 212))
    elif layout is LayoutType.Eckhart:
        ctx.debug.click((285, 475))
    elif layout is LayoutType.Caesar:
        if info_page:
            ctx.debug.press_middle()
        else:
            ctx.debug.press_right()
    else:
        raise NotImplementedError(layout)


def cancel(ctx: "BootloaderTestContext") -> None:
    """Press the cancelling button of a bootloader confirmation screen."""
    layout = ctx.layout_type
    if layout in (LayoutType.Bolt, LayoutType.Delizia):
        ctx.debug.click((60, 212))
    elif layout is LayoutType.Eckhart:
        ctx.debug.click((95, 475))
    elif layout is LayoutType.Caesar:
        ctx.debug.press_left()
    else:
        raise NotImplementedError(layout)
