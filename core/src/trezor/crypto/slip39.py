# Copyright (c) 2018 Andrew R. Kozlik
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from micropython import const

from trezor.crypto import hashlib, hmac, pbkdf2, random
from trezor.crypto.slip39_wordlist import wordlist
from trezorcrypto import shamir

_RADIX_BITS = const(10)
"""The length of the radix in bits."""


def bits_to_bytes(n):
    return (n + 7) // 8


def bits_to_words(n):
    return (n + _RADIX_BITS - 1) // _RADIX_BITS


_RADIX = 2 ** _RADIX_BITS
"""The number of words in the wordlist."""

_ID_LENGTH_BITS = const(15)
"""The length of the random identifier in bits."""

_ITERATION_EXP_LENGTH_BITS = const(5)
"""The length of the iteration exponent in bits."""

_ID_EXP_LENGTH_WORDS = bits_to_words(_ID_LENGTH_BITS + _ITERATION_EXP_LENGTH_BITS)
"""The length of the random identifier and iteration exponent in words."""

_MAX_SHARE_COUNT = const(16)
"""The maximum number of shares that can be created."""

_CHECKSUM_LENGTH_WORDS = const(3)
"""The length of the RS1024 checksum in words."""

_DIGEST_LENGTH_BYTES = const(4)
"""The length of the digest of the shared secret in bytes."""

_CUSTOMIZATION_STRING = b"shamir"
"""The customization string used in the RS1024 checksum and in the PBKDF2 salt."""

_METADATA_LENGTH_WORDS = _ID_EXP_LENGTH_WORDS + 2 + _CHECKSUM_LENGTH_WORDS
"""The length of the mnemonic in words without the share value."""

_MIN_STRENGTH_BITS = const(128)
"""The minimum allowed entropy of the master secret."""

_MIN_MNEMONIC_LENGTH_WORDS = _METADATA_LENGTH_WORDS + bits_to_words(_MIN_STRENGTH_BITS)
"""The minimum allowed length of the mnemonic in words."""

_BASE_ITERATION_COUNT = const(10000)
"""The minimum number of iterations to use in PBKDF2."""

_ROUND_COUNT = const(4)
"""The number of rounds to use in the Feistel cipher."""

_SECRET_INDEX = const(255)
"""The index of the share containing the shared secret."""

_DIGEST_INDEX = const(254)
"""The index of the share containing the digest of the shared secret."""


class MnemonicError(Exception):
    pass


def word_index(word):
    word = word + " " * (8 - len(word))
    lo = 0
    hi = _RADIX
    while hi - lo > 1:
        mid = (hi + lo) // 2
        if wordlist[mid * 8 : mid * 8 + 8] > word:
            hi = mid
        else:
            lo = mid
    if wordlist[lo * 8 : lo * 8 + 8] != word:
        raise MnemonicError('Invalid mnemonic word "{}".'.format(word))
    return lo


def _rs1024_polymod(values):
    GEN = (
        0xE0E040,
        0x1C1C080,
        0x3838100,
        0x7070200,
        0xE0E0009,
        0x1C0C2412,
        0x38086C24,
        0x3090FC48,
        0x21B1F890,
        0x3F3F120,
    )
    chk = 1
    for v in values:
        b = chk >> 20
        chk = (chk & 0xFFFFF) << 10 ^ v
        for i in range(10):
            chk ^= GEN[i] if ((b >> i) & 1) else 0
    return chk


def rs1024_create_checksum(data):
    values = tuple(_CUSTOMIZATION_STRING) + data + _CHECKSUM_LENGTH_WORDS * (0,)
    polymod = _rs1024_polymod(values) ^ 1
    return tuple(
        (polymod >> 10 * i) & 1023 for i in reversed(range(_CHECKSUM_LENGTH_WORDS))
    )


def rs1024_verify_checksum(data):
    return _rs1024_polymod(tuple(_CUSTOMIZATION_STRING) + data) == 1


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def _int_from_indices(indices):
    """Converts a list of base 1024 indices in big endian order to an integer value."""
    value = 0
    for index in indices:
        value = (value << _RADIX_BITS) + index
    return value


