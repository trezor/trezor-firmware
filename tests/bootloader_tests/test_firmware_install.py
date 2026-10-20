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

import typing as t

from trezorlib._internal.bootargs import BootArgs, BootCommand
from trezorlib._internal.bootloader_emulator import BootloaderStartup, ExitKind

from .common import confirm

if t.TYPE_CHECKING:
    from .conftest import BootloaderRunner

VERSION = (2, 9, 0, 0)
NEWER_VERSION = (2, 9, 1, 0)


def test_install_on_empty_device(bootloader: "BootloaderRunner") -> None:
    """A trusted image installs on an empty device without a confirmation."""
    emu = bootloader.start(BootloaderStartup())
    ctx = emu.ctx
    assert not ctx.features.firmware_present

    # the vendor is fully trusted and there is nothing to replace, so the
    # bootloader asks nothing and the call returns after the upload
    ctx.firmware_update(bootloader.make_firmware(version=VERSION))

    record = bootloader.wait_exit()
    assert record.kind is ExitKind.REBOOT
    assert record.bootargs is not None
    assert record.bootargs.command == BootCommand.REBOOT
    # a fresh install starts with empty storage
    assert record.storage_erased is True


def test_boot_installed_firmware(bootloader: "BootloaderRunner") -> None:
    """With trusted firmware present the bootloader boots it straight away."""
    image = bootloader.profile_dir / "firmware.bin"
    image.write_bytes(bootloader.make_firmware(version=VERSION))

    emu = bootloader.start(BootloaderStartup(firmware=image))
    # no screen to interact with: the run is over before the debug link
    # answers, the storage marker written at startup must survive
    assert not emu.running

    record = bootloader.wait_exit()
    assert record.kind is ExitKind.JUMP
    assert record.bootargs is not None
    assert record.bootargs.command == BootCommand.NONE
    assert record.storage_erased is False


def test_install_on_device_with_firmware(bootloader: "BootloaderRunner") -> None:
    """Upgrading installed firmware asks for a confirmation and keeps the seed."""
    installed = bootloader.profile_dir / "firmware-installed.bin"
    installed.write_bytes(bootloader.make_firmware(version=VERSION))
    # stay in the bootloader on the screen that talks to the host
    connect = BootArgs.stop_and_connect().write(
        bootloader.profile_dir / "connect.bootargs"
    )

    emu = bootloader.start(BootloaderStartup(firmware=installed, bootargs=connect))
    ctx = emu.ctx
    features = ctx.features
    assert features.firmware_present
    assert (features.fw_major, features.fw_minor, features.fw_patch) == VERSION[:3]

    # firmware is present, so the bootloader asks before replacing it
    with ctx.debug.wait_for_layout_change():
        upload = ctx.firmware_update_in_background(
            bootloader.make_firmware(version=NEWER_VERSION)
        )
    confirm(ctx, info_page=True)
    upload.result(timeout=60)

    record = bootloader.wait_exit()
    assert record.kind is ExitKind.REBOOT
    assert record.bootargs is not None
    assert record.bootargs.command == BootCommand.REBOOT
    # same vendor: the seed survives the upgrade
    assert record.storage_erased is False
