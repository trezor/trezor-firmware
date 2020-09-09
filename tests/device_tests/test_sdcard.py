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

    assert e.value.code == messages.FailureType.ProcessError


@pytest.mark.sd_card
@pytest.mark.setup_client(pin="1234")
def test_sd_protect_unlock(client):
    def input_flow_enable_sd_protect():
        yield  # Enter PIN to unlock device
        assert "PinDialog" == client.debug.wait_layout().text
        client.debug.input("1234")

        yield  # do you really want to enable SD protection
        assert "SD card protection" in client.debug.wait_layout().text
        client.debug.press_yes()

        yield  # enter current PIN
        assert "PinDialog" == client.debug.wait_layout().text
        client.debug.input("1234")

        yield  # you have successfully enabled SD protection
        assert "Success" in client.debug.wait_layout().text
        client.debug.press_yes()

    with client:
        client.watch_layout()
        client.set_input_flow(input_flow_enable_sd_protect)
        device.sd_protect(client, Op.ENABLE)

    def input_flow_change_pin():
        yield  # do you really want to change PIN?
        assert "Change PIN" in client.debug.wait_layout().text
        client.debug.press_yes()

        yield  # enter current PIN
        assert "PinDialog" == client.debug.wait_layout().text
        client.debug.input("1234")

        yield  # enter new PIN
        assert "PinDialog" == client.debug.wait_layout().text
        client.debug.input("1234")

        yield  # enter new PIN again
        assert "PinDialog" == client.debug.wait_layout().text
        client.debug.input("1234")

        yield  # Pin change successful
        assert "Success" in client.debug.wait_layout().text
        client.debug.press_yes()

    with client:
        client.watch_layout()
        client.set_input_flow(input_flow_change_pin)
        device.change_pin(client)

    client.debug.erase_sd_card(format=False)

    def input_flow_change_pin_format():
        yield  # do you really want to change PIN?
        assert "Change PIN" in client.debug.wait_layout().text
        client.debug.press_yes()

        yield  # enter current PIN
        assert "PinDialog" == client.debug.wait_layout().text
        client.debug.input("1234")

        yield  # SD card problem
        assert "Wrong SD card" in client.debug.wait_layout().text
        client.debug.press_no()  # close

    with client, pytest.raises(TrezorFailure) as e:
        client.watch_layout()
        client.set_input_flow(input_flow_change_pin_format)
        device.change_pin(client)

    assert e.value.code == messages.FailureType.ProcessError
