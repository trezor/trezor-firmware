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

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator, Optional
from unittest import mock

import pytest

from trezorlib import btc, messages, models, tools
from trezorlib.debuglink import LayoutType

if TYPE_CHECKING:
    from _pytest.mark.structures import MarkDecorator

    from trezorlib.debuglink import DebugLink
    from trezorlib.debuglink import TrezorClientDebugLink as Client
    from trezorlib.messages import ButtonRequest

PRIVATE_KEYS_DEV = [byte * 32 for byte in (b"\xdd", b"\xde", b"\xdf")]

BRGeneratorType = Generator[None, messages.ButtonRequest, None]


# fmt: off
#                1      2     3    4      5      6      7     8      9    10    11    12
MNEMONIC12 = "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
MNEMONIC_SLIP39_BASIC_20_3of6 = [
    "extra extend academic bishop cricket bundle tofu goat apart victim enlarge program behavior permit course armed jerky faint language modern",
    "extra extend academic acne away best indicate impact square oasis prospect painting voting guest either argue username racism enemy eclipse",
    "extra extend academic arcade born dive legal hush gross briefing talent drug much home firefly toxic analysis idea umbrella slice",
]
MNEMONIC_SLIP39_BASIC_20_3of6_SECRET = "491b795b80fc21ccdf466c0fbc98c8fc"
MNEMONIC_SLIP39_BASIC_EXT_20_2of3 = [
    "enemy favorite academic acid cowboy phrase havoc level response walnut budget painting inside trash adjust froth kitchen learn tidy punish",
    "enemy favorite academic always academic sniff script carpet romp kind promise scatter center unfair training emphasis evening belong fake enforce",
]
MNEMONIC_SLIP39_BASIC_EXT_20_2of3_SECRET = "644c905b0c4da21692f06fff3ed8b3e1"
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
MNEMONIC_SLIP39_CUSTOM_1of1 = ["tolerate flexible academic academic average dwarf square home promise aspect temple cluster roster forward hand unfair tenant emperor ceramic element forget perfect knit adapt review usual formal receiver typical pleasure duke yield party"]
MNEMONIC_SLIP39_CUSTOM_SECRET = "3439316237393562383066633231636364663436366330666263393863386663"

MNEMONIC_SLIP39_SINGLE_EXT_20 = ["academic again academic academic academic academic academic academic academic academic academic academic academic academic academic academic academic pecan provide remember"]

# External entropy mocked as received from trezorlib.
EXTERNAL_ENTROPY = b"zlutoucky kun upel divoke ody" * 2
# fmt: on

TEST_ADDRESS_N = tools.parse_path("m/44h/1h/0h/0/0")
COMMON_FIXTURES_DIR = (
    Path(__file__).resolve().parent.parent / "common" / "tests" / "fixtures"
)

