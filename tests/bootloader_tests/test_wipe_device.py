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

from __future__ import annotations

import subprocess
import typing as t

from trezorlib import messages
from trezorlib._internal.bootargs import BootCommand
from trezorlib._internal.bootloader_emulator import BootloaderStartup, ExitKind
from trezorlib.debuglink import LayoutType
from trezorlib.messages import DebugWaitType

if t.TYPE_CHECKING:
    from .conftest import BootloaderRunner


def confirm_wipe(ctx) -> None:
    """Press the confirming button of the wipe-confirmation screen."""
    layout = ctx.layout_type
    if layout in (LayoutType.Bolt, LayoutType.Delizia):
        ctx.debug.click((180, 212))
    elif layout is LayoutType.Eckhart:
        ctx.debug.click((285, 475))
    elif layout is LayoutType.Caesar:
        ctx.debug.press_right()
    else:
        raise NotImplementedError(layout)


def test_host_wipe_empty_device(bootloader: "BootloaderRunner") -> None:
    """An empty device wipes its storage on the host's request."""
    emu = bootloader.start(BootloaderStartup())
    ctx = emu.ctx
    assert ctx.features.bootloader_mode
    assert not ctx.features.firmware_present

    # the welcome screen listens on the wire port; the reply comes after the
    # confirmation on screen
    with ctx.debug.wait_for_layout_change():
        reply = ctx.wire.call_in_background(messages.WipeDevice(), timeout=60)
    confirm_wipe(ctx)
    assert isinstance(reply.result(timeout=60), messages.Success)

    # Success is sent 100 ms before the success screen is drawn; without
    # layout tokens the test cannot wait for that screen by name
    ctx.debug.state(DebugWaitType.IMMEDIATE)

    if ctx.layout_type is LayoutType.Eckhart:
        # the success screen offers a restart button; a tap that lands on
        # the progress screen before it is ignored, so tap until the run ends
        record = None
        for _ in range(10):
            ctx.debug.click((190, 475))
            try:
                record = bootloader.wait_exit(timeout=2)
                break
            except subprocess.TimeoutExpired:
                continue
        assert record is not None, "the restart button did not end the run"
        assert record.kind is ExitKind.REBOOT
        assert record.bootargs is not None
        assert record.bootargs.command == BootCommand.REBOOT
    else:
        # the success screen asks the user to reconnect the device, which
        # nothing on the emulator can do
        record = bootloader.abort()
        assert record.kind is ExitKind.QUIT
    assert record.storage_erased is True
