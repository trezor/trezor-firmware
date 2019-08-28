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

pytestmark = pytest.mark.skip_t1

SHARES_20_2of3_2of3_GROUPS = [
    "gesture negative ceramic leaf device fantasy style ceramic safari keyboard thumb total smug cage plunge aunt favorite lizard intend peanut",
    "gesture negative acrobat leaf craft sidewalk adorn spider submit bumpy alcohol cards salon making prune decorate smoking image corner method",
    "gesture negative acrobat lily bishop voting humidity rhyme parcel crunch elephant victim dish mailman triumph agree episode wealthy mayor beam",
    "gesture negative beard leaf deadline stadium vegan employer armed marathon alien lunar broken edge justice military endorse diet sweater either",
    "gesture negative beard lily desert belong speak realize explain bolt diet believe response counter medal luck wits glance remove ending",
]


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
    for index, share in enumerate(shares):
        if index >= 1:
            # confirm remaining shares
            debug.swipe_down()
            code = yield
            assert code == messages.ButtonRequestType.Other
            debug.press_yes()
        code = yield
        assert code == messages.ButtonRequestType.MnemonicInput
        # Enter mnemonic words
        for word in share.split(" "):
            debug.input(word)

        # Confirm share entered
        yield
        debug.press_yes()

        # Homescreen - continue
        # or Homescreen - confirm success
        yield
        debug.press_yes()


@pytest.mark.setup_client(uninitialized=True)
def test_recover_no_pin_no_passphrase(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Recovery
        debug.press_yes()
        # Proceed with recovery
        yield from enter_all_shares(debug, SHARES_20_2of3_2of3_GROUPS)

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
        yield from enter_all_shares(debug, SHARES_20_2of3_2of3_GROUPS)

    with client:
        client.set_input_flow(input_flow)
        device.recover(client, pin_protection=False, label="label")
        client.init_device()
        assert client.features.initialized is True
