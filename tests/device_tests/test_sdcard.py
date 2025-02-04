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

PIN = "1234"

pytestmark = pytest.mark.models("core", skip=["safe3", "eckhart"])


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
@pytest.mark.setup_client(pin=PIN)
def test_sd_protect_unlock(session: Session):
    debug = session.client.debug
    layout = debug.read_layout

    def input_flow_enable_sd_protect():
        # debug.press_yes()
        yield  # Enter PIN to unlock device
        assert "PinKeyboard" in layout().all_components()
        debug.input(PIN)

        yield  # do you really want to enable SD protection
        assert TR.sd_card__enable in layout().text_content()
        debug.press_yes()

        yield  # enter current PIN
        assert "PinKeyboard" in layout().all_components()
        debug.input(PIN)

        yield  # you have successfully enabled SD protection
        assert TR.sd_card__enabled in layout().text_content()
        debug.press_yes()

    with session, session.client as client:
        client.watch_layout()
        client.set_input_flow(input_flow_enable_sd_protect)
        device.sd_protect(session, Op.ENABLE)

    def input_flow_change_pin():
        yield  # do you really want to change PIN?
        assert layout().title() == TR.pin__title_settings
        debug.press_yes()

        yield  # enter current PIN
        assert "PinKeyboard" in layout().all_components()
        debug.input(PIN)

        yield  # enter new PIN
        assert "PinKeyboard" in layout().all_components()
        debug.input(PIN)

        yield  # enter new PIN again
        assert "PinKeyboard" in layout().all_components()
        debug.input(PIN)

        yield  # Pin change successful
        assert TR.pin__changed in layout().text_content()
        debug.press_yes()

    with session, session.client as client:
        client.watch_layout()
        client.set_input_flow(input_flow_change_pin)
        device.change_pin(session)

    debug.erase_sd_card(format=False)

    def input_flow_change_pin_format():
        yield  # do you really want to change PIN?
        assert layout().title() == TR.pin__title_settings
        debug.press_yes()

        yield  # enter current PIN
        assert "PinKeyboard" in layout().all_components()
        debug.input(PIN)

        yield  # SD card problem
        assert (
            TR.sd_card__unplug_and_insert_correct in layout().text_content()
            or TR.sd_card__insert_correct_card in layout().text_content()
        )
        debug.press_no()  # close

    with session, session.client as client, pytest.raises(TrezorFailure) as e:
        client.watch_layout()
        client.set_input_flow(input_flow_change_pin_format)
        device.change_pin(session)

    assert e.value.code == messages.FailureType.ProcessError
