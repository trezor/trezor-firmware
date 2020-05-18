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

"""
This implements the high-level functions for SLIP-39, also called "Shamir Backup".
It uses crypto/shamir.c for the cryptographic operations and crypto.slip39.c for
performance-heavy operations (mostly regarding the wordlist).

This consideres the Encrypted Master Secret, as defined in SLIP-39, as what is
stored in the storage, then "decrypted" using a passphrase into a Master Secret,
which is then fed into BIP-32 for example.

See https://github.com/satoshilabs/slips/blob/master/slip-0039.md.
"""

from micropython import const
from trezorcrypto import shamir, slip39

from trezor.crypto import hashlib, hmac, pbkdf2, random
from trezor.errors import MnemonicError

if False:
    from typing import Dict, Iterable, List, Optional, Set, Tuple

    Indices = Tuple[int, ...]
    MnemonicGroups = Dict[int, Tuple[int, Set[Tuple[int, bytes]]]]

"""
## Simple helpers
"""

_RADIX_BITS = const(10)
"""The length of the radix in bits."""


def _bits_to_bytes(n: int) -> int:
    return (n + 7) // 8


def _bits_to_words(n: int) -> int:
    return (n + _RADIX_BITS - 1) // _RADIX_BITS


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


"""
## Constants
"""

_ID_LENGTH_BITS = const(15)
"""The length of the random identifier in bits."""

_ITERATION_EXP_LENGTH_BITS = const(5)
"""The length of the iteration exponent in bits."""

_ID_EXP_LENGTH_WORDS = _bits_to_words(_ID_LENGTH_BITS + _ITERATION_EXP_LENGTH_BITS)
"""The length of the random identifier and iteration exponent in words."""

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

_MIN_MNEMONIC_LENGTH_WORDS = _METADATA_LENGTH_WORDS + _bits_to_words(_MIN_STRENGTH_BITS)
"""The minimum allowed length of the mnemonic in words."""

_BASE_ITERATION_COUNT = const(10000)
"""The minimum number of iterations to use in PBKDF2."""

_ROUND_COUNT = const(4)
"""The number of rounds to use in the Feistel cipher."""

_SECRET_INDEX = const(255)
"""The index of the share containing the shared secret."""

_DIGEST_INDEX = const(254)
"""The index of the share containing the digest of the shared secret."""


"""
# Keyboard functions
"""

KEYBOARD_FULL_MASK = const(0x1FF)
"""All buttons are allowed. 9-bit bitmap all set to 1."""


def compute_mask(prefix: str) -> int:
    if not prefix:
        return KEYBOARD_FULL_MASK
    return slip39.compute_mask(int(prefix))


def button_sequence_to_word(prefix: str) -> str:
    if not prefix:
        return ""
    return slip39.button_sequence_to_word(int(prefix))


"""
# External API
"""

MAX_SHARE_COUNT = const(16)
"""The maximum number of shares that can be created."""
MAX_GROUP_COUNT = const(16)
"""The maximum number of groups that can be created."""

DEFAULT_ITERATION_EXPONENT = const(1)


class Share:
    """
    Represents a single mnemonic and offers its parsed metadata.
    """

    def __init__(
        self,
        identifier: int,
        iteration_exponent: int,
        group_index: int,
        group_threshold: int,
        group_count: int,
        index: int,
        threshold: int,
        share_value: bytes,
    ):
        self.identifier = identifier
        self.iteration_exponent = iteration_exponent
        self.group_index = group_index
        self.group_threshold = group_threshold
        self.group_count = group_count
        self.index = index
        self.threshold = threshold
        self.share_value = share_value


