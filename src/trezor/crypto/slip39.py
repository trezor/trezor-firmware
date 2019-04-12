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

from trezor.crypto import pbkdf2
from trezor.crypto import hmac
from trezor.crypto import hashlib
import math
from trezor.crypto.slip39_wordlist import wordlist
from trezor.crypto import random
from trezorcrypto import shamir

class ConfigurationError(Exception):
    pass


class InterpolationError(Exception):
    pass


class MnemonicError(Exception):
    pass


class ShamirMnemonic(object):
    RADIX_BITS = 10
    """The length of the radix in bits."""

    RADIX = 2 ** RADIX_BITS
    """The number of words in the wordlist."""

    ID_LENGTH_BITS = 15
    """The length of the random identifier in bits."""

    ITERATION_EXP_LENGTH_BITS = 5
    """The length of the iteration exponent in bits."""

    ID_EXP_LENGTH_WORDS = (ID_LENGTH_BITS + ITERATION_EXP_LENGTH_BITS) // RADIX_BITS
    """The length of the random identifier and iteration exponent in words."""

    MAX_SHARE_COUNT = 2 ** (RADIX_BITS // 2)
    """The maximum number of shares that can be created."""

    CHECKSUM_LENGTH_WORDS = 3
    """The length of the RS1024 checksum in words."""

    DIGEST_LENGTH_BYTES = 4
    """The length of the digest of the shared secret in bytes."""

    CUSTOMIZATION_STRING = b"shamir"
    """The customization string used in the RS1024 checksum and in the PBKDF2 salt."""

    METADATA_LENGTH_WORDS = ID_EXP_LENGTH_WORDS + 2 + CHECKSUM_LENGTH_WORDS
    """The length of the mnemonic in words without the share value."""

    MIN_STRENGTH_BITS = 128
    """The minimum allowed entropy of the master secret."""

    MIN_MNEMONIC_LENGTH_WORDS = METADATA_LENGTH_WORDS + math.ceil(
        MIN_STRENGTH_BITS / 10
    )
    """The minimum allowed length of the mnemonic in words."""

    MIN_ITERATION_COUNT = 10000
    """The minimum number of iterations to use in PBKDF2."""

    ROUND_COUNT = 4
    """The number of rounds to use in the Feistel cipher."""

    SECRET_INDEX = 255
    """The index of the share containing the shared secret."""

    DIGEST_INDEX = 254
    """The index of the share containing the digest of the shared secret."""

    def __init__(self):
        # Load the word list.

        if len(wordlist) != self.RADIX:
            raise ConfigurationError(
                "The wordlist should contain {} words, but it contains {} words.".format(
                    self.RADIX, len(wordlist)
                )
            )

        self.word_index_map = {word: i for i, word in enumerate(wordlist)}

    def _interpolate(self, shares, x):
        """
        Returns f(x) given the Shamir shares (x_1, f(x_1)), ... , (x_k, f(x_k)).
        :param shares: The Shamir shares.
        :type shares: A list of pairs (x_i, y_i), where x_i is an integer and y_i is an array of
            bytes representing the evaluations of the polynomials in x_i.
        :param int x: The x coordinate of the result.
        :return: Evaluations of the polynomials in x.
        :rtype: Array of bytes.
        """

        x_coordinates = set(share[0] for share in shares)

        if len(x_coordinates) != len(shares):
            raise InterpolationError(
                "Invalid set of shares. Share indices must be unique."
            )

        share_value_lengths = set(len(share[1]) for share in shares)
        if len(share_value_lengths) != 1:
            raise InterpolationError(
                "Invalid set of shares. All share values must have the same length."
            )

        if x in x_coordinates:
            for share in shares:
                if share[0] == x:
                    return share[1]

        return shamir.interpolate(shares, x)

    @classmethod
    def _rs1024_polymod(cls, values):
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

    @classmethod
    def rs1024_create_checksum(cls, data):
        values = (
            tuple(cls.CUSTOMIZATION_STRING) + data + cls.CHECKSUM_LENGTH_WORDS * (0,)
        )
        polymod = cls._rs1024_polymod(values) ^ 1
        return tuple(
            (polymod >> 10 * i) & 1023
            for i in reversed(range(cls.CHECKSUM_LENGTH_WORDS))
        )

    @classmethod
    def rs1024_verify_checksum(cls, data):
        return cls._rs1024_polymod(tuple(cls.CUSTOMIZATION_STRING) + data) == 1

    @staticmethod
    def xor(a, b):
        return bytes(x ^ y for x, y in zip(a, b))

    @classmethod
    def _int_from_indices(cls, indices):
        """Converts a list of base 1024 indices in big endian order to an integer value."""
        value = 0
        for index in indices:
            value = (value << cls.RADIX_BITS) + index
        return value

    @classmethod
    def _int_to_indices(cls, value, length):
        """Converts an integer value to base 1024 indices in big endian order."""
        return (
            (value >> (i * cls.RADIX_BITS)) % cls.RADIX for i in reversed(range(length))
        )

    def mnemonic_from_indices(self, indices):
        return " ".join(wordlist[i] for i in indices)

    def mnemonic_to_indices(self, mnemonic):
        try:
            return (self.word_index_map[word.lower()] for word in mnemonic.split())
        except KeyError as key_error:
            raise MnemonicError("Invalid mnemonic word {}.".format(key_error)) from None

    @classmethod
    def _round_function(cls, i, passphrase, e, salt, r):
        """The round function used internally by the Feistel cipher."""
        return pbkdf2(pbkdf2.HMAC_SHA256, bytes([i]) + passphrase, salt + r, (cls.MIN_ITERATION_COUNT << e) // cls.ROUND_COUNT).key()[:len(r)]

    @classmethod
    def _get_salt(cls, identifier):
        return cls.CUSTOMIZATION_STRING + identifier.to_bytes(
            math.ceil(cls.ID_LENGTH_BITS / 8), "big"
        )

    @classmethod
    def _encrypt(cls, master_secret, passphrase, iteration_exponent, identifier):
        l = master_secret[: len(master_secret) // 2]
        r = master_secret[len(master_secret) // 2 :]
        salt = cls._get_salt(identifier)
        for i in range(cls.ROUND_COUNT):
            (l, r) = (
                r,
                cls.xor(
                    l, cls._round_function(i, passphrase, iteration_exponent, salt, r)
                ),
            )
        return r + l

    @classmethod
    def _decrypt(
        cls, encrypted_master_secret, passphrase, iteration_exponent, identifier
    ):
        l = encrypted_master_secret[: len(encrypted_master_secret) // 2]
        r = encrypted_master_secret[len(encrypted_master_secret) // 2 :]
        salt = cls._get_salt(identifier)
        for i in reversed(range(cls.ROUND_COUNT)):
            (l, r) = (
                r,
                cls.xor(
                    l, cls._round_function(i, passphrase, iteration_exponent, salt, r)
                ),
            )
        return r + l

    @classmethod
    def _create_digest(cls, random_data, shared_secret):
        return hmac.new(random_data, shared_secret, hashlib.sha256).digest()[
            : cls.DIGEST_LENGTH_BYTES
        ]

    def _split_secret(self, threshold, share_count, shared_secret):
        assert 0 < threshold <= share_count <= self.MAX_SHARE_COUNT

        # If the threshold is 1, then the digest of the shared secret is not used.
        if threshold == 1:
            return [(i, shared_secret) for i in range(share_count)]

        random_share_count = threshold - 2

        if share_count > self.MAX_SHARE_COUNT:
            raise ValueError(
                "The requested number of shares ({}) must not exceed {}.".format(
                    share_count, self.MAX_SHARE_COUNT
                )
            )

        shares = [
            (i, random.bytes(len(shared_secret)))
            for i in range(random_share_count)
        ]

        random_part = random.bytes(len(shared_secret) - self.DIGEST_LENGTH_BYTES)
        digest = self._create_digest(random_part, shared_secret)

        base_shares = shares + [
            (self.DIGEST_INDEX, digest + random_part),
            (self.SECRET_INDEX, shared_secret),
        ]

        for i in range(random_share_count, share_count):
            shares.append((i, self._interpolate(base_shares, i)))

        return shares

    def _recover_secret(self, threshold, shares):
        shared_secret = self._interpolate(shares, self.SECRET_INDEX)

        # If the threshold is 1, then the digest of the shared secret is not used.
        if threshold != 1:
            digest_share = self._interpolate(shares, self.DIGEST_INDEX)
            digest = digest_share[: self.DIGEST_LENGTH_BYTES]
            random_part = digest_share[self.DIGEST_LENGTH_BYTES :]

            if digest != self._create_digest(random_part, shared_secret):
                raise MnemonicError("Invalid digest of the shared secret.")

        return shared_secret

    @classmethod
    def _group_prefix(
        cls, identifier, iteration_exponent, group_index, group_threshold
    ):
        id_exp_int = (identifier << cls.ITERATION_EXP_LENGTH_BITS) + iteration_exponent
        return tuple(cls._int_to_indices(id_exp_int, cls.ID_EXP_LENGTH_WORDS)) + (
            group_index * cls.MAX_SHARE_COUNT + (group_threshold - 1),
        )

    def encode_mnemonic(
        self,
        identifier,
        iteration_exponent,
        group_index,
        group_threshold,
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
        :param int member_index: The x coordinate of the member share in the given group.
        :param int member_threshold: The number of member shares needed to reconstruct the group share.
        :param value: The share value representing the y coordinates of the share.
        :type value: Array of bytes.
        :return: The share mnemonic.
        :rtype: Array of bytes.
        """

        # Convert the share value from bytes to wordlist indices.
        value_word_count = math.ceil(len(value) * 8 / self.RADIX_BITS)
        value_int = int.from_bytes(value, "big")

        share_data = (
            self._group_prefix(
                identifier, iteration_exponent, group_index, group_threshold
            )
            + (member_index * self.MAX_SHARE_COUNT + (member_threshold - 1),)
            + tuple(self._int_to_indices(value_int, value_word_count))
        )
        checksum = self.rs1024_create_checksum(share_data)

        return self.mnemonic_from_indices(share_data + checksum)

    def decode_mnemonic(self, mnemonic):
        """Converts a share mnemonic to share data."""

        mnemonic_data = tuple(self.mnemonic_to_indices(mnemonic))

        if len(mnemonic_data) < self.MIN_MNEMONIC_LENGTH_WORDS:
            raise MnemonicError(
                "Invalid mnemonic length. The length of each mnemonic must be at least {} words.".format(
                    self.MIN_MNEMONIC_LENGTH_WORDS
                )
            )

        padding_len = (10 * (len(mnemonic_data) - self.METADATA_LENGTH_WORDS)) % 16
        if padding_len > 8:
            raise MnemonicError("Invalid mnemonic length.")

        if not self.rs1024_verify_checksum(mnemonic_data):
            raise MnemonicError(
                'Invalid mnemonic checksum for "{} ...".'.format(
                    " ".join(mnemonic.split()[: self.ID_EXP_LENGTH_WORDS + 2])
                )
            )

        id_exp_int = self._int_from_indices(mnemonic_data[: self.ID_EXP_LENGTH_WORDS])
        identifier = id_exp_int >> self.ITERATION_EXP_LENGTH_BITS
        iteration_exponent = id_exp_int & ((1 << self.ITERATION_EXP_LENGTH_BITS) - 1)
        group_index = mnemonic_data[self.ID_EXP_LENGTH_WORDS] // self.MAX_SHARE_COUNT
        group_threshold = (
            mnemonic_data[self.ID_EXP_LENGTH_WORDS] % self.MAX_SHARE_COUNT
        ) + 1
        member_index = (
            mnemonic_data[self.ID_EXP_LENGTH_WORDS + 1] // self.MAX_SHARE_COUNT
        )
        member_threshold = (
            mnemonic_data[self.ID_EXP_LENGTH_WORDS + 1] % self.MAX_SHARE_COUNT
        ) + 1
        value_data = mnemonic_data[
            self.ID_EXP_LENGTH_WORDS + 2 : -self.CHECKSUM_LENGTH_WORDS
        ]

        value_byte_count = (10 * len(value_data) - padding_len) // 8
        value_int = self._int_from_indices(value_data)
        if value_data[0] >= 1 << (10 - padding_len):
            raise MnemonicError("Invalid mnemonic padding.")
        value = value_int.to_bytes(value_byte_count, "big")

        return (
            identifier,
            iteration_exponent,
            group_index,
            group_threshold,
            member_index,
            member_threshold,
            value,
        )

    def _decode_mnemonics(self, mnemonics):
        identifiers = set()
        iteration_exponents = set()
        group_thresholds = set()
        groups = {}  # { group_index : [member_threshold, set_of_member_shares] }
        for mnemonic in mnemonics:
            identifier, iteration_exponent, group_index, group_threshold, member_index, member_threshold, share_value = self.decode_mnemonic(
                mnemonic
            )
            identifiers.add(identifier)
            iteration_exponents.add(iteration_exponent)
            group_thresholds.add(group_threshold)
            group = groups.setdefault(group_index, [member_threshold, set()])
            if group[0] != member_threshold:
                raise MnemonicError(
                    "Invalid set of mnemonics. All mnemonics in a group must have the same member threshold."
                )
            group[1].add((member_index, share_value))

        if len(identifiers) != 1 or len(iteration_exponents) != 1:
            raise MnemonicError(
                "Invalid set of mnemonics. All mnemonics must begin with the same {} words.".format(
                    self.ID_EXP_LENGTH_WORDS
                )
            )

        if len(group_thresholds) != 1:
            raise MnemonicError(
                "Invalid set of mnemonics. All mnemonics must have the same group threshold."
            )

        return (
            identifiers.pop(),
            iteration_exponents.pop(),
            group_thresholds.pop(),
            groups,
        )

    def _generate_random_identifier(self):
        """Returns a randomly generated integer in the range 0, ... , 2**ID_LENGTH_BITS - 1."""

        identifier = int.from_bytes(
            random.bytes(math.ceil(self.ID_LENGTH_BITS / 8)), "big"
        )
        return identifier & ((1 << self.ID_LENGTH_BITS) - 1)

    def generate_mnemonics(
        self,
        group_threshold,
        groups,
        master_secret,
        passphrase=b"",
        iteration_exponent=0,
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

        identifier = self._generate_random_identifier()

        if len(master_secret) * 8 < self.MIN_STRENGTH_BITS:
            raise ValueError(
                "The length of the master secret ({} bytes) must be at least {} bytes.".format(
                    len(master_secret), math.ceil(self.MIN_STRENGTH_BITS / 8)
                )
            )

        if len(master_secret) % 2 != 0:
            raise ValueError(
                "The length of the master secret in bytes must be an even number."
            )

        if group_threshold > len(groups):
            raise ValueError(
                "The requested group threshold ({}) must not exceed the number of groups ({}).".format(
                    group_threshold, len(groups)
                )
            )

        encrypted_master_secret = self._encrypt(
            master_secret, passphrase, iteration_exponent, identifier
        )

        group_shares = self._split_secret(
            group_threshold, len(groups), encrypted_master_secret
        )

        return [
            [
                self.encode_mnemonic(
                    identifier,
                    iteration_exponent,
                    group_index,
                    group_threshold,
                    member_index,
                    member_threshold,
                    value,
                )
                for member_index, value in self._split_secret(
                    member_threshold, member_count, group_secret
                )
            ]
            for (member_threshold, member_count), (group_index, group_secret) in zip(
                groups, group_shares
            )
        ]

    def generate_mnemonics_random(
        self,
        group_threshold,
        groups,
        strength_bits=128,
        passphrase=b"",
        iteration_exponent=0,
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

        if strength_bits < self.MIN_STRENGTH_BITS:
            raise ValueError(
                "The requested strength of the master secret ({} bits) must be at least {} bits.".format(
                    strength_bits, self.MIN_STRENGTH_BITS
                )
            )

        if strength_bits % 16 != 0:
            raise ValueError(
                "The requested strength of the master secret ({} bits) must be a multiple of 16 bits.".format(
                    strength_bits
                )
            )

        return self.generate_mnemonics(
            group_threshold,
            groups,
            random.bytes(strength_bits // 8),
            passphrase,
            iteration_exponent,
        )

    def combine_mnemonics(self, mnemonics, passphrase=b""):
        """
        Combines mnemonic shares to obtain the master secret which was previously split using
        Shamir's secret sharing scheme.
        :param mnemonics: List of mnemonics.
        :type mnemonics: List of byte arrays.
        :param passphrase: The passphrase used to encrypt the master secret.
        :type passphrase: Array of bytes.
        :return: The master secret.
        :rtype: Array of bytes.
        """

        if not mnemonics:
            raise MnemonicError("The list of mnemonics is empty.")

        identifier, iteration_exponent, group_threshold, groups = self._decode_mnemonics(
            mnemonics
        )

        if len(groups) < group_threshold:
            raise MnemonicError(
                "Insufficient number of mnemonic groups ({}). The required number of groups is {}.".format(
                    len(groups), group_threshold
                )
            )

        # Remove the groups, where the number of shares is below the member threshold.
        bad_groups = {
            group_index: group
            for group_index, group in groups.items()
            if len(group[1]) < group[0]
        }
        for group_index in bad_groups:
            groups.pop(group_index)

        if len(groups) < group_threshold:
            group_index, group = next(iter(bad_groups.items()))
            prefix = self._group_prefix(
                identifier, iteration_exponent, group_index, group_threshold
            )
            raise MnemonicError(
                'Insufficient number of mnemonics. At least {} mnemonics starting with "{} ..." are required.'.format(
                    group[0], self.mnemonic_from_indices(prefix)
                )
            )

        group_shares = [
            (group_index, self._recover_secret(group[0], list(group[1])))
            for group_index, group in groups.items()
        ]

        return self._decrypt(
            self._recover_secret(group_threshold, group_shares),
            passphrase,
            iteration_exponent,
            identifier,
        )
