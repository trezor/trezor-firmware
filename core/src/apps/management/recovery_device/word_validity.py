from micropython import const

import storage.recovery
from trezor.messages import BackupType

from apps.management.recovery_device import recover

if False:
    from typing import List, Optional
    from trezor.messages.ResetDevice import EnumTypeBackupType

OK = const(0)
NOK_IDENTIFIER_MISMATCH = const(1)
NOK_ALREADY_ADDED = const(2)
NOK_THRESHOLD_REACHED = const(3)


def check(
    backup_type: Optional[EnumTypeBackupType], partial_mnemonic: List[str]
) -> int:
    # we can't perform any checks if the backup type was not yet decided
    if backup_type is None:
        return OK
    # there are no "on-the-fly" checks for BIP-39
    if backup_type is BackupType.Bip39:
        return OK

    previous_mnemonics = recover.fetch_previous_mnemonics()
    if previous_mnemonics is None:
        # this should not happen if backup_type is set
        raise RuntimeError

    if backup_type == BackupType.Slip39_Basic:
        return check_slip39_basic(partial_mnemonic, previous_mnemonics)

    if backup_type == BackupType.Slip39_Advanced:
        return check_slip39_advanced(partial_mnemonic, previous_mnemonics)

    # there are no other backup types
    raise RuntimeError


def check_slip39_basic(
    partial_mnemonic: List[str], previous_mnemonics: List[List[str]]
) -> int:
    # check if first 3 words of mnemonic match
    # we can check against the first one, others were checked already
    current_index = len(partial_mnemonic) - 1
    current_word = partial_mnemonic[-1]
    if current_index < 3:
        share_list = previous_mnemonics[0][0].split(" ")
        if share_list[current_index] != current_word:
            return NOK_IDENTIFIER_MISMATCH
    elif current_index == 3:
        for share in previous_mnemonics[0]:
            share_list = share.split(" ")
            # check if the fourth word is different from previous shares
            if share_list[current_index] == current_word:
                return NOK_ALREADY_ADDED

    return OK


def check_slip39_advanced(
    partial_mnemonic: List[str], previous_mnemonics: List[List[str]]
) -> int:
    current_index = len(partial_mnemonic) - 1
    current_word = partial_mnemonic[-1]
    if current_index < 2:
        share_list = next(s for s in previous_mnemonics if s)[0].split(" ")
        if share_list[current_index] != current_word:
            return NOK_IDENTIFIER_MISMATCH
    # check if we reached threshold in group
    elif current_index == 2:
        for i, group in enumerate(previous_mnemonics):
            if len(group) > 0:
                if current_word == group[0].split(" ")[current_index]:
                    remaining_shares = storage.recovery.fetch_slip39_remaining_shares()
                    # if backup_type is not None, some share was already entered -> remaining needs to be set
                    assert remaining_shares is not None
                    if remaining_shares[i] == 0:
                        return NOK_THRESHOLD_REACHED
    # check if share was already added for group
    elif current_index == 3:
        # we use the 3rd word from previously entered shares to find the group id
        group_identifier_word = partial_mnemonic[2]
        group_index = None
        for i, group in enumerate(previous_mnemonics):
            if len(group) > 0:
                if group_identifier_word == group[0].split(" ")[2]:
                    group_index = i

        if group_index is not None:
            group = previous_mnemonics[group_index]
            for share in group:
                if current_word == share.split(" ")[current_index]:
                    return NOK_ALREADY_ADDED

    return OK
