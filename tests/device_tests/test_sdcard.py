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
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import SdProtectOperationType as Op

from .. import translations as TR

pytestmark = pytest.mark.models("core", skip="safe3")


@pytest.mark.sd_card(formatted=False)
def test_sd_format(session: Session):
    device.sd_protect(session, Op.ENABLE)
    assert session.features.sd_protection is True


@pytest.mark.sd_card(formatted=False)
def test_sd_no_format(session: Session):
    debug = session.client.debug

    def input_flow():
        yield  # enable SD protection?
        debug.press_yes()

        yield  # format SD card
        debug.press_no()

    with session, session.client as client, pytest.raises(TrezorFailure) as e:
        client.set_input_flow(input_flow)
        device.sd_protect(session, Op.ENABLE)

    assert e.value.code == messages.FailureType.ProcessError


@pytest.mark.sd_card
@pytest.mark.setup_client(pin="1234")
def test_sd_protect_unlock(session: Session):
    raise Exception("FAILS, NOT SURE WHY")
    debug = session.client.debug
    layout = debug.read_layout

    def input_flow_enable_sd_protect():
        # debug.press_yes()
        yield  # Enter PIN to unlock device
        assert "PinKeyboard" in layout().all_components()
        debug.input("1234")

        yield  # do you really want to enable SD protection
        TR.assert_in(layout().text_content(), "sd_card__enable")
        debug.press_yes()

        yield  # enter current PIN
        assert "PinKeyboard" in layout().all_components()
        debug.input("1234")

        yield  # you have successfully enabled SD protection
        TR.assert_in(layout().text_content(), "sd_card__enabled")
        debug.press_yes()

    with session, session.client as client:
        client.watch_layout()
        client.set_input_flow(input_flow_enable_sd_protect)
        device.sd_protect(session, Op.ENABLE)

    def input_flow_change_pin():
        yield  # do you really want to change PIN?
        TR.assert_equals(layout().title(), "pin__title_settings")
        debug.press_yes()

        yield  # enter current PIN
        assert "PinKeyboard" in layout().all_components()
        debug.input("1234")

        yield  # enter new PIN
        assert "PinKeyboard" in layout().all_components()
        debug.input("1234")

        yield  # enter new PIN again
        assert "PinKeyboard" in layout().all_components()
        debug.input("1234")

        yield  # Pin change successful
        TR.assert_in(layout().text_content(), "pin__changed")
        debug.press_yes()

    with session.client as client:
        client.watch_layout()
        client.set_input_flow(input_flow_change_pin)
        device.change_pin(session)

    debug.erase_sd_card(format=False)

    def input_flow_change_pin_format():
        yield  # do you really want to change PIN?
        TR.assert_equals(layout().title(), "pin__title_settings")
        debug.press_yes()
        yield  # enter current PIN
        assert "PinKeyboard" in layout().all_components()
        debug.input("1234")

        yield  # SD card problem
        TR.assert_in_multiple(
            layout().text_content(),
            ["sd_card__unplug_and_insert_correct", "sd_card__insert_correct_card"],
        )
        debug.press_no()  # close

    with session, session.client as client, pytest.raises(TrezorFailure) as e:
        client.watch_layout()
        client.set_input_flow(input_flow_change_pin_format)
        device.change_pin(session)

    assert e.value.code == messages.FailureType.ProcessError
