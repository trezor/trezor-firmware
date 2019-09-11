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

from trezorlib.messages import ButtonRequestType as B

# fmt: off
#                1      2     3    4      5      6      7     8      9    10    11    12
MNEMONIC12 = "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
MNEMONIC18 = "owner little vague addict embark decide pink prosper true fork panda embody mixture exchange choose canoe electric jewel"
MNEMONIC24 = "dignity pass list indicate nasty swamp pool script soccer toe leaf photo multiply desk host tomato cradle drill spread actor shine dismiss champion exotic"
MNEMONIC_ALLALLALL = " ".join(["all"] * 12)
# fmt: on

MNEMONIC_SHAMIR_20_3of6 = [
    "extra extend academic bishop cricket bundle tofu goat apart victim enlarge program behavior permit course armed jerky faint language modern",
    "extra extend academic acne away best indicate impact square oasis prospect painting voting guest either argue username racism enemy eclipse",
    "extra extend academic arcade born dive legal hush gross briefing talent drug much home firefly toxic analysis idea umbrella slice",
]
MNEMONIC_SHAMIR_20_2of3_2of3_GROUPS = [
    "gesture negative ceramic leaf device fantasy style ceramic safari keyboard thumb total smug cage plunge aunt favorite lizard intend peanut",
    "gesture negative acrobat leaf craft sidewalk adorn spider submit bumpy alcohol cards salon making prune decorate smoking image corner method",
    "gesture negative acrobat lily bishop voting humidity rhyme parcel crunch elephant victim dish mailman triumph agree episode wealthy mayor beam",
    "gesture negative beard leaf deadline stadium vegan employer armed marathon alien lunar broken edge justice military endorse diet sweater either",
    "gesture negative beard lily desert belong speak realize explain bolt diet believe response counter medal luck wits glance remove ending",
]


class TrezorTest:
    mnemonic12 = MNEMONIC12
    mnemonic18 = MNEMONIC18
    mnemonic24 = MNEMONIC24
    mnemonic_all = MNEMONIC_ALLALLALL

    pin4 = "1234"
    pin6 = "789456"
    pin8 = "45678978"


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
        if groups and index >= 1:
            # confirm remaining shares
            debug.swipe_down()
            code = yield
            assert code == B.Other
            debug.press_yes()

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
            debug.swipe_down()
        else:
            # last page is confirmation
            debug.press_yes()
            break

    # check share
    for _ in range(3):
        index = debug.read_reset_word_pos()
        debug.input(mnemonic[index])

    return " ".join(mnemonic)
