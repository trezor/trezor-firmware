#!/usr/bin/env python3

# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

import hashlib

import mnemonic

__doc__ = """
    Use this script to cross-check that Trezor generated valid
    mnemonic sentence for given internal (Trezor-generated)
    and external (computer-generated) entropy.

    Keep in mind that you're entering secret information to this script.
    Leaking of these information may lead to stealing your bitcoins
    from your wallet! We strongly recommend to run this script only on
    highly secured computer (ideally live linux distribution
    without an internet connection).
"""


def generate_entropy(
    strength: int, internal_entropy: bytes, external_entropy: bytes
) -> bytes:
    """
    strength - length of produced seed. One of 128, 192, 256
    random - binary stream of random data from external HRNG
    """
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


def main() -> None:
    print(__doc__)

    comp = bytes.fromhex(
        input("Please enter computer-generated entropy (in hex): ").strip()
    )
    trzr = bytes.fromhex(
        input("Please enter Trezor-generated entropy (in hex): ").strip()
    )
    word_count = int(input("How many words your mnemonic has? "))

    strength = word_count * 32 // 3

    entropy = generate_entropy(strength, trzr, comp)

    words = mnemonic.Mnemonic("english").to_mnemonic(entropy)
    if not mnemonic.Mnemonic("english").check(words):
        print("Mnemonic is invalid")
        return

    if len(words.split(" ")) != word_count:
        print("Mnemonic length mismatch!")
        return

    print("Generated mnemonic is:", words)


if __name__ == "__main__":
    main()
