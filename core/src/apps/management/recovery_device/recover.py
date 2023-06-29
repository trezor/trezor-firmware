from typing import TYPE_CHECKING

import storage.recovery as storage_recovery
import storage.recovery_shares as storage_recovery_shares
from trezor.crypto import slip39

if TYPE_CHECKING:
    from trezor.enums import BackupType


class RecoveryAborted(Exception):
    pass


def process_bip39(words: str) -> bytes:
    """
    Receives single mnemonic and processes it. Returns what is then stored
    in the storage, which is the mnemonic itself for BIP-39.
    """
    from trezor.crypto import bip39
    from trezor.errors import MnemonicError

    if not bip39.check(words):
        raise MnemonicError
    return words.encode()


def process_slip39(words: str) -> tuple[bytes | None, slip39.Share]:
    """
    Processes a single mnemonic share. Returns the encrypted master secret
    (or None if more shares are needed) and the share's group index and member index.
    """
    share = slip39.decode_mnemonic(words)

    group_index = share.group_index  # local_cache_attribute

    remaining = storage_recovery.fetch_slip39_remaining_shares()

    # if this is the first share, parse and store metadata
    if not remaining:
        storage_recovery.set_slip39_group_count(share.group_count)
        storage_recovery.set_slip39_iteration_exponent(share.iteration_exponent)
        storage_recovery.set_slip39_identifier(share.identifier)
        storage_recovery.set_slip39_remaining_shares(share.threshold - 1, group_index)
        storage_recovery_shares.set(share.index, group_index, words)

        # if share threshold and group threshold are 1
        # we can calculate the secret right away
        if share.threshold == 1 and share.group_threshold == 1:
            _, _, secret = slip39.recover_ems([words])
            return secret, share
        else:
            # we need more shares
            return None, share

    # These should be checked by UI before so it's a Runtime exception otherwise
    if share.identifier != storage_recovery.get_slip39_identifier():
        raise RuntimeError("Slip39: Share identifiers do not match")
    if share.iteration_exponent != storage_recovery.get_slip39_iteration_exponent():
        raise RuntimeError("Slip39: Share exponents do not match")
    if storage_recovery_shares.get(share.index, group_index):
        raise RuntimeError("Slip39: This mnemonic was already entered")
    if share.group_count != storage_recovery.get_slip39_group_count():
        raise RuntimeError("Slip39: Group count does not match")

    remaining_for_share = (
        storage_recovery.get_slip39_remaining_shares(group_index) or share.threshold
    )
    storage_recovery.set_slip39_remaining_shares(remaining_for_share - 1, group_index)
    remaining[group_index] = remaining_for_share - 1
    storage_recovery_shares.set(share.index, group_index, words)

    if remaining.count(0) < share.group_threshold:
        # we need more shares
        return None, share

    if share.group_count > 1:
        mnemonics = []
        for i, r in enumerate(remaining):
            # if we have multiple groups pass only the ones with threshold reached
            if r == 0:
                group = storage_recovery_shares.fetch_group(i)
                mnemonics.extend(group)
    else:
        # in case of slip39 basic we only need the first and only group
        mnemonics = storage_recovery_shares.fetch_group(0)

    _, _, secret = slip39.recover_ems(mnemonics)
    return secret, share


if TYPE_CHECKING:
    Slip39State = tuple[int, BackupType] | tuple[None, None]


def load_slip39_state() -> Slip39State:
    from .. import backup_types

    previous_mnemonics = fetch_previous_mnemonics()
    if not previous_mnemonics:
        return None, None
    # let's get the first mnemonic and decode it to find out the metadata
    mnemonic = next(p[0] for p in previous_mnemonics if p)
    share = slip39.decode_mnemonic(mnemonic)
    word_count = len(mnemonic.split(" "))
    return word_count, backup_types.infer_backup_type(True, share)


def fetch_previous_mnemonics() -> list[list[str]] | None:
    mnemonics = []
    if not storage_recovery.get_slip39_group_count():
        return None
    for i in range(storage_recovery.get_slip39_group_count()):
        mnemonics.append(storage_recovery_shares.fetch_group(i))
    if not any(p for p in mnemonics):
        return None
    return mnemonics
