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

import json
from pathlib import Path

import pytest

from trezorlib import btc, tools
from trezorlib.messages import ButtonRequestType as B

# fmt: off
#                1      2     3    4      5      6      7     8      9    10    11    12
MNEMONIC12 = "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
MNEMONIC_SLIP39_BASIC_20_3of6 = [
    "extra extend academic bishop cricket bundle tofu goat apart victim enlarge program behavior permit course armed jerky faint language modern",
    "extra extend academic acne away best indicate impact square oasis prospect painting voting guest either argue username racism enemy eclipse",
    "extra extend academic arcade born dive legal hush gross briefing talent drug much home firefly toxic analysis idea umbrella slice",
]
MNEMONIC_SLIP39_BASIC_20_3of6_SECRET = "491b795b80fc21ccdf466c0fbc98c8fc"
# Shamir shares (128 bits, 2 groups from 1 of 1, 1 of 1, 3 of 5, 2 of 6)
MNEMONIC_SLIP39_ADVANCED_20 = [
    "eraser senior beard romp adorn nuclear spill corner cradle style ancient family general leader ambition exchange unusual garlic promise voice",
    "eraser senior ceramic snake clay various huge numb argue hesitate auction category timber browser greatest hanger petition script leaf pickup",
    "eraser senior ceramic shaft dynamic become junior wrist silver peasant force math alto coal amazing segment yelp velvet image paces",
    "eraser senior ceramic round column hawk trust auction smug shame alive greatest sheriff living perfect corner chest sled fumes adequate",
]
# Shamir shares (256 bits, 2 groups from 1 of 1, 1 of 1, 3 of 5, 2 of 6):
MNEMONIC_SLIP39_ADVANCED_33 = [
    "wildlife deal beard romp alcohol space mild usual clothes union nuclear testify course research heat listen task location thank hospital slice smell failure fawn helpful priest ambition average recover lecture process dough stadium",
    "wildlife deal acrobat romp anxiety axis starting require metric flexible geology game drove editor edge screw helpful have huge holy making pitch unknown carve holiday numb glasses survive already tenant adapt goat fangs",
]
# External entropy mocked as received from trezorlib.
EXTERNAL_ENTROPY = b"zlutoucky kun upel divoke ody" * 2
# fmt: on

TEST_ADDRESS_N = tools.parse_path("m/44h/1h/0h/0/0")
COMMON_FIXTURES_DIR = (
    Path(__file__).parent.resolve().parent / "common" / "tests" / "fixtures"
)


def parametrize_using_common_fixtures(*paths):
    fixtures = []
    for path in paths:
        fixtures.append(json.loads((COMMON_FIXTURES_DIR / path).read_text()))

    tests = []
    for fixture in fixtures:
        for test in fixture["tests"]:
            tests.append(
                pytest.param(
                    test["parameters"],
                    test["result"],
                    marks=pytest.mark.setup_client(
                        passphrase=fixture["setup"]["passphrase"],
                        mnemonic=fixture["setup"]["mnemonic"],
                    ),
                )
            )

    return pytest.mark.parametrize("parameters, result", tests)


def generate_entropy(strength, internal_entropy, external_entropy):
    """
    strength - length of produced seed. One of 128, 192, 256
    random - binary stream of random data from external HRNG
    """
    import hashlib

    if strength not in (128, 192, 256):
        raise ValueError("Invalid strength")

    if not internal_entropy:
        raise ValueError("Internal entropy is not provided")

    if len(internal_entropy) < 32:
        raise ValueError("Internal entropy too short")

    if not external_entropy:
        raise ValueError("External entropy is not provided")

    if len(external_entropy) < 32:
        raise ValueError("External entropy too short")

    entropy = hashlib.sha256(internal_entropy + external_entropy).digest()
    entropy_stripped = entropy[: strength // 8]

    if len(entropy_stripped) * 8 != strength:
        raise ValueError("Entropy length mismatch")

    return entropy_stripped


def recovery_enter_shares(debug, shares, groups=False):
    """Perform the recovery flow for a set of Shamir shares.

    For use in an input flow function.
    Example:

    def input_flow():
        yield  # start recovery
        client.debug.press_yes()
        yield from recovery_enter_shares(client.debug, SOME_SHARES)
    """
    word_count = len(shares[0].split(" "))

    # Homescreen - proceed to word number selection
    yield
    debug.press_yes()
    # Input word number
    code = yield
    assert code == B.MnemonicWordCount
    debug.input(str(word_count))
    # Homescreen - proceed to share entry
    yield
    debug.press_yes()
    # Enter shares
    for index, share in enumerate(shares):
        code = yield
        assert code == B.MnemonicInput
        # Enter mnemonic words
        for word in share.split(" "):
            debug.input(word)

        if groups:
            # Confirm share entered
            yield
            debug.press_yes()

        # Homescreen - continue
        # or Homescreen - confirm success
        yield
        debug.press_yes()


def click_through(debug, screens, code=None):
    """Click through N dialog screens.

    For use in an input flow function.
    Example:

    def input_flow():
        # 1. Confirm reset
        # 2. Backup your seed
        # 3. Confirm warning
        # 4. Shares info
        yield from click_through(client.debug, screens=4, code=B.ResetDevice)
    """
    for _ in range(screens):
        received = yield
        if code is not None:
            assert received == code
        debug.press_yes()


def read_and_confirm_mnemonic(debug, words):
    """Read a given number of mnemonic words from Trezor T screen and correctly
    answer confirmation questions. Return the full mnemonic.

    For use in an input flow function.
    Example:

    def input_flow():
        yield from click_through(client.debug, screens=3)

        yield  # confirm mnemonic entry
        mnemonic = read_and_confirm_mnemonic(client.debug, words=20)
    """
    mnemonic = []
    while True:
        mnemonic.extend(debug.read_reset_word().split())
        if len(mnemonic) < words:
            debug.swipe_up()
        else:
            # last page is confirmation
            debug.press_yes()
            break

    # check share
    for _ in range(3):
        index = debug.read_reset_word_pos()
        debug.input(mnemonic[index])

    return " ".join(mnemonic)


def get_test_address(client):
    """Fetch a testnet address on a fixed path. Useful to make a pin/passphrase
    protected call, or to identify the root secret (seed+passphrase)"""
    return btc.get_address(client, "Testnet", TEST_ADDRESS_N)
