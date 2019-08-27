import pytest

from trezorlib import device, messages
from trezorlib.exceptions import TrezorFailure

from .conftest import setup_client

pytestmark = pytest.mark.skip_t1

SHARES_20_2of3_2of3_GROUPS = [
    "gesture negative ceramic leaf device fantasy style ceramic safari keyboard thumb total smug cage plunge aunt favorite lizard intend peanut",
    "gesture negative acrobat leaf craft sidewalk adorn spider submit bumpy alcohol cards salon making prune decorate smoking image corner method",
    "gesture negative acrobat lily bishop voting humidity rhyme parcel crunch elephant victim dish mailman triumph agree episode wealthy mayor beam",
    "gesture negative beard leaf deadline stadium vegan employer armed marathon alien lunar broken edge justice military endorse diet sweater either",
    "gesture negative beard lily desert belong speak realize explain bolt diet believe response counter medal luck wits glance remove ending",
]

INVALID_SHARES_20_2of3_2of3_GROUPS = [
    "chest garlic acrobat leaf diploma thank soul predator grant laundry camera license language likely slim twice amount rich total carve",
    "chest garlic acrobat lily adequate dwarf genius wolf faint nylon scroll national necklace leader pants literary lift axle watch midst",
    "chest garlic beard leaf coastal album dramatic learn identify angry dismiss goat plan describe round writing primary surprise sprinkle orbit",
    "chest garlic beard lily burden pistol retreat pickup emphasis large gesture hand eyebrow season pleasure genuine election skunk champion income",
]


@setup_client(mnemonic=SHARES_20_2of3_2of3_GROUPS[1:5], passphrase=False)
def test_2of3_dryrun(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Dryrun
        debug.press_yes()
        # run recovery flow
        yield from enter_all_shares(debug, SHARES_20_2of3_2of3_GROUPS)

    with client:
        client.set_input_flow(input_flow)
        ret = device.recover(
            client,
            passphrase_protection=False,
            pin_protection=False,
            label="label",
            language="english",
            dry_run=True,
        )

    # Dry run was successful
    assert ret == messages.Success(
        message="The seed is valid and matches the one in the device"
    )


@setup_client(mnemonic=SHARES_20_2of3_2of3_GROUPS[1:5], passphrase=True)
def test_2of3_invalid_seed_dryrun(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Dryrun
        debug.press_yes()
        # run recovery flow
        yield from enter_all_shares(debug, INVALID_SHARES_20_2of3_2of3_GROUPS)

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
