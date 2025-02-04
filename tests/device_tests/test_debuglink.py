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

from trezorlib import debuglink, device, messages, misc
from trezorlib.client import ProtocolVersion
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path
from trezorlib.transport import udp

from ..common import MNEMONIC12


@pytest.mark.models("legacy")
def test_layout(client: Client):
    layout = client.debug.state().layout
    assert len(layout) == 1024


@pytest.mark.models("legacy")
@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_mnemonic(session: Session):
    session.ensure_unlocked()
    mnemonic = session.client.debug.state().mnemonic_secret
    assert mnemonic == MNEMONIC12.encode()


@pytest.mark.models("legacy")
@pytest.mark.setup_client(mnemonic=MNEMONIC12, pin="1234", passphrase="")
def test_pin(session: Session):
    resp = session.call_raw(
        messages.GetAddress(address_n=parse_path("m/44'/0'/0'/0/0"))
    )
    assert isinstance(resp, messages.PinMatrixRequest)

    with session.client as client:
        state = client.debug.state()
        assert state.pin == "1234"
        assert state.matrix != ""

        pin_encoded = client.debug.encode_pin("1234")
        resp = session.call_raw(messages.PinMatrixAck(pin=pin_encoded))
        assert isinstance(resp, messages.PassphraseRequest)

        resp = session.call_raw(messages.PassphraseAck(passphrase=""))
        assert isinstance(resp, messages.Address)


@pytest.mark.models("core")
def test_softlock_instability(session: Session):
    if session.protocol_version == ProtocolVersion.PROTOCOL_V2:
        raise Exception("THIS NEEDS TO BE CHANGED FOR THP")

    def load_device():
        debuglink.load_device(
            session,
            mnemonic=MNEMONIC12,
            pin="1234",
            passphrase_protection=False,
            label="test",
        )

    # start from a clean slate:
    resp = session.client.debug.reseed(0)
    if isinstance(resp, messages.Failure) and not isinstance(
        session.client.transport, udp.UdpTransport
    ):
        pytest.xfail("reseed only supported on emulator")
    device.wipe(session)
    entropy_after_wipe = misc.get_entropy(session, 16)
    session.refresh_features()

    # configure and wipe the device
    load_device()
    session.client.debug.reseed(0)
    device.wipe(session)
    assert misc.get_entropy(session, 16) == entropy_after_wipe
    session.refresh_features()

    load_device()
    # the device has PIN -> lock it
    session.call(messages.LockDevice())
    session.client.debug.reseed(0)
    # wipe_device should succeed with no need to unlock
    device.wipe(session)
    # the device is now trying to run the lockscreen, which attempts to unlock.
    # If the device actually called config.unlock(), it would use additional randomness.
    # That is undesirable. Assert that the returned entropy is still the same.
    assert misc.get_entropy(session, 16) == entropy_after_wipe