# So that all the random things are consistent
MOCK_GET_ENTROPY = mock.Mock(return_value=EXTERNAL_ENTROPY)


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

            skip_models = test.get("skip_models", [])
            skiplist = []
            # TODO: genericify this
            for skip_model in skip_models:
                if skip_model in ("t1", "t1b1"):
                    skiplist.append(models.T1B1)
                if skip_model in ("t2", "t2t1"):
                    skiplist.append(models.T2T1)
                if skip_model in ("tr", "t2b1"):
                    skiplist.append(models.T2B1)
                    skiplist.append(models.T3B1)
                if skip_model == "t3t1":
                    skiplist.append(models.T3T1)
            if skiplist:
                skip_marks = [pytest.mark.models(skip=skiplist)]
            else:
                skip_marks = []

            tests.append(
                pytest.param(
                    test["parameters"],
                    test["result"],
                    marks=[
                        pytest.mark.setup_client(
                            passphrase=fixture["setup"]["passphrase"],
                            mnemonic=fixture["setup"]["mnemonic"],
                        )
                    ]
                    + skip_marks,
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


def click_through(
    debug: "DebugLink", screens: int, code: Optional[messages.ButtonRequestType] = None
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
    """Read mnemonic words from the screen and answer
    confirmation questions.
    Return the full mnemonic or None if `choose_wrong` is True.

    For use in an input flow function.
    Example:

    def input_flow():
        yield from click_through(client.debug, screens=3)

        mnemonic = yield from read_and_confirm_mnemonic(client.debug)
    """
    if debug.layout_type is LayoutType.Bolt:
        mnemonic = yield from read_mnemonic_from_screen_bolt(debug)
    elif debug.layout_type is LayoutType.Caesar:
        mnemonic = yield from read_mnemonic_from_screen_caesar(debug)
    elif debug.layout_type is LayoutType.Delizia:
        mnemonic = yield from read_mnemonic_from_screen_delizia(debug)
    else:
        raise ValueError(f"Unknown model: {debug.layout_type}")

    if not check_share(debug, mnemonic, choose_wrong):
        return None
    return " ".join(mnemonic)


def read_mnemonic_from_screen_bolt(
    debug: "DebugLink",
) -> Generator[None, "ButtonRequest", list[str]]:
    mnemonic: list[str] = []
    br = yield
    assert br.pages is not None

    for i in range(br.pages):
        words = debug.read_layout().seed_words()
        mnemonic.extend(words)
        # Not swiping on the last page
        if i < br.pages - 1:
            debug.swipe_up()

    debug.press_yes()
    return mnemonic


def read_mnemonic_from_screen_caesar(
    debug: "DebugLink",
) -> Generator[None, "ButtonRequest", list[str]]:
    mnemonic: list[str] = []
    yield  # write down all 12 words in order
    debug.press_yes()
    br = yield
    assert br.pages is not None
    for _ in range(br.pages - 1):
        layout = debug.read_layout()
        words = layout.seed_words()
        mnemonic.extend(words)
        debug.press_right()
    debug.press_yes()

    yield  # Select correct words...
    debug.press_right()
    return mnemonic


def read_mnemonic_from_screen_delizia(
    debug: "DebugLink",
) -> Generator[None, "ButtonRequest", list[str]]:
    mnemonic: list[str] = []
    br = yield
    assert br.pages is not None

    debug.read_layout()
    debug.swipe_up()

    for _ in range(br.pages - 2):
        words = debug.read_layout().seed_words()
        mnemonic.extend(words)
        debug.swipe_up()

    debug.read_layout()
    debug.press_yes()

    return mnemonic


def check_share(
    debug: "DebugLink", mnemonic: list[str], choose_wrong: bool = False
) -> bool:
    """
    Given the mnemonic word list, proceed with the backup check:
    three rounds of `Select word X of Y` choices.
    """
    re_num_of_word = r"\d+"
    for _ in range(3):
        if debug.layout_type is LayoutType.Bolt:
            # T2T1 has position as the first number in the text
            word_pos_match = re.search(
                re_num_of_word, debug.read_layout().text_content()
            )
        elif debug.layout_type is LayoutType.Caesar:
            # other models have the instruction in the title/subtitle
            word_pos_match = re.search(re_num_of_word, debug.read_layout().title())
        elif debug.layout_type is LayoutType.Delizia:
            word_pos_match = re.search(re_num_of_word, debug.read_layout().subtitle())
        else:
            word_pos_match = None

        assert word_pos_match is not None
        word_pos = int(word_pos_match.group(0))

        index = word_pos - 1
        if choose_wrong:
            debug.input(mnemonic[(index + 1) % len(mnemonic)])
            return False
        else:
            debug.input(mnemonic[index])

    return True


def click_info_button_bolt(debug: "DebugLink") -> Generator[Any, Any, ButtonRequest]:
    """Click Shamir backup info button and return back."""
    debug.press_info()
    debug.press_yes()
    return (yield)


def click_info_button_delizia(debug: "DebugLink"):
    """Click Shamir backup info button and return back."""
    debug.click(debug.screen_buttons.menu())
    layout = debug.read_layout()
    assert "VerticalMenu" in layout.all_components()
    debug.click(debug.screen_buttons.vertical_menu_items()[0])
    debug.click(debug.screen_buttons.menu())
    debug.click(debug.screen_buttons.menu())


def check_pin_backoff_time(attempts: int, start: float) -> None:
    """Helper to assert the exponentially growing delay after incorrect PIN attempts"""
    expected = (2**attempts) - 1
    got = round(time.time() - start, 2)
    assert got >= expected


def get_test_address(client: "Client") -> str:
    """Fetch a testnet address on a fixed path. Useful to make a pin/passphrase
    protected call, or to identify the root secret (seed+passphrase)"""
    return btc.get_address(client, "Testnet", TEST_ADDRESS_N)


def compact_size(n: int) -> bytes:
    if n < 253:
        return n.to_bytes(1, "little")
    elif n < 0x1_0000:
        return bytes([253]) + n.to_bytes(2, "little")
    elif n < 0x1_0000_0000:
        return bytes([254]) + n.to_bytes(4, "little")
    else:
        return bytes([255]) + n.to_bytes(8, "little")


def get_text_possible_pagination(debug: "DebugLink", br: messages.ButtonRequest) -> str:
    text = debug.read_layout().text_content()
    if br.pages is not None:
        for _ in range(br.pages - 1):
            debug.swipe_up()
            text += " "
            text += debug.read_layout().text_content()
    return text


def swipe_if_necessary(
    debug: "DebugLink", br_code: messages.ButtonRequestType | None = None
) -> BRGeneratorType:
    br = yield
    if br_code is not None:
        assert br.code == br_code
    swipe_till_the_end(debug, br)


def swipe_till_the_end(debug: "DebugLink", br: messages.ButtonRequest) -> None:
    if br.pages is not None:
        for _ in range(br.pages - 1):
            debug.swipe_up()


def is_core(client: "Client") -> bool:
    return client.model is not models.T1B1
