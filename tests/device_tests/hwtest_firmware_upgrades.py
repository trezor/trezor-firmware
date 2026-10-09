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

"""Firmware upgrade test on a real hardware device.

The device must be connected through a debug probe (for `xtask flash`,
`xtask flash-erase` and `xtask reset`) and via USB (for debuglink).

The upgrade uses the interaction-less update (ILU) flow, so no button presses
are needed in the bootloader: the test sends `RebootToBootloader` with
`INSTALL_UPGRADE` and the new firmware header, debuglink confirms the update
in the firmware, and the bootloader then installs the image without asking.
The bootloader only allows this when the new image is from the same vendor,
has a strictly higher version and a full-trust vendor header (dev builds
qualify).

This file is not collected by default (it does not match `test_*.py`), run it
explicitly:

    HWTEST_UPGRADE_FW=path/to/firmware.bin \\
    HWTEST_COMBINED_FW=path/to/combined.bin \\
        pytest -s tests/device_tests/hwtest_firmware_upgrades.py

Environment variables:
    HWTEST_UPGRADE_FW   firmware to upgrade to (required); must be a non-debug
                        build, because debug firmware wipes the storage on boot
                        on real hardware. Its boot PIN has to be entered by hand.
    HWTEST_COMBINED_FW  combined image to flash first; if unset, the image built
                        by `xtask combine` is used
    TREZOR_PATH         optional, device path to connect to

Use `-s` to see the progress live.
"""

from __future__ import annotations

import itertools
import os
import subprocess
import time
from pathlib import Path

import pytest

from trezorlib import debuglink, device, firmware, messages
from trezorlib.client import AppManifest, TrezorClient, get_client
from trezorlib.debuglink import TrezorTestContext
from trezorlib.firmware.core import VendorFirmware
from trezorlib.transport import get_transport
from trezorlib.transport.ble import BleTransport

from ..common import MNEMONIC_SLIP39_SINGLE_EXT_20, get_test_address

MODEL = "T3B1"
PIN = "1"
LABEL = "upgrades"

ROOT = Path(__file__).resolve().parents[2]

COMMAND_TIMEOUT = 600
DEVICE_TIMEOUT = 60
# Long enough to enter the PIN on the device by hand.
PIN_ENTRY_TIMEOUT = 300

_step = itertools.count(1)


def log(msg: str) -> None:
    """Print a numbered progress message (run pytest with `-s` to see it live)."""
    print(f"\n[{next(_step):2}] {msg}", flush=True)


def run_external(*cmd: str, timeout: float = COMMAND_TIMEOUT) -> None:
    """Run an external command and wait for it to finish successfully."""
    log(f"Running: {' '.join(cmd)}")
    start = time.monotonic()
    subprocess.run(cmd, cwd=ROOT, check=True, timeout=timeout)
    print(f"     done in {time.monotonic() - start:.1f}s", flush=True)


def xtask(*args: str) -> None:
    run_external("xtask", *args, "--model", MODEL)


def wait_for_device(
    force_wipe: bool = False, timeout: float = DEVICE_TIMEOUT
) -> TrezorTestContext:
    """Wait until a debuggable device running firmware is available."""
    path = os.environ.get("TREZOR_PATH")
    log(f"Waiting for the device (timeout {timeout}s)")
    start = time.monotonic()
    deadline = start + timeout
    while True:
        try:
            test_ctx = TrezorTestContext(
                get_transport(path), auto_interact=True, force_wipe=force_wipe
            )
            # In bootloader mode, debuglink is not available, so the constructor
            # fails before we get here. Double-check anyway.
            if not test_ctx.features.bootloader_mode:
                f = test_ctx.features
                print(
                    f"     connected after {time.monotonic() - start:.1f}s: "
                    f"{test_ctx.model.internal_name} "
                    f"{f.major_version}.{f.minor_version}.{f.patch_version}",
                    flush=True,
                )
                return test_ctx
            close(test_ctx)
            error: Exception = RuntimeError("Device is in bootloader mode")
        except Exception as e:
            error = e
        if time.monotonic() > deadline:
            raise RuntimeError(f"Timed out waiting for the device: {error}") from error
        time.sleep(1)


def wait_for_client(bootloader: bool, timeout: float = DEVICE_TIMEOUT) -> TrezorClient:
    """Wait until the device is available in bootloader or firmware mode.

    Unlike `wait_for_device`, this does not need debuglink, so it works with
    the bootloader and with non-debug firmware.
    """
    path = os.environ.get("TREZOR_PATH")
    mode = "bootloader" if bootloader else "firmware"
    log(f"Waiting for the {mode} (timeout {timeout}s)")
    start = time.monotonic()
    deadline = start + timeout
    while True:
        transport = None
        try:
            transport = get_transport(path)
            transport.open()
            client = get_client(AppManifest(app_name="hwtest"), transport)
            if bool(client.features.bootloader_mode) == bootloader:
                print(
                    f"     {mode} after {time.monotonic() - start:.1f}s",
                    flush=True,
                )
                return client
            error: Exception = RuntimeError(f"Device is not in {mode} mode")
        except Exception as e:
            error = e
        if transport is not None:
            transport.close()
        if time.monotonic() > deadline:
            raise RuntimeError(f"Timed out waiting for the {mode}: {error}") from error
        time.sleep(1)


