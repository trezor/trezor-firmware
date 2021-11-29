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

from trezorlib import device, exceptions, messages

from ...common import (
    MNEMONIC_SLIP39_BASIC_20_3of6,
    MNEMONIC_SLIP39_BASIC_20_3of6_SECRET,
    recovery_enter_shares,
)

pytestmark = pytest.mark.skip_t1

MNEMONIC_SLIP39_BASIC_20_1of1 = [
    "academic academic academic academic academic academic academic academic academic academic academic academic academic academic academic academic academic rebuild aquatic spew"
]


MNEMONIC_SLIP39_BASIC_33_2of5 = [
    "hobo romp academic axis august founder knife legal recover alien expect emphasis loan kitchen involve teacher capture rebuild trial numb spider forward ladle lying voter typical security quantity hawk legs idle leaves gasoline",
    "hobo romp academic agency ancestor industry argue sister scene midst graduate profile numb paid headset airport daisy flame express scene usual welcome quick silent downtown oral critical step remove says rhythm venture aunt",
]

VECTORS = (
    (MNEMONIC_SLIP39_BASIC_20_3of6, MNEMONIC_SLIP39_BASIC_20_3of6_SECRET),
    (
        MNEMONIC_SLIP39_BASIC_33_2of5,
        "b770e0da1363247652de97a39bdbf2463be087848d709ecbf28e84508e31202a",
    ),
)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.parametrize("shares, secret", VECTORS)
def test_secret(client, shares, secret):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        # run recovery flow
        yield from recovery_enter_shares(debug, shares)

    with client:
        client.set_input_flow(input_flow)
        ret = device.recover(client, pin_protection=False, label="label")

    # Workflow succesfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    assert client.features.backup_type is messages.BackupType.Slip39_Basic

    # Check mnemonic
    assert debug.state().mnemonic_secret.hex() == secret


@pytest.mark.setup_client(uninitialized=True)
def test_recover_with_pin_passphrase(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        yield  # Enter PIN
        debug.input("654")
        yield  # Enter PIN again
        debug.input("654")
        # Proceed with recovery
        yield from recovery_enter_shares(debug, MNEMONIC_SLIP39_BASIC_20_3of6)

    with client:
        client.set_input_flow(input_flow)
        ret = device.recover(
            client, pin_protection=True, passphrase_protection=True, label="label"
        )

    # Workflow succesfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.pin_protection is True
    assert client.features.passphrase_protection is True
    assert client.features.backup_type is messages.BackupType.Slip39_Basic


@pytest.mark.setup_client(uninitialized=True)
def test_abort(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        yield  # Homescreen - abort process
        debug.press_no()
        yield  # Homescreen - confirm abort
        debug.press_yes()

    with client:
        client.set_input_flow(input_flow)
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is False


@pytest.mark.setup_client(uninitialized=True)
def test_noabort(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        yield  # Homescreen - abort process
        debug.press_no()
        yield  # Homescreen - go back to process
        debug.press_no()
        yield from recovery_enter_shares(debug, MNEMONIC_SLIP39_BASIC_20_3of6)

    with client:
        client.set_input_flow(input_flow)
        device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is True


@pytest.mark.setup_client(uninitialized=True)
def test_ask_word_number(client):
    debug = client.debug

    def input_flow_retry_first():
        yield  # Confirm Recovery
        debug.press_yes()
        yield  # Homescreen - start process
        debug.press_yes()
        yield  # Enter number of words
        debug.input("20")
        yield  # Homescreen - proceed to share entry
        debug.press_yes()
        yield  # Enter first share
        for _ in range(20):
            debug.input("slush")

        br = yield  # Invalid share
        assert br.code == messages.ButtonRequestType.Warning
        debug.press_yes()

        yield  # Homescreen - start process
        debug.press_yes()
        yield  # Enter number of words
        debug.input("33")
        yield  # Homescreen - proceed to share entry
        debug.press_yes()
        yield  # Enter first share
        for _ in range(33):
            debug.input("slush")

        br = yield  # Invalid share
        assert br.code == messages.ButtonRequestType.Warning
        debug.press_yes()

        yield  # Homescreen
        debug.press_no()
        yield  # Confirm abort
        debug.press_yes()

    with client:
        client.set_input_flow(input_flow_retry_first)
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is False

    def input_flow_retry_second():
        yield  # Confirm Recovery
        debug.press_yes()
        yield  # Homescreen - start process
        debug.press_yes()
        yield  # Enter number of words
        debug.input("20")
        yield  # Homescreen - proceed to share entry
        debug.press_yes()
        yield  # Enter first share
        share = MNEMONIC_SLIP39_BASIC_20_3of6[0].split(" ")
        for word in share:
            debug.input(word)

        yield  # More shares needed
        debug.press_yes()

        yield  # Enter another share
        share = share[:3] + ["slush"] * 17
        for word in share:
            debug.input(word)

        br = yield  # Invalid share
        assert br.code == messages.ButtonRequestType.Warning
        debug.press_yes()

        yield  # Proceed to next share
        share = MNEMONIC_SLIP39_BASIC_20_3of6[1].split(" ")
        for word in share:
            debug.input(word)

        yield  # More shares needed
        debug.press_no()
        yield  # Confirm abort
        debug.press_yes()

    with client:
        client.set_input_flow(input_flow_retry_second)
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is False


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.parametrize("nth_word", range(3))
def test_wrong_nth_word(client, nth_word):
    debug = client.debug
    share = MNEMONIC_SLIP39_BASIC_20_3of6[0].split(" ")

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        yield  # Homescreen - start process
        debug.press_yes()
        yield  # Enter number of words
        debug.input(str(len(share)))
        yield  # Homescreen - proceed to share entry
        debug.press_yes()
        yield  # Enter first share
        for word in share:
            debug.input(word)

        yield  # Continue to next share
        debug.press_yes()
        yield  # Enter next share
        for i, word in enumerate(share):
            if i < nth_word:
                debug.input(word)
            else:
                debug.input(share[-1])
                break

        br = yield
        assert br.code == messages.ButtonRequestType.Warning

        client.cancel()

    with client:
        client.set_input_flow(input_flow)
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")


@pytest.mark.setup_client(uninitialized=True)
def test_same_share(client):
    debug = client.debug
    first_share = MNEMONIC_SLIP39_BASIC_20_3of6[0].split(" ")
    # second share is first 4 words of first
    second_share = MNEMONIC_SLIP39_BASIC_20_3of6[0].split(" ")[:4]

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        yield  # Homescreen - start process
        debug.press_yes()
        yield  # Enter number of words
        debug.input(str(len(first_share)))
        yield  # Homescreen - proceed to share entry
        debug.press_yes()
        yield  # Enter first share
        for word in first_share:
            debug.input(word)

        yield  # Continue to next share
        debug.press_yes()
        yield  # Enter next share
        for word in second_share:
            debug.input(word)

        br = yield
        assert br.code == messages.ButtonRequestType.Warning

        client.cancel()

    with client:
        client.set_input_flow(input_flow)
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")


@pytest.mark.setup_client(uninitialized=True)
def test_1of1(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        # Proceed with recovery
        yield from recovery_enter_shares(
            debug, MNEMONIC_SLIP39_BASIC_20_1of1, groups=False
        )

    with client:
        client.set_input_flow(input_flow)
        ret = device.recover(
            client, pin_protection=False, passphrase_protection=False, label="label"
        )

    # Workflow succesfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.initialized is True
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    assert client.features.backup_type is messages.BackupType.Slip39_Basic
