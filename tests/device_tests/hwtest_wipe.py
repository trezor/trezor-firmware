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

"""Check that `TrezorTestContext.wipe_device()` works on a real hardware device.

`wipe_device()` picks how to wipe based on `DebugLink.has_wipe`:
- firmware >= 2.9.1 sends `WipeDevice` over debuglink,
- older firmware sends `WipeDevice` over a normal session, and debuglink
  confirms the wipe on the device.

These tests use the standard `test_ctx` fixture, which goes through
`_prepared_test_ctx`, so the device is also wiped (and set up again) before
every test.

The device must be connected via USB and run a debug firmware build. This file
is not collected by default (it does not match `test_*.py`), run it explicitly:

    pytest -s tests/device_tests/hwtest_wipe.py
"""

from __future__ import annotations

import pytest

from trezorlib.debuglink import TrezorTestContext

HAS_WIPE_SINCE = (2, 9, 1)
PIN = "1234"


def wipe_path(test_ctx: TrezorTestContext) -> str:
    return "debuglink" if test_ctx.debug.has_wipe else "normal session"


def version_str(test_ctx: TrezorTestContext) -> str:
    return ".".join(str(v) for v in test_ctx.version)


def test_has_wipe_matches_version(test_ctx: TrezorTestContext) -> None:
    print(
        f"\nFirmware {version_str(test_ctx)}: "
        f"has_wipe={test_ctx.debug.has_wipe}, wiping via {wipe_path(test_ctx)}"
    )
    assert test_ctx.debug.has_wipe == (test_ctx.version >= HAS_WIPE_SINCE)


def test_wipe_device(test_ctx: TrezorTestContext) -> None:
    # The fixture has set up the device with the default seed.
    assert test_ctx.features.initialized

    print(f"\nWiping {version_str(test_ctx)} via {wipe_path(test_ctx)}")
    test_ctx.wipe_device()

    features = test_ctx.refresh_features()
    assert not features.initialized
    assert not features.pin_protection


@pytest.mark.setup_client(pin=PIN)
def test_wipe_device_with_pin(test_ctx: TrezorTestContext) -> None:
    # The `test_ctx` fixture locks the device before the test.
    assert test_ctx.features.initialized
    assert test_ctx.features.pin_protection

    print(f"\nWiping {version_str(test_ctx)} via {wipe_path(test_ctx)} (PIN set)")
    # In case the firmware asks for the PIN before wiping a locked device.
    test_ctx.use_pin_sequence([PIN])
    test_ctx.wipe_device()

    features = test_ctx.refresh_features()
    assert not features.initialized
    assert not features.pin_protection
