from trezor.crypto import bip39, slip39
from trezor.errors import GroupThresholdReachedError, MnemonicError

from apps.common import storage

if False:
    from typing import Optional, Tuple


class RecoveryAborted(Exception):
    pass


def process_bip39(words: str) -> bytes:
    """
    Receives single mnemonic and processes it. Returns what is then stored
    in the storage, which is the mnemonic itself for BIP-39.
    """
    if not bip39.check(words):
        raise MnemonicError()
    return words.encode()


def process_slip39(words: str) -> Tuple[Optional[bytes], int, int]:
    """
    Processes a single mnemonic share. Returns the encrypted master secret
    (or None if more shares are needed) and the share's group index and member index.
    """
    share = slip39.decode_mnemonic(words)

    remaining = storage.recovery.fetch_slip39_remaining_shares()
    # TODO: move this whole logic to storage
    index_with_group_offset = share.index + share.group_index * slip39.MAX_SHARE_COUNT

    # if this is the first share, parse and store metadata
    if not remaining:
        storage.recovery.set_slip39_group_count(share.group_count)
        storage.recovery.set_slip39_group_threshold(share.group_threshold)
        storage.recovery.set_slip39_iteration_exponent(share.iteration_exponent)
        storage.recovery.set_slip39_identifier(share.identifier)
        storage.recovery.set_slip39_threshold(share.threshold)
        storage.recovery.set_slip39_remaining_shares(
            share.threshold - 1, share.group_index
        )
        storage.recovery_shares.set(index_with_group_offset, words)

        # if share threshold and group threshold are 1
        # we can calculate the secret right away
        if share.threshold == 1 and share.group_threshold == 1:
            identifier, iteration_exponent, secret, _ = slip39.combine_mnemonics(words)
            return secret, share.group_index, share.index
        else:
            return None, share.group_index, share.index  # we need more shares

    if remaining[share.group_index] == 0:
        raise GroupThresholdReachedError()

    # These should be checked by UI before so it's a Runtime exception otherwise
    if share.identifier != storage.recovery.get_slip39_identifier():
        raise RuntimeError("Slip39: Share identifiers do not match")
    if storage.recovery_shares.get(index_with_group_offset):
        raise RuntimeError("Slip39: This mnemonic was already entered")

    remaining_for_share = (
        storage.recovery.get_slip39_remaining_shares(share.group_index)
        or share.threshold
    )
    storage.recovery.set_slip39_remaining_shares(
        remaining_for_share - 1, share.group_index
    )
    remaining[share.group_index] = remaining_for_share - 1
    storage.recovery_shares.set(index_with_group_offset, words)

    if remaining.count(0) < share.group_threshold:
        return None, share.group_index, share.index  # we need more shares

    if len(remaining) > 1:
        mnemonics = []
        for i, r in enumerate(remaining):
            # if we have multiple groups pass only the ones with threshold reached
            if r == 0:
                group = storage.recovery_shares.fetch_group(i)
                mnemonics.extend(group)
    else:
        mnemonics = storage.recovery_shares.fetch()

    identifier, iteration_exponent, secret, _ = slip39.combine_mnemonics(mnemonics)
    return secret, share.group_index, share.index
