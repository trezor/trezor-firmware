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

import pytest

from trezorlib import device, messages

from ..common import MNEMONIC_SLIP39_BASIC_20_3of6
from . import recovery


@pytest.mark.skip_t1
@pytest.mark.setup_client(uninitialized=True)
def test_recovery(device_handler):
    features = device_handler.features()
    debug = device_handler.debuglink()

    assert features.initialized is False
    device_handler.run(device.recover, pin_protection=False)

    recovery.confirm_recovery(debug)

    recovery.select_number_of_words(debug)
    recovery.enter_shares(debug, MNEMONIC_SLIP39_BASIC_20_3of6)
    recovery.finalize(debug)

    assert isinstance(device_handler.result(), messages.Success)
    features = device_handler.features()
    assert features.initialized is True
    assert features.recovery_mode is False