def version_str(version: tuple[int, ...]) -> str:
    return ".".join(str(v) for v in version)


def close(test_ctx: TrezorTestContext) -> None:
    """Release the USB interfaces so that external tools can use them."""
    test_ctx.debug.close()
    test_ctx.transport.close()


@pytest.fixture(autouse=True)
def _no_ble() -> None:
    if os.environ.get("TREZOR_BLE") != "1":
        BleTransport.ENABLED = False


def test_firmware_upgrade() -> None:
    upgrade_fw = os.environ.get("HWTEST_UPGRADE_FW")
    if not upgrade_fw:
        pytest.fail("HWTEST_UPGRADE_FW must point to the firmware to upgrade to")
    # External commands run from the repo root, so make the paths absolute.
    upgrade_fw = str(Path(upgrade_fw).resolve())
    combined_fw = os.environ.get("HWTEST_COMBINED_FW")
    if combined_fw:
        combined_fw = str(Path(combined_fw).resolve())
    log(f"Combined FW: {combined_fw or '(xtask combine output)'}")
    log(f"Upgrade FW: {upgrade_fw}")

    # reset first and twice to make sure initial state is correct
    xtask("reset")
    xtask("reset")
    # Put the device into a known state.
    xtask("flash-erase")
    xtask("reset")
    xtask("reset")
    if combined_fw:
        xtask("flash", "firmware", "--combined", "--file", combined_fw)
    else:
        xtask("flash", "firmware", "--combined")
    xtask("reset")
    xtask("reset")

    # Set up the device with a seed and a PIN.
    test_ctx = wait_for_device(force_wipe=True)
    log(f"Loading seed and PIN {PIN!r}")
    debuglink.load_device(
        test_ctx.get_seedless_session(),
        mnemonic=MNEMONIC_SLIP39_SINGLE_EXT_20,
        pin=PIN,
        passphrase_protection=False,
        label=LABEL,
    )
    test_ctx.refresh_features()
    log("Checking the device is initialized and PIN protected")
    assert test_ctx.features.initialized
    assert test_ctx.features.pin_protection
    address = get_test_address(test_ctx.get_session())
    log(f"Address before upgrade: {address}")

    # Upgrade using the interaction-less update flow.
    fw_data = Path(upgrade_fw).read_bytes()
    fw = firmware.parse(fw_data)
    assert isinstance(fw, VendorFirmware)
    f = test_ctx.features
    current_version = (f.major_version, f.minor_version, f.patch_version, 0)
    new_version = tuple(fw.firmware.header.version)
    log(
        f"Upgrading {version_str(current_version)} ({f.fw_vendor!r}) to "
        f"{version_str(new_version)} ({fw.vendor_header.text!r})"
    )
    # Same conditions as the bootloader, otherwise it would ask for confirmation.
    assert (
        fw.vendor_header.text == f.fw_vendor
    ), "Upgrade firmware must be from the same vendor"
    assert new_version > current_version, "Upgrade firmware must be newer"
    assert (
        fw.vendor_header.trust.is_full_trust()
    ), "Upgrade firmware must have a full-trust vendor header"

    log("Rebooting to bootloader with INSTALL_UPGRADE (confirmed via debuglink)")
    header_len = fw.vendor_header.header_len + fw.firmware.header.header_len
    device.reboot_to_bootloader(
        test_ctx.get_seedless_session(),
        boot_command=messages.BootCommand.INSTALL_UPGRADE,
        firmware_header=fw_data[:header_len],
    )
    close(test_ctx)

    client = wait_for_client(bootloader=True)
    try:
        log(f"Uploading {len(fw_data)} bytes of firmware")
        firmware.update(client.get_session(passphrase=None), fw_data)
        print("     upload finished", flush=True)
    finally:
        client.transport.close()

    # Device must keep its seed and PIN after the upgrade.
    # The upgrade firmware must be a non-debug build: debug firmware wipes the
    # storage on every boot on real hardware (see core/src/boot.py). Without
    # debuglink, the PIN asked at boot has to be entered on the device by hand,
    # and the device does not respond over USB until then.
    log(f"Enter PIN {PIN!r} on the device")
    client = wait_for_client(bootloader=False, timeout=PIN_ENTRY_TIMEOUT)
    try:
        f = client.features
        log(
            f"Checking the device runs {version_str(new_version[:3])} "
            "and kept its seed, PIN and label"
        )
        assert (f.major_version, f.minor_version, f.patch_version) == new_version[
            :3
        ], "Device is not running the upgrade firmware"
        assert f.initialized, "Device lost its seed (was the upgrade a debug build?)"
        assert f.pin_protection
        assert f.label == LABEL
        address_after = get_test_address(client.get_session())
        log(f"Address after upgrade: {address_after}")
        assert address_after == address
        log("Upgrade test passed")
    finally:
        client.transport.close()
