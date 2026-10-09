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
`xtask flash-erase` and `xtask reset`) and via USB (for debuglink and trezorctl).

This file is not collected by default (it does not match `test_*.py`), run it
explicitly:

    HWTEST_UPGRADE_FW=path/to/firmware.bin \\
    HWTEST_COMBINED_FW=path/to/combined.bin \\
        pytest -s tests/device_tests/hwtest_firmware_upgrades.py

Environment variables:
    HWTEST_UPGRADE_FW   firmware passed to `trezorctl firmware update --filename` (required)
    HWTEST_COMBINED_FW  combined image to flash first; if unset, the image built
                        by `xtask combine` is used
    TREZOR_PATH         optional, device path to connect to

Use `-s` so that you can see trezorctl output and confirm the update on the
device when the bootloader asks for it.
"""

from __future__ import annotations

import itertools
import os
import subprocess
import time
from pathlib import Path

import pytest

from trezorlib import debuglink
from trezorlib.debuglink import TrezorTestContext
from trezorlib.transport import get_transport
from trezorlib.transport.ble import BleTransport

from ..common import MNEMONIC_SLIP39_SINGLE_EXT_20, get_test_address

MODEL = "T3B1"
PIN = "1"
LABEL = "upgrades"

ROOT = Path(__file__).resolve().parents[2]

COMMAND_TIMEOUT = 600
DEVICE_TIMEOUT = 60

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
            raise RuntimeError("Timed out waiting for the device") from error
        time.sleep(1)


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
    combined_fw = os.environ.get("HWTEST_COMBINED_FW")
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
    log("Releasing the device for trezorctl")
    close(test_ctx)

    # Upgrade.
    run_external("trezorctl", "firmware", "update", "--filename", upgrade_fw)

    # Device must keep its seed and PIN after the upgrade.
    test_ctx = wait_for_device()
    try:
        log("Checking the device kept its seed, PIN and label")
        assert test_ctx.features.initialized
        assert test_ctx.features.pin_protection
        assert test_ctx.features.label == LABEL
        test_ctx.use_pin_sequence([PIN])
        address_after = get_test_address(test_ctx.get_session())
        log(f"Address after upgrade: {address_after}")
        assert address_after == address
        log("Upgrade test passed")
    finally:
        close(test_ctx)
