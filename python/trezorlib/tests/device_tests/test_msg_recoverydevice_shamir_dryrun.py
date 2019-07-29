import time

import pytest

from trezorlib import device, messages
from trezorlib.exceptions import TrezorFailure

from .conftest import setup_client

pytestmark = pytest.mark.skip_t1

SHARES_20_2of3 = [
    "crush merchant academic acid dream decision orbit smug trend trust painting slice glad crunch veteran lunch friar satoshi engage aquatic",
    "crush merchant academic agency devote eyebrow disaster island deploy flip toxic budget numerous airport loyalty fitness resident learn sympathy daughter",
    "crush merchant academic always course verdict rescue paces fridge museum energy solution space ladybug junction national biology game fawn coal",
]

INVALID_SHARES_20_2of3 = [
    "gesture necklace academic acid civil round fiber buyer swing ancient jerky kitchen chest dining enjoy tension museum increase various rebuild",
    "gesture necklace academic agency decrease justice ounce dragon shaped unknown material answer dress wrote smell family squeeze diet angry husband",
]


@setup_client(mnemonic=SHARES_20_2of3[0:2], passphrase=True)
def test_2of3_dryrun(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Dryrun
        debug.press_yes()
        # run recovery flow
        yield from enter_all_shares(debug, SHARES_20_2of3[1:3])

    with client:
        client.set_input_flow(input_flow)
        ret = device.recover(
            client,
            passphrase_protection=False,
            pin_protection=False,
            label="label",
            language="english",
            dry_run=True,
            type=messages.ResetDeviceBackupType.Slip39_Single_Group,
        )

    # Dry run was successful
    assert ret == messages.Success(
        message="The seed is valid and matches the one in the device"
    )


@setup_client(mnemonic=SHARES_20_2of3[0:2], passphrase=True)
def test_2of3_invalid_seed_dryrun(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Dryrun
        debug.press_yes()
        # run recovery flow
        yield from enter_all_shares(debug, INVALID_SHARES_20_2of3)

    # test fails because of different seed on device
    with client, pytest.raises(
        TrezorFailure, match=r"The seed does not match the one in the device"
    ):
        client.set_input_flow(input_flow)
        device.recover(
            client,
            passphrase_protection=False,
            pin_protection=False,
            label="label",
            language="english",
            dry_run=True,
            type=messages.ResetDeviceBackupType.Slip39_Single_Group,
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
