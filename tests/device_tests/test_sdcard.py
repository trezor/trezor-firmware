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
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import SdProtectOperationType as Op

pytestmark = pytest.mark.skip_t1


@pytest.mark.sd_card(formatted=False)
def test_sd_format(client):
    device.sd_protect(client, Op.ENABLE)
    assert client.features.sd_protection is True


@pytest.mark.sd_card(formatted=False)
def test_sd_no_format(client):
    def input_flow():
        yield  # enable SD protection?
        client.debug.press_yes()

        yield  # format SD card
        client.debug.press_no()

    with pytest.raises(TrezorFailure) as e, client:
        client.set_input_flow(input_flow)
        device.sd_protect(client, Op.ENABLE)

    assert e.value.failure.code == messages.FailureType.ProcessError
