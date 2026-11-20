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
confirming button bottom-right on touch layouts, where trezorlib's
`ScreenButtons` finds it as it does in firmware tests; on Caesar both
physical buttons together confirm. Which screen is up comes from the layout
tokens in DebugLinkState, see `wait_for_screen()`.
"""

from __future__ import annotations

import time
import typing as t

from trezorlib import messages
from trezorlib.debuglink import LayoutContent, LayoutType

if t.TYPE_CHECKING:
    from trezorlib._internal.bootloader_emulator import BootloaderTestContext


def wait_for_screen(
    ctx: "BootloaderTestContext",
    accept: t.Callable[[LayoutContent], bool],
    timeout: float = 10,
) -> LayoutContent:
    """Read the screen until `accept` takes it, and return it.

    The bootloader reports the screen on display, also while a workflow keeps
    it busy, so polling sees every screen that stays up long enough to read.
    Each read is bounded by the deadline too, so a stalled debug link fails
    the test instead of hanging it.
    """
    deadline = time.monotonic() + timeout
    while True:
        state = ctx.debug._call(
            messages.DebugLinkGetState(wait_layout=messages.DebugWaitType.IMMEDIATE),
            timeout=max(deadline - time.monotonic(), 0.1),
            expect=messages.DebugLinkState,
        )
        layout = LayoutContent(state.tokens)
        if accept(layout):
            return layout
        if time.monotonic() >= deadline:
            raise TimeoutError(f"screen not reached, showing: {layout.dict}")
        time.sleep(0.05)


def confirm(ctx: "BootloaderTestContext") -> None:
    """Press the confirming button of a bootloader confirmation screen."""
    layout = ctx.layout_type
    if layout in (LayoutType.Bolt, LayoutType.Delizia, LayoutType.Eckhart):
        ctx.debug.click(ctx.debug.screen_buttons.ok())
    elif layout is LayoutType.Caesar:
        ctx.debug.press_middle()
    else:
        raise NotImplementedError(layout)


def cancel(ctx: "BootloaderTestContext") -> None:
    """Press the cancelling button of a bootloader confirmation screen."""
    layout = ctx.layout_type
    if layout in (LayoutType.Bolt, LayoutType.Delizia, LayoutType.Eckhart):
        ctx.debug.click(ctx.debug.screen_buttons.cancel())
    elif layout is LayoutType.Caesar:
        ctx.debug.press_left()
    else:
        raise NotImplementedError(layout)
