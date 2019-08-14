from trezor.crypto import bip39, slip39
from trezor.errors import GroupThresholdReachedError, MnemonicError

from apps.common import storage

if False:
    from typing import Optional


class RecoveryAborted(Exception):
    pass


_GROUP_STORAGE_OFFSET = 16


def process_bip39(words: str) -> bytes:
    """
    Receives single mnemonic and processes it. Returns what is then stored
    in the storage, which is the mnemonic itself for BIP-39.
    """
    if not bip39.check(words):
        raise MnemonicError()
    return words.encode()


def process_slip39(words: str) -> Optional[bytes, int, int]:
    """
    Receives single mnemonic and processes it. Returns what is then stored in storage or
    None if more shares are needed.
    """
    identifier, iteration_exponent, group_index, group_threshold, group_count, index, threshold, value = slip39.decode_mnemonic(
        words
    )  # TODO: use better data structure for this

    remaining = storage.recovery.fetch_slip39_remaining_shares()
    index_with_group_offset = index + group_index * _GROUP_STORAGE_OFFSET

    # if this is the first share, parse and store metadata
    if not remaining:
        storage.recovery.set_slip39_group_count(group_count)
        storage.recovery.set_slip39_group_threshold(group_threshold)
        storage.recovery.set_slip39_iteration_exponent(iteration_exponent)
        storage.recovery.set_slip39_identifier(identifier)
        storage.recovery.set_slip39_threshold(threshold)
        storage.recovery.set_slip39_remaining_shares(threshold - 1, group_index)
        storage.recovery_shares.set(index_with_group_offset, words)

        return None, group_index, index  # we need more shares

    if remaining[group_index] == 0:
        raise GroupThresholdReachedError()
    # These should be checked by UI before so it's a Runtime exception otherwise
    if identifier != storage.recovery.get_slip39_identifier():
        raise RuntimeError("Slip39: Share identifiers do not match")
    if storage.recovery_shares.get(index_with_group_offset):
        raise RuntimeError("Slip39: This mnemonic was already entered")

    remaining_for_share = (
        storage.recovery.get_slip39_remaining_shares(group_index) or threshold
    )
    storage.recovery.set_slip39_remaining_shares(remaining_for_share - 1, group_index)
    remaining[group_index] = remaining_for_share - 1
    storage.recovery_shares.set(index_with_group_offset, words)

    if remaining.count(0) < group_threshold:
        return None, group_index, index  # we need more shares

    if len(remaining) > 1:
        mnemonics = []
        for i, r in enumerate(remaining):
            # if we have multiple groups pass only the ones with threshold reached
            if r == 0:
                group = storage.recovery_shares.fetch_group(i)
                mnemonics.extend(group)
    else:
        mnemonics = storage.recovery_shares.fetch()

    identifier, iteration_exponent, secret = slip39.combine_mnemonics(mnemonics)
    return secret, group_index, index
