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
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path
from trezorlib.transport import udp

from ..common import MNEMONIC12


@pytest.mark.skip_t2
@pytest.mark.skip_tr
def test_layout(client: Client):
    layout = client.debug.state().layout
    assert len(layout) == 1024


@pytest.mark.skip_t2
@pytest.mark.skip_tr
@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_mnemonic(client: Client):
    client.ensure_unlocked()
    mnemonic = client.debug.state().mnemonic_secret
    assert mnemonic == MNEMONIC12.encode()


@pytest.mark.skip_t2
@pytest.mark.skip_tr
@pytest.mark.setup_client(mnemonic=MNEMONIC12, pin="1234", passphrase="")
def test_pin(client: Client):
    resp = client.call_raw(messages.GetAddress(address_n=parse_path("m/44'/0'/0'/0/0")))
    assert isinstance(resp, messages.PinMatrixRequest)

    state = client.debug.state()
    assert state.pin == "1234"
    assert state.matrix != ""

    pin_encoded = client.debug.encode_pin("1234")
    resp = client.call_raw(messages.PinMatrixAck(pin=pin_encoded))
    assert isinstance(resp, messages.PassphraseRequest)

    resp = client.call_raw(messages.PassphraseAck(passphrase=""))
    assert isinstance(resp, messages.Address)


@pytest.mark.skip_t1
def test_softlock_instability(client: Client):
    def load_device():
        debuglink.load_device(
            client,
            mnemonic=MNEMONIC12,
            pin="1234",
            passphrase_protection=False,
            label="test",
        )

    # start from a clean slate:
    resp = client.debug.reseed(0)
    if isinstance(resp, messages.Failure) and not isinstance(
        client.transport, udp.UdpTransport
    ):
        pytest.xfail("reseed only supported on emulator")
    device.wipe(client)
    entropy_after_wipe = misc.get_entropy(client, 16)

    # configure and wipe the device
    load_device()
    client.debug.reseed(0)
    device.wipe(client)
    assert misc.get_entropy(client, 16) == entropy_after_wipe

    load_device()
    # the device has PIN -> lock it
    client.call(messages.LockDevice())
    client.debug.reseed(0)
    # wipe_device should succeed with no need to unlock
    device.wipe(client)
    # the device is now trying to run the lockscreen, which attempts to unlock.
    # If the device actually called config.unlock(), it would use additional randomness.
    # That is undesirable. Assert that the returned entropy is still the same.
    assert misc.get_entropy(client, 16) == entropy_after_wipe
