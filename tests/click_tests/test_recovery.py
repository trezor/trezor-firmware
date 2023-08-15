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

from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator

import pytest

from trezorlib import device, messages

from ..common import MNEMONIC12, MNEMONIC_SLIP39_BASIC_20_3of6
from . import recovery

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink

    from ..device_handler import BackgroundDeviceHandler


pytestmark = [pytest.mark.skip_t1]


@contextmanager
def prepare_recovery_and_evaluate(
    device_handler: "BackgroundDeviceHandler",
) -> Generator["DebugLink", None, None]:
    features = device_handler.features()
    debug = device_handler.debuglink()
    assert features.initialized is False
    device_handler.run(device.recover, pin_protection=False)  # type: ignore

    yield debug

    assert isinstance(device_handler.result(), messages.Success)
    features = device_handler.features()
    assert features.initialized is True
    assert features.recovery_mode is False


@pytest.mark.setup_client(uninitialized=True)
def test_recovery_slip39_basic(device_handler: "BackgroundDeviceHandler"):
    with prepare_recovery_and_evaluate(device_handler) as debug:
        recovery.confirm_recovery(debug)

        recovery.select_number_of_words(debug)
        recovery.enter_shares(debug, MNEMONIC_SLIP39_BASIC_20_3of6)
        recovery.finalize(debug)


@pytest.mark.setup_client(uninitialized=True)
def test_recovery_bip39(device_handler: "BackgroundDeviceHandler"):
    with prepare_recovery_and_evaluate(device_handler) as debug:
        recovery.confirm_recovery(debug)

        recovery.select_number_of_words(debug, num_of_words=12)
        recovery.enter_seed(debug, MNEMONIC12.split())
        recovery.finalize(debug)
