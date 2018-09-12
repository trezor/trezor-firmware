#!/usr/bin/env python3
import hashlib

import mnemonic

__doc__ = '''
    Use this script to cross-check that TREZOR generated valid
    mnemonic sentence for given internal (TREZOR-generated)
    and external (computer-generated) entropy.

    Keep in mind that you're entering secret information to this script.
    Leaking of these information may lead to stealing your bitcoins
    from your wallet! We strongly recommend to run this script only on
    highly secured computer (ideally live linux distribution
    without an internet connection).
'''


def generate_entropy(strength, internal_entropy, external_entropy):
    '''
    strength - length of produced seed. One of 128, 192, 256
    random - binary stream of random data from external HRNG
    '''
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
    entropy_stripped = entropy[:strength // 8]

    if len(entropy_stripped) * 8 != strength:
        raise ValueError("Entropy length mismatch")

    return entropy_stripped


def main():
    print(__doc__)

    comp = bytes.fromhex(input("Please enter computer-generated entropy (in hex): ").strip())
    trzr = bytes.fromhex(input("Please enter TREZOR-generated entropy (in hex): ").strip())
    word_count = int(input("How many words your mnemonic has? "))

    strength = word_count * 32 // 3

    entropy = generate_entropy(strength, trzr, comp)

    words = mnemonic.Mnemonic('english').to_mnemonic(entropy)
    if not mnemonic.Mnemonic('english').check(words):
        print("Mnemonic is invalid")
        return

    if len(words.split(' ')) != word_count:
        print("Mnemonic length mismatch!")
        return

    print("Generated mnemonic is:", words)


if __name__ == '__main__':
    main()
