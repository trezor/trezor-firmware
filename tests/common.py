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
import time
from pathlib import Path
from typing import TYPE_CHECKING, Generator, Optional
from unittest import mock

import pytest

from trezorlib import btc, tools
from trezorlib.messages import ButtonRequestType

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, TrezorClientDebugLink as Client
    from trezorlib.messages import ButtonRequest
    from _pytest.mark.structures import MarkDecorator


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
    Path(__file__).resolve().parent.parent / "common" / "tests" / "fixtures"
)

# So that all the random things are consistent
MOCK_OS_URANDOM = mock.Mock(return_value=EXTERNAL_ENTROPY)
WITH_MOCK_URANDOM = mock.patch("os.urandom", MOCK_OS_URANDOM)


def parametrize_using_common_fixtures(*paths: str) -> "MarkDecorator":
    fixtures = []
    for path in paths:
        fixtures.append(json.loads((COMMON_FIXTURES_DIR / path).read_text()))

    tests = []
    for fixture in fixtures:
        for test in fixture["tests"]:
            test_id = test.get("name")
            if not test_id:
                test_id = test.get("description")
                if test_id is not None:
                    test_id = test_id.lower().replace(" ", "_")

            tests.append(
                pytest.param(
                    test["parameters"],
                    test["result"],
                    marks=pytest.mark.setup_client(
                        passphrase=fixture["setup"]["passphrase"],
                        mnemonic=fixture["setup"]["mnemonic"],
                    ),
                    id=test_id,
                )
            )

    return pytest.mark.parametrize("parameters, result", tests)


def generate_entropy(
    strength: int, internal_entropy: bytes, external_entropy: bytes
) -> bytes:
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


def recovery_enter_shares(
    debug: "DebugLink",
    shares: list[str],
    groups: bool = False,
    click_info: bool = False,
) -> Generator[None, "ButtonRequest", None]:
    if debug.model == "T":
        yield from recovery_enter_shares_tt(
            debug, shares, groups=groups, click_info=click_info
        )
    elif debug.model == "R":
        yield from recovery_enter_shares_tr(debug, shares, groups=groups)
    else:
        raise ValueError(f"Unknown model: {debug.model}")


def recovery_enter_shares_tt(
    debug: "DebugLink",
    shares: list[str],
    groups: bool = False,
    click_info: bool = False,
) -> Generator[None, "ButtonRequest", None]:
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
    br = yield
    assert br.code == ButtonRequestType.MnemonicWordCount
    debug.input(str(word_count))
    # Homescreen - proceed to share entry
    yield
    debug.press_yes()
    # Enter shares
    for share in shares:
        br = yield
        assert br.code == ButtonRequestType.MnemonicInput
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

        if click_info:
            # Moving through the INFO button
            debug.press_info()
            yield
            debug.swipe_up()
            debug.press_yes()

        # Finishing with current share
        debug.press_yes()


def recovery_enter_shares_tr(
    debug: "DebugLink",
    shares: list[str],
    groups: bool = False,
) -> Generator[None, "ButtonRequest", None]:
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
    br = yield
    assert br.code == ButtonRequestType.MnemonicWordCount
    debug.input(str(word_count))
    # Homescreen - proceed to share entry
    yield
    debug.press_yes()

    # Enter shares
    for share in shares:
        br = yield
        assert br.code == ButtonRequestType.RecoveryHomepage

        # Word entering
        yield
        debug.press_yes()

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

        # Finishing with current share
        debug.press_yes()

    yield


def click_through(
    debug: "DebugLink", screens: int, code: Optional[ButtonRequestType] = None
) -> Generator[None, "ButtonRequest", None]:
    """Click through N dialog screens.

    For use in an input flow function.
    Example:

    def input_flow():
        # 1. Confirm reset
        # 2. Backup your seed
        # 3. Confirm warning
        # 4. Shares info
        yield from click_through(client.debug, screens=4, code=ButtonRequestType.ResetDevice)
    """
    for _ in range(screens):
        received = yield
        if code is not None:
            assert received.code == code
        debug.press_yes()


def read_and_confirm_mnemonic(
    debug: "DebugLink", choose_wrong: bool = False
) -> Generator[None, "ButtonRequest", Optional[str]]:
    # TODO: these are very similar, reuse some code
    if debug.model == "T":
        mnemonic = yield from read_and_confirm_mnemonic_tt(debug, choose_wrong)
    elif debug.model == "R":
        mnemonic = yield from read_and_confirm_mnemonic_tr(debug, choose_wrong)
    else:
        raise ValueError(f"Unknown model: {debug.model}")

    return mnemonic


def read_and_confirm_mnemonic_tt(
    debug: "DebugLink", choose_wrong: bool = False
) -> Generator[None, "ButtonRequest", Optional[str]]:
    """Read a given number of mnemonic words from Trezor T screen and correctly
    answer confirmation questions. Return the full mnemonic.

    For use in an input flow function.
    Example:

    def input_flow():
        yield from click_through(client.debug, screens=3)

        mnemonic = yield from read_and_confirm_mnemonic(client.debug)
    """
    mnemonic: list[str] = []
    br = yield
    assert br.pages is not None

    for i in range(br.pages):
        if i == 0:
            layout = debug.wait_layout()
        else:
            layout = debug.read_layout()
        words = layout.seed_words()
        mnemonic.extend(words)
        # Not swiping on the last page
        if i < br.pages - 1:
            debug.swipe_up(wait=True)

    debug.press_yes()

    # check share
    for i in range(3):
        index = debug.read_reset_word_pos()
        if choose_wrong:
            debug.input(mnemonic[(index + 1) % len(mnemonic)])
            return None
        else:
            debug.input(mnemonic[index])

    return " ".join(mnemonic)


def read_and_confirm_mnemonic_tr(
    debug: "DebugLink", choose_wrong: bool = False
) -> Generator[None, "ButtonRequest", Optional[str]]:
    mnemonic: list[str] = []
    br = yield
    assert br.pages is not None
    for _ in range(br.pages - 1):
        layout = debug.wait_layout()
        words = layout.seed_words()
        mnemonic.extend(words)
        debug.press_right()
    debug.press_right()

    yield  # Select correct words...
    debug.press_right()

    for _ in range(3):
        index = debug.read_reset_word_pos()
        if choose_wrong:
            debug.input(mnemonic[(index + 1) % len(mnemonic)])
            return None
        else:
            debug.input(mnemonic[index])

    return " ".join(mnemonic)


def click_info_button(debug: "DebugLink"):
    """Click Shamir backup info button and return back."""
    debug.press_info()
    yield  # Info screen with text
    debug.press_yes()


def check_PIN_backoff_time(attempts: int, start: float) -> None:
    """Helper to assert the exponentially growing delay after incorrect PIN attempts"""
    expected = (2**attempts) - 1
    got = round(time.time() - start, 2)
    assert got >= expected


def get_test_address(client: "Client") -> str:
    """Fetch a testnet address on a fixed path. Useful to make a pin/passphrase
    protected call, or to identify the root secret (seed+passphrase)"""
    return btc.get_address(client, "Testnet", TEST_ADDRESS_N)


def get_text_from_paginated_screen(client: "Client", screen_count: int) -> str:
    """Aggregating screen text from more pages into one string."""
    text: str = client.debug.wait_layout().str_content
    for _ in range(screen_count - 1):
        client.debug.swipe_up()
        text += client.debug.wait_layout().str_content

    return text
