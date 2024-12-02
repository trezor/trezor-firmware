#
# This file is part of the Trezor project.
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

import time

import pytest

from trezorlib import device, messages, models
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure

from ..common import TEST_ADDRESS_N, get_test_address

PIN4 = "1234"

pytestmark = pytest.mark.setup_client(pin=PIN4)


def pin_request(session: Session):
    return (
        messages.PinMatrixRequest
        if session.model is models.T1B1
        else messages.ButtonRequest
    )


def set_autolock_delay(session: Session, delay):
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses(
            [
                pin_request(session),
                messages.ButtonRequest,
                messages.Success,
                # messages.Features,
            ]
        )
        device.apply_settings(session, auto_lock_delay_ms=delay)


def test_apply_auto_lock_delay(session: Session):
    set_autolock_delay(session, 10 * 1000)

    time.sleep(0.1)  # sleep less than auto-lock delay
    with session:
        # No PIN protection is required.
        session.set_expected_responses([messages.Address])
        get_test_address(session)

    time.sleep(10.5)  # sleep more than auto-lock delay
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses([pin_request(session), messages.Address])
        get_test_address(session)


@pytest.mark.parametrize(
    "seconds",
    [
        10,  # 10 seconds, minimum
        60,  # 1 minute
        123,  # 2 minutes
        3601,  # 1 hour
        7227,  # 2 hours
        536870,  # 149 hours, maximum
    ],
)
def test_apply_auto_lock_delay_valid(session: Session, seconds):
    set_autolock_delay(session, seconds * 1000)
    assert session.features.auto_lock_delay_ms == seconds * 1000


def test_autolock_default_value(session: Session):
    assert session.features.auto_lock_delay_ms is None
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        device.apply_settings(session, label="pls unlock")
        session.refresh_features()
    assert session.features.auto_lock_delay_ms == 60 * 10 * 1000


@pytest.mark.parametrize(
    "seconds",
    [0, 1, 9, 536871, 2**22],
)
def test_apply_auto_lock_delay_out_of_range(session: Session, seconds):

    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses(
            [
                pin_request(session),
                messages.Failure(code=messages.FailureType.ProcessError),
            ]
        )

        delay = seconds * 1000
        with pytest.raises(TrezorFailure):
            device.apply_settings(session, auto_lock_delay_ms=delay)


@pytest.mark.models("core")
def test_autolock_cancels_ui(session: Session):
    set_autolock_delay(session, 10 * 1000)

    resp = session.call_raw(
        messages.GetAddress(
            coin_name="Testnet",
            address_n=TEST_ADDRESS_N,
            show_display=True,
            script_type=messages.InputScriptType.SPENDADDRESS,
        )
    )
    assert isinstance(resp, messages.ButtonRequest)

    # send an ack, do not read response
    session._write(messages.ButtonAck())
    # sleep more than auto-lock delay
    time.sleep(10.5)
    resp = session._read()

    assert isinstance(resp, messages.Failure)
    assert resp.code == messages.FailureType.ActionCancelled


def test_autolock_ignores_initialize(session: Session):
    client = session.client
    set_autolock_delay(session, 10 * 1000)

    assert session.features.unlocked is True

    start = time.monotonic()
    while time.monotonic() - start < 11:
        # init_device should always work even if locked
        client.resume_session(session)
        time.sleep(0.1)

    # after 11 seconds we are definitely locked
    session.refresh_features()
    assert session.features.unlocked is False


def test_autolock_ignores_getaddress(session: Session):

    set_autolock_delay(session, 10 * 1000)

    assert session.features.unlocked is True

    start = time.monotonic()
    # let's continue for 8 seconds to give a little leeway to the slow CI
    while time.monotonic() - start < 8:
        get_test_address(session)
        time.sleep(0.1)

    # sleep 3 more seconds to wait for autolock
    time.sleep(3)

    # after 11 seconds we are definitely locked
    session.refresh_features()
    assert session.features.unlocked is False