def decrypt(
    encrypted_master_secret: bytes,
    passphrase: bytes,
    iteration_exponent: int,
    identifier: int,
) -> bytes:
    """
    Converts the Encrypted Master Secret to a Master Secret by applying the passphrase.
    This is analogous to BIP-39 passphrase derivation. We do not use the term "derive"
    here, because passphrase function is symmetric in SLIP-39. We are using the terms
    "encrypt" and "decrypt" instead.
    """
    l = encrypted_master_secret[: len(encrypted_master_secret) // 2]
    r = encrypted_master_secret[len(encrypted_master_secret) // 2 :]
    salt = _get_salt(identifier)
    for i in reversed(range(_ROUND_COUNT)):
        (l, r) = (
            r,
            _xor(l, _round_function(i, passphrase, iteration_exponent, salt, r)),
        )
    return r + l


def generate_random_identifier() -> int:
    """Returns a randomly generated integer in the range 0, ... , 2**_ID_LENGTH_BITS - 1."""

    identifier = int.from_bytes(random.bytes(_bits_to_bytes(_ID_LENGTH_BITS)), "big")
    return identifier & ((1 << _ID_LENGTH_BITS) - 1)


def split_ems(
    group_threshold: int,  # The number of groups required to reconstruct the master secret.
    groups: List[Tuple[int, int]],  # A list of (member_threshold, member_count).
    identifier: int,
    iteration_exponent: int,
    encrypted_master_secret: bytes,  # The encrypted master secret to split.
) -> List[List[str]]:
    """
    Splits an encrypted master secret into mnemonic shares using Shamir's secret sharing scheme.

    The `groups` argument takes pairs for each group, where member_count is the number of shares
    to generate for the group and member_threshold is the number of members required to reconstruct
    the group secret.

    Returns a list of mnemonics, grouped by the groups.
    """

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

    # Split the Encrypted Master Secret on the group level.
    group_shares = _split_secret(group_threshold, len(groups), encrypted_master_secret)

    mnemonics = []  # type: List[List[str]]
    for (member_threshold, member_count), (group_index, group_secret) in zip(
        groups, group_shares
    ):
        group_mnemonics = []
        # Split the group's secret between shares.
        shares = _split_secret(member_threshold, member_count, group_secret)
        for member_index, value in shares:
            group_mnemonics.append(
                _encode_mnemonic(
                    identifier,
                    iteration_exponent,
                    group_index,
                    group_threshold,
                    len(groups),
                    member_index,
                    member_threshold,
                    value,
                )
            )
        mnemonics.append(group_mnemonics)
    return mnemonics


def recover_ems(mnemonics: List[str]) -> Tuple[int, int, bytes]:
    """
    Combines mnemonic shares to obtain the encrypted master secret which was previously
    split using Shamir's secret sharing scheme.
    Returns identifier, iteration exponent and the encrypted master secret.
    """

    if not mnemonics:
        raise MnemonicError("The list of mnemonics is empty.")

    (
        identifier,
        iteration_exponent,
        group_threshold,
        group_count,
        groups,
    ) = _decode_mnemonics(mnemonics)

    if len(groups) != group_threshold:
        raise MnemonicError(
            "Wrong number of mnemonic groups. Expected {} groups, but {} were provided.".format(
                group_threshold, len(groups)
            )
        )

    for group_index, group in groups.items():
        if len(group[1]) != group[0]:  # group[0] is threshold
            raise MnemonicError(
                "Wrong number of mnemonics. Expected {} mnemonics, but {} were provided.".format(
                    group[0], len(group[1])
                )
            )

    group_shares = [
        (group_index, _recover_secret(group[0], list(group[1])))
        for group_index, group in groups.items()
    ]

    encrypted_master_secret = _recover_secret(group_threshold, group_shares)
    return identifier, iteration_exponent, encrypted_master_secret


def decode_mnemonic(mnemonic: str) -> Share:
    """Converts a share mnemonic to share data."""

    mnemonic_data = tuple(_mnemonic_to_indices(mnemonic))

    if len(mnemonic_data) < _MIN_MNEMONIC_LENGTH_WORDS:
        raise MnemonicError(
            "Invalid mnemonic length. The length of each mnemonic must be at least {} words.".format(
                _MIN_MNEMONIC_LENGTH_WORDS
            )
        )

    padding_len = (_RADIX_BITS * (len(mnemonic_data) - _METADATA_LENGTH_WORDS)) % 16
    if padding_len > 8:
        raise MnemonicError("Invalid mnemonic length.")

    if not _rs1024_verify_checksum(mnemonic_data):
        raise MnemonicError("Invalid mnemonic checksum.")

    id_exp_int = _int_from_indices(mnemonic_data[:_ID_EXP_LENGTH_WORDS])
    identifier = id_exp_int >> _ITERATION_EXP_LENGTH_BITS
    iteration_exponent = id_exp_int & ((1 << _ITERATION_EXP_LENGTH_BITS) - 1)
    tmp = _int_from_indices(
        mnemonic_data[_ID_EXP_LENGTH_WORDS : _ID_EXP_LENGTH_WORDS + 2]
    )
    (
        group_index,
        group_threshold,
        group_count,
        member_index,
        member_threshold,
    ) = _int_to_indices(tmp, 5, 4)
    value_data = mnemonic_data[_ID_EXP_LENGTH_WORDS + 2 : -_CHECKSUM_LENGTH_WORDS]

    if group_count < group_threshold:
        raise MnemonicError(
            "Invalid mnemonic. Group threshold cannot be greater than group count."
        )

    value_byte_count = _bits_to_bytes(_RADIX_BITS * len(value_data) - padding_len)
    value_int = _int_from_indices(value_data)
    if value_data[0] >= 1 << (_RADIX_BITS - padding_len):
        raise MnemonicError("Invalid mnemonic padding")
    value = value_int.to_bytes(value_byte_count, "big")

    return Share(
        identifier,
        iteration_exponent,
        group_index,
        group_threshold + 1,
        group_count + 1,
        member_index,
        member_threshold + 1,
        value,
    )


"""
## Convert mnemonics or integers to incices and back
"""


def _int_from_indices(indices: Indices) -> int:
    """Converts a list of base 1024 indices in big endian order to an integer value."""
    value = 0
    for index in indices:
        value = (value << _RADIX_BITS) + index
    return value


def _int_to_indices(value: int, length: int, bits: int) -> Iterable[int]:
    """Converts an integer value to indices in big endian order."""
    mask = (1 << bits) - 1
    return ((value >> (i * bits)) & mask for i in reversed(range(length)))


def _mnemonic_from_indices(indices: Indices) -> str:
    return " ".join(slip39.get_word(i) for i in indices)


def _mnemonic_to_indices(mnemonic: str) -> Iterable[int]:
    return (slip39.word_index(word.lower()) for word in mnemonic.split())


"""
## Checksum functions
"""


def _rs1024_create_checksum(data: Indices) -> Indices:
    """
    This implements the checksum - a Reed-Solomon code over GF(1024) that guarantees
    detection of any error affecting at most 3 words and has less than a 1 in 10^9
    chance of failing to detect more errors.
    """
    values = tuple(_CUSTOMIZATION_STRING) + data + _CHECKSUM_LENGTH_WORDS * (0,)
    polymod = _rs1024_polymod(values) ^ 1
    return tuple(
        (polymod >> 10 * i) & 1023 for i in reversed(range(_CHECKSUM_LENGTH_WORDS))
    )


def _rs1024_polymod(values: Indices) -> int:
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


def _rs1024_verify_checksum(data: Indices) -> bool:
    """
    Verifies a checksum of the given mnemonic, which was already parsed into Indices.
    """
    return _rs1024_polymod(tuple(_CUSTOMIZATION_STRING) + data) == 1


def _rs1024_error_index(data: Indices) -> Optional[int]:
    """
    Returns the index where an error possibly occurred.
    Currently unused.
    """
    GEN = (
        0x91F9F87,
        0x122F1F07,
        0x244E1E07,
        0x81C1C07,
        0x10281C0E,
        0x20401C1C,
        0x103838,
        0x207070,
        0x40E0E0,
        0x81C1C0,
    )
    chk = _rs1024_polymod(tuple(_CUSTOMIZATION_STRING) + data) ^ 1
    if chk == 0:
        return None

    for i in reversed(range(len(data))):
        b = chk & 0x3FF
        chk >>= 10
        if chk == 0:
            return i
        for j in range(10):
            chk ^= GEN[j] if ((b >> j) & 1) else 0
    return None


"""
## Internal functions
"""


def _round_function(i: int, passphrase: bytes, e: int, salt: bytes, r: bytes) -> bytes:
    """The round function used internally by the Feistel cipher."""
    return pbkdf2(
        pbkdf2.HMAC_SHA256,
        bytes([i]) + passphrase,
        salt + r,
        (_BASE_ITERATION_COUNT << e) // _ROUND_COUNT,
    ).key()[: len(r)]


def _get_salt(identifier: int) -> bytes:
    return _CUSTOMIZATION_STRING + identifier.to_bytes(
        _bits_to_bytes(_ID_LENGTH_BITS), "big"
    )


def _create_digest(random_data: bytes, shared_secret: bytes) -> bytes:
    return hmac.new(random_data, shared_secret, hashlib.sha256).digest()[
        :_DIGEST_LENGTH_BYTES
    ]


def _split_secret(
    threshold: int, share_count: int, shared_secret: bytes
) -> List[Tuple[int, bytes]]:
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

    if share_count > MAX_SHARE_COUNT:
        raise ValueError(
            "The requested number of shares ({}) must not exceed {}.".format(
                share_count, MAX_SHARE_COUNT
            )
        )

    # If the threshold is 1, then the digest of the shared secret is not used.
    if threshold == 1:
        return [(i, shared_secret) for i in range(share_count)]

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


def _recover_secret(threshold: int, shares: List[Tuple[int, bytes]]) -> bytes:
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
    identifier: int,
    iteration_exponent: int,
    group_index: int,
    group_threshold: int,
    group_count: int,
) -> Indices:
    id_exp_int = (identifier << _ITERATION_EXP_LENGTH_BITS) + iteration_exponent
    return tuple(_int_to_indices(id_exp_int, _ID_EXP_LENGTH_WORDS, _RADIX_BITS)) + (
        (group_index << 6) + ((group_threshold - 1) << 2) + ((group_count - 1) >> 2),
    )


def _encode_mnemonic(
    identifier: int,
    iteration_exponent: int,
    group_index: int,  # The x coordinate of the group share.
    group_threshold: int,  # The number of group shares needed to reconstruct the encrypted master secret.
    group_count: int,  # The total number of groups in existence.
    member_index: int,  # The x coordinate of the member share in the given group.
    member_threshold: int,  # The number of member shares needed to reconstruct the group share.
    value: bytes,  # The share value representing the y coordinates of the share.
) -> str:
    """
    Takes the metadata and the value to be encoded and converts it into a mnemonic words.
    Also appends a checksum.
    """

    # Convert the share value from bytes to wordlist indices.
    value_word_count = _bits_to_words(len(value) * 8)
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
    checksum = _rs1024_create_checksum(share_data)

    return _mnemonic_from_indices(share_data + checksum)


def _decode_mnemonics(
    mnemonics: List[str],
) -> Tuple[int, int, int, int, MnemonicGroups]:
    identifiers = set()
    iteration_exponents = set()
    group_thresholds = set()
    group_counts = set()

    # { group_index : [threshold, set_of_member_shares] }
    groups = {}  # type: MnemonicGroups
    for mnemonic in mnemonics:
        share = decode_mnemonic(mnemonic)
        identifiers.add(share.identifier)
        iteration_exponents.add(share.iteration_exponent)
        group_thresholds.add(share.group_threshold)
        group_counts.add(share.group_count)
        group = groups.setdefault(share.group_index, (share.threshold, set()))
        if group[0] != share.threshold:
            raise MnemonicError(
                "Invalid set of mnemonics. All mnemonics in a group must have the same member threshold."
            )
        group[1].add((share.index, share.share_value))

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
