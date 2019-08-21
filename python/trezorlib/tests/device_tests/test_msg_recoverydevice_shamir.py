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

import time

import pytest

from trezorlib import device, exceptions, messages

pytestmark = pytest.mark.skip_t1

SHARES_20_3of6 = [
    "extra extend academic bishop cricket bundle tofu goat apart victim enlarge program behavior permit course armed jerky faint language modern",
    "extra extend academic acne away best indicate impact square oasis prospect painting voting guest either argue username racism enemy eclipse",
    "extra extend academic arcade born dive legal hush gross briefing talent drug much home firefly toxic analysis idea umbrella slice",
]

SHARES_33_2of5 = [
    "hobo romp academic axis august founder knife legal recover alien expect emphasis loan kitchen involve teacher capture rebuild trial numb spider forward ladle lying voter typical security quantity hawk legs idle leaves gasoline",
    "hobo romp academic agency ancestor industry argue sister scene midst graduate profile numb paid headset airport daisy flame express scene usual welcome quick silent downtown oral critical step remove says rhythm venture aunt",
]


VECTORS = (
    (SHARES_20_3of6, "491b795b80fc21ccdf466c0fbc98c8fc"),
    (
        SHARES_33_2of5,
        "b770e0da1363247652de97a39bdbf2463be087848d709ecbf28e84508e31202a",
    ),
)


def enter_all_shares(debug, shares):
    word_count = len(shares[0].split(" "))

    # Homescreen - proceed to word number selection
    yield
    debug.press_yes()
    # Input word number
    code = yield
    assert code == messages.ButtonRequestType.MnemonicWordCount
    debug.input(str(word_count))
    # Homescreen - proceed to share entry
    yield
    debug.press_yes()
    # Enter shares
    for share in shares:
        code = yield
        assert code == messages.ButtonRequestType.MnemonicInput
        # Enter mnemonic words
        for word in share.split(" "):
            time.sleep(1)
            debug.input(word)

        # Homescreen - continue
        # or Homescreen - confirm success
        yield
        debug.press_yes()


@pytest.mark.parametrize("shares, secret", VECTORS)
def test_secret(client, shares, secret):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        # run recovery flow
        yield from enter_all_shares(debug, shares)

    with client:
        client.set_input_flow(input_flow)
        ret = device.recover(client, pin_protection=False, label="label")

    # Workflow succesfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False

    # Check mnemonic
    assert debug.read_mnemonic_secret().hex() == secret


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
        yield from enter_all_shares(debug, SHARES_20_3of6)

    with client:
        client.set_input_flow(input_flow)
        ret = device.recover(
            client, pin_protection=True, passphrase_protection=True, label="label"
        )

    # Workflow succesfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.pin_protection is True
    assert client.features.passphrase_protection is True


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


def test_noabort(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        yield  # Homescreen - abort process
        debug.press_no()
        yield  # Homescreen - go back to process
        debug.press_no()
        yield from enter_all_shares(debug, SHARES_20_3of6)

    with client:
        client.set_input_flow(input_flow)
        device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is True


@pytest.mark.parametrize("nth_word", range(3))
def test_wrong_nth_word(client, nth_word):
    debug = client.debug
    share = SHARES_20_3of6[0].split(" ")

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
            time.sleep(1)
            debug.input(word)

        yield  # Continue to next share
        debug.press_yes()
        yield  # Enter next share
        for i, word in enumerate(share):
            time.sleep(1)
            if i < nth_word:
                debug.input(word)
            else:
                debug.input(share[-1])
                break

        code = yield
        assert code == messages.ButtonRequestType.Warning

        client.cancel()

    with client:
        client.set_input_flow(input_flow)
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")


def test_same_share(client):
    debug = client.debug
    first_share = SHARES_20_3of6[0].split(" ")
    # second share is first 4 words of first
    second_share = SHARES_20_3of6[0].split(" ")[:4]

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
            time.sleep(1)
            debug.input(word)

        yield  # Continue to next share
        debug.press_yes()
        yield  # Enter next share
        for word in second_share:
            time.sleep(1)
            debug.input(word)

        code = yield
        assert code == messages.ButtonRequestType.Warning

        client.cancel()

    with client:
        client.set_input_flow(input_flow)
        with pytest.raises(exceptions.Cancelled):
            device.recover(client, pin_protection=False, label="label")