def _int_to_indices(value, length, bits):
    """Converts an integer value to indices in big endian order."""
    mask = (1 << bits) - 1
    return ((value >> (i * bits)) & mask for i in reversed(range(length)))


def mnemonic_from_indices(indices):
    return " ".join(wordlist[i * 8 : i * 8 + 8].strip() for i in indices)


def mnemonic_to_indices(mnemonic):
    return (word_index(word.lower()) for word in mnemonic.split())


def _round_function(i, passphrase, e, salt, r):
    """The round function used internally by the Feistel cipher."""
    return pbkdf2(
        pbkdf2.HMAC_SHA256,
        bytes([i]) + passphrase,
        salt + r,
        (_BASE_ITERATION_COUNT << e) // _ROUND_COUNT,
    ).key()[: len(r)]


def _get_salt(identifier):
    return _CUSTOMIZATION_STRING + identifier.to_bytes(
        bits_to_bytes(_ID_LENGTH_BITS), "big"
    )


def _encrypt(master_secret, passphrase, iteration_exponent, identifier):
    l = master_secret[: len(master_secret) // 2]
    r = master_secret[len(master_secret) // 2 :]
    salt = _get_salt(identifier)
    for i in range(_ROUND_COUNT):
        (l, r) = (
            r,
            xor(l, _round_function(i, passphrase, iteration_exponent, salt, r)),
        )
    return r + l


def decrypt(identifier, iteration_exponent, encrypted_master_secret, passphrase):
    l = encrypted_master_secret[: len(encrypted_master_secret) // 2]
    r = encrypted_master_secret[len(encrypted_master_secret) // 2 :]
    salt = _get_salt(identifier)
    for i in reversed(range(_ROUND_COUNT)):
        (l, r) = (
            r,
            xor(l, _round_function(i, passphrase, iteration_exponent, salt, r)),
        )
    return r + l


def _create_digest(random_data, shared_secret):
    return hmac.new(random_data, shared_secret, hashlib.sha256).digest()[
        :_DIGEST_LENGTH_BYTES
    ]


def _split_secret(threshold, share_count, shared_secret):
    if threshold < 1:
        raise ValueError(
            "The requested threshold ({}) must be a positive integer.".format(threshold)
        )

    if threshold > share_count:
        raise ValueError(
            "The requested threshold ({}) must not exceed the number of shares ({}).".format(
                threshold, share_count
            )
        )

    if share_count > _MAX_SHARE_COUNT:
        raise ValueError(
            "The requested number of shares ({}) must not exceed {}.".format(
                share_count, _MAX_SHARE_COUNT
            )
        )

    # If the threshold is 1, then the digest of the shared secret is not used.
    if threshold == 1:
        return [(0, shared_secret)]

    random_share_count = threshold - 2

    shares = [(i, random.bytes(len(shared_secret))) for i in range(random_share_count)]

    random_part = random.bytes(len(shared_secret) - _DIGEST_LENGTH_BYTES)
    digest = _create_digest(random_part, shared_secret)

    base_shares = shares + [
        (_DIGEST_INDEX, digest + random_part),
        (_SECRET_INDEX, shared_secret),
    ]

    for i in range(random_share_count, share_count):
        shares.append((i, shamir.interpolate(base_shares, i)))

    return shares


def _recover_secret(threshold, shares):
    # If the threshold is 1, then the digest of the shared secret is not used.
    if threshold == 1:
        return shares[0][1]

    shared_secret = shamir.interpolate(shares, _SECRET_INDEX)
    digest_share = shamir.interpolate(shares, _DIGEST_INDEX)
    digest = digest_share[:_DIGEST_LENGTH_BYTES]
    random_part = digest_share[_DIGEST_LENGTH_BYTES:]

    if digest != _create_digest(random_part, shared_secret):
        raise MnemonicError("Invalid digest of the shared secret.")

    return shared_secret


def _group_prefix(
    identifier, iteration_exponent, group_index, group_threshold, group_count
):
    id_exp_int = (identifier << _ITERATION_EXP_LENGTH_BITS) + iteration_exponent
    return tuple(_int_to_indices(id_exp_int, _ID_EXP_LENGTH_WORDS, _RADIX_BITS)) + (
        (group_index << 6) + ((group_threshold - 1) << 2) + ((group_count - 1) >> 2),
    )


def encode_mnemonic(
    identifier,
    iteration_exponent,
    group_index,
    group_threshold,
    group_count,
    member_index,
    member_threshold,
    value,
):
    """
    Converts share data to a share mnemonic.
    :param int identifier: The random identifier.
    :param int iteration_exponent: The iteration exponent.
    :param int group_index: The x coordinate of the group share.
    :param int group_threshold: The number of group shares needed to reconstruct the encrypted master secret.
    :param int group_count: The total number of groups in existence.
    :param int member_index: The x coordinate of the member share in the given group.
    :param int member_threshold: The number of member shares needed to reconstruct the group share.
    :param value: The share value representing the y coordinates of the share.
    :type value: Array of bytes.
    :return: The share mnemonic.
    :rtype: Array of bytes.
    """

    # Convert the share value from bytes to wordlist indices.
    value_word_count = bits_to_words(len(value) * 8)
    value_int = int.from_bytes(value, "big")

    share_data = (
        _group_prefix(
            identifier, iteration_exponent, group_index, group_threshold, group_count
        )
        + (
            (((group_count - 1) & 3) << 8)
            + (member_index << 4)
            + (member_threshold - 1),
        )
        + tuple(_int_to_indices(value_int, value_word_count, _RADIX_BITS))
    )
    checksum = rs1024_create_checksum(share_data)

    return mnemonic_from_indices(share_data + checksum)


def decode_mnemonic(mnemonic):
    """Converts a share mnemonic to share data."""

    mnemonic_data = tuple(mnemonic_to_indices(mnemonic))

    if len(mnemonic_data) < _MIN_MNEMONIC_LENGTH_WORDS:
        raise MnemonicError(
            "Invalid mnemonic length. The length of each mnemonic must be at least {} words.".format(
                _MIN_MNEMONIC_LENGTH_WORDS
            )
        )

    padding_len = (_RADIX_BITS * (len(mnemonic_data) - _METADATA_LENGTH_WORDS)) % 16
    if padding_len > 8:
        raise MnemonicError("Invalid mnemonic length.")

    if not rs1024_verify_checksum(mnemonic_data):
        raise MnemonicError(
            'Invalid mnemonic checksum for "{} ...".'.format(
                " ".join(mnemonic.split()[: _ID_EXP_LENGTH_WORDS + 2])
            )
        )

    id_exp_int = _int_from_indices(mnemonic_data[:_ID_EXP_LENGTH_WORDS])
    identifier = id_exp_int >> _ITERATION_EXP_LENGTH_BITS
    iteration_exponent = id_exp_int & ((1 << _ITERATION_EXP_LENGTH_BITS) - 1)
    tmp = _int_from_indices(
        mnemonic_data[_ID_EXP_LENGTH_WORDS : _ID_EXP_LENGTH_WORDS + 2]
    )
    group_index, group_threshold, group_count, member_index, member_threshold = _int_to_indices(
        tmp, 5, 4
    )
    value_data = mnemonic_data[_ID_EXP_LENGTH_WORDS + 2 : -_CHECKSUM_LENGTH_WORDS]

    if group_count < group_threshold:
        raise MnemonicError(
            'Invalid mnemonic "{} ...". Group threshold cannot be greater than group count.'.format(
                " ".join(mnemonic.split()[: _ID_EXP_LENGTH_WORDS + 2])
            )
        )

    value_byte_count = bits_to_bytes(_RADIX_BITS * len(value_data) - padding_len)
    value_int = _int_from_indices(value_data)
    if value_data[0] >= 1 << (_RADIX_BITS - padding_len):
        raise MnemonicError(
            'Invalid mnemonic padding for "{} ...".'.format(
                " ".join(mnemonic.split()[: _ID_EXP_LENGTH_WORDS + 2])
            )
        )
    value = value_int.to_bytes(value_byte_count, "big")

    return (
        identifier,
        iteration_exponent,
        group_index,
        group_threshold + 1,
        group_count + 1,
        member_index,
        member_threshold + 1,
        value,
    )


def _decode_mnemonics(mnemonics):
    identifiers = set()
    iteration_exponents = set()
    group_thresholds = set()
    group_counts = set()
    groups = {}  # { group_index : [member_threshold, set_of_member_shares] }
    for mnemonic in mnemonics:
        identifier, iteration_exponent, group_index, group_threshold, group_count, member_index, member_threshold, share_value = decode_mnemonic(
            mnemonic
        )
        identifiers.add(identifier)
        iteration_exponents.add(iteration_exponent)
        group_thresholds.add(group_threshold)
        group_counts.add(group_count)
        group = groups.setdefault(group_index, [member_threshold, set()])
        if group[0] != member_threshold:
            raise MnemonicError(
                "Invalid set of mnemonics. All mnemonics in a group must have the same member threshold."
            )
        group[1].add((member_index, share_value))

    if len(identifiers) != 1 or len(iteration_exponents) != 1:
        raise MnemonicError(
            "Invalid set of mnemonics. All mnemonics must begin with the same {} words.".format(
                _ID_EXP_LENGTH_WORDS
            )
        )

    if len(group_thresholds) != 1:
        raise MnemonicError(
            "Invalid set of mnemonics. All mnemonics must have the same group threshold."
        )

    if len(group_counts) != 1:
        raise MnemonicError(
            "Invalid set of mnemonics. All mnemonics must have the same group count."
        )

    for group_index, group in groups.items():
        if len(set(share[0] for share in group[1])) != len(group[1]):
            raise MnemonicError(
                "Invalid set of shares. Member indices in each group must be unique."
            )

    return (
        identifiers.pop(),
        iteration_exponents.pop(),
        group_thresholds.pop(),
        group_counts.pop(),
        groups,
    )


def _generate_random_identifier():
    """Returns a randomly generated integer in the range 0, ... , 2**_ID_LENGTH_BITS - 1."""

    identifier = int.from_bytes(random.bytes(bits_to_bytes(_ID_LENGTH_BITS)), "big")
    return identifier & ((1 << _ID_LENGTH_BITS) - 1)


def generate_mnemonics(
    group_threshold, groups, master_secret, passphrase=b"", iteration_exponent=0
):
    """
    Splits a master secret into mnemonic shares using Shamir's secret sharing scheme.
    :param int group_threshold: The number of groups required to reconstruct the master secret.
    :param groups: A list of (member_threshold, member_count) pairs for each group, where member_count
        is the number of shares to generate for the group and member_threshold is the number of members required to
        reconstruct the group secret.
    :type groups: List of pairs of integers.
    :param master_secret: The master secret to split.
    :type master_secret: Array of bytes.
    :param passphrase: The passphrase used to encrypt the master secret.
    :type passphrase: Array of bytes.
    :param int iteration_exponent: The iteration exponent.
    :return: List of mnemonics.
    :rtype: List of byte arrays.
    """

    identifier = _generate_random_identifier()

    if len(master_secret) * 8 < _MIN_STRENGTH_BITS:
        raise ValueError(
            "The length of the master secret ({} bytes) must be at least {} bytes.".format(
                len(master_secret), bits_to_bytes(_MIN_STRENGTH_BITS)
            )
        )

    if len(master_secret) % 2 != 0:
        raise ValueError(
            "The length of the master secret in bytes must be an even number."
        )

    if not all(32 <= c <= 126 for c in passphrase):
        raise ValueError(
            "The passphrase must contain only printable ASCII characters (code points 32-126)."
        )

    if group_threshold > len(groups):
        raise ValueError(
            "The requested group threshold ({}) must not exceed the number of groups ({}).".format(
                group_threshold, len(groups)
            )
        )

    if any(
        member_threshold == 1 and member_count > 1
        for member_threshold, member_count in groups
    ):
        raise ValueError(
            "Creating multiple member shares with member threshold 1 is not allowed. Use 1-of-1 member sharing instead."
        )

    encrypted_master_secret = _encrypt(
        master_secret, passphrase, iteration_exponent, identifier
    )

    group_shares = _split_secret(group_threshold, len(groups), encrypted_master_secret)

    return [
        [
            encode_mnemonic(
                identifier,
                iteration_exponent,
                group_index,
                group_threshold,
                len(groups),
                member_index,
                member_threshold,
                value,
            )
            for member_index, value in _split_secret(
                member_threshold, member_count, group_secret
            )
        ]
        for (member_threshold, member_count), (group_index, group_secret) in zip(
            groups, group_shares
        )
    ]


def generate_mnemonics_random(
    group_threshold, groups, strength_bits=128, passphrase=b"", iteration_exponent=0
):
    """
    Generates a random master secret and splits it into mnemonic shares using Shamir's secret
    sharing scheme.
    :param int group_threshold: The number of groups required to reconstruct the master secret.
    :param groups: A list of (member_threshold, member_count) pairs for each group, where member_count
        is the number of shares to generate for the group and member_threshold is the number of members required to
        reconstruct the group secret.
    :type groups: List of pairs of integers.
    :param int strength_bits: The entropy of the randomly generated master secret in bits.
    :param passphrase: The passphrase used to encrypt the master secret.
    :type passphrase: Array of bytes.
    :param int iteration_exponent: The iteration exponent.
    :return: List of mnemonics.
    :rtype: List of byte arrays.
    """

    if strength_bits < _MIN_STRENGTH_BITS:
        raise ValueError(
            "The requested strength of the master secret ({} bits) must be at least {} bits.".format(
                strength_bits, _MIN_STRENGTH_BITS
            )
        )

    if strength_bits % 16 != 0:
        raise ValueError(
            "The requested strength of the master secret ({} bits) must be a multiple of 16 bits.".format(
                strength_bits
            )
        )

    return generate_mnemonics(
        group_threshold,
        groups,
        random.bytes(strength_bits // 8),
        passphrase,
        iteration_exponent,
    )


def combine_mnemonics(mnemonics):
    """
    Combines mnemonic shares to obtain the master secret which was previously split using
    Shamir's secret sharing scheme.
    :param mnemonics: List of mnemonics.
    :type mnemonics: List of byte arrays.
    :return: Identifier, iteration exponent, the encrypted master secret.
    :rtype: Integer, integer, array of bytes.
    """

    if not mnemonics:
        raise MnemonicError("The list of mnemonics is empty.")

    identifier, iteration_exponent, group_threshold, group_count, groups = _decode_mnemonics(
        mnemonics
    )

    if len(groups) != group_threshold:
        raise MnemonicError(
            "Wrong number of mnemonic groups. Expected {} groups, but {} were provided.".format(
                group_threshold, len(groups)
            )
        )

    for group_index, group in groups.items():
        if len(group[1]) != group[0]:
            prefix = _group_prefix(
                identifier,
                iteration_exponent,
                group_index,
                group_threshold,
                group_count,
            )
            raise MnemonicError(
                'Wrong number of mnemonics. Expected {} mnemonics starting with "{} ...", but {} were provided.'.format(
                    group[0], mnemonic_from_indices(prefix), len(group[1])
                )
            )

    group_shares = [
        (group_index, _recover_secret(group[0], list(group[1])))
        for group_index, group in groups.items()
    ]

    return (
        identifier,
        iteration_exponent,
        _recover_secret(group_threshold, group_shares),
    )
