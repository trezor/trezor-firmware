import pytest

from trezorlib import device, messages
from trezorlib.exceptions import TrezorFailure

from .common import MNEMONIC_SHAMIR_20_2of3_2of3_GROUPS, recovery_enter_shares

pytestmark = pytest.mark.skip_t1

INVALID_SHARES_20_2of3_2of3_GROUPS = [
    "chest garlic acrobat leaf diploma thank soul predator grant laundry camera license language likely slim twice amount rich total carve",
    "chest garlic acrobat lily adequate dwarf genius wolf faint nylon scroll national necklace leader pants literary lift axle watch midst",
    "chest garlic beard leaf coastal album dramatic learn identify angry dismiss goat plan describe round writing primary surprise sprinkle orbit",
    "chest garlic beard lily burden pistol retreat pickup emphasis large gesture hand eyebrow season pleasure genuine election skunk champion income",
]


@pytest.mark.setup_client(
    mnemonic=MNEMONIC_SHAMIR_20_2of3_2of3_GROUPS[1:5], passphrase=False
)
def test_2of3_dryrun(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Dryrun
        debug.press_yes()
        # run recovery flow
        yield from recovery_enter_shares(
            debug, MNEMONIC_SHAMIR_20_2of3_2of3_GROUPS, groups=True
        )

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


@pytest.mark.setup_client(
    mnemonic=MNEMONIC_SHAMIR_20_2of3_2of3_GROUPS[1:5], passphrase=True
)
def test_2of3_invalid_seed_dryrun(client):
    debug = client.debug

    def input_flow():
        yield  # Confirm Dryrun
        debug.press_yes()
        # run recovery flow
        yield from recovery_enter_shares(
            debug, INVALID_SHARES_20_2of3_2of3_GROUPS, groups=True
        )

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
