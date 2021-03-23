import storage.recovery
from trezor.enums import BackupType

from . import recover


class WordValidityResult(Exception):
    pass


class IdentifierMismatch(WordValidityResult):
    pass


class AlreadyAdded(WordValidityResult):
    pass


class ThresholdReached(WordValidityResult):
    pass


def check(backup_type: BackupType | None, partial_mnemonic: list[str]) -> None:
    # we can't perform any checks if the backup type was not yet decided
    if backup_type is None:
        return
    # there are no "on-the-fly" checks for BIP-39
    if backup_type is BackupType.Bip39:
        return

    previous_mnemonics = recover.fetch_previous_mnemonics()
    if previous_mnemonics is None:
        # this should not happen if backup_type is set
        raise RuntimeError

    if backup_type == BackupType.Slip39_Basic:
        check_slip39_basic(partial_mnemonic, previous_mnemonics)
    elif backup_type == BackupType.Slip39_Advanced:
        check_slip39_advanced(partial_mnemonic, previous_mnemonics)
    else:
        # there are no other backup types
        raise RuntimeError


def check_slip39_basic(
    partial_mnemonic: list[str], previous_mnemonics: list[list[str]]
) -> None:
    # check if first 3 words of mnemonic match
    # we can check against the first one, others were checked already
    current_index = len(partial_mnemonic) - 1
    current_word = partial_mnemonic[-1]
    if current_index < 3:
        share_list = previous_mnemonics[0][0].split(" ")
        if share_list[current_index] != current_word:
            raise IdentifierMismatch
    elif current_index == 3:
        for share in previous_mnemonics[0]:
            share_list = share.split(" ")
            # check if the fourth word is different from previous shares
            if share_list[current_index] == current_word:
                raise AlreadyAdded


def check_slip39_advanced(
    partial_mnemonic: list[str], previous_mnemonics: list[list[str]]
) -> None:
    current_index = len(partial_mnemonic) - 1
    current_word = partial_mnemonic[-1]

    if current_index < 2:
        share_list = next(s for s in previous_mnemonics if s)[0].split(" ")
        if share_list[current_index] != current_word:
            raise IdentifierMismatch
    # check if we reached threshold in group
    elif current_index == 2:
        for i, group in enumerate(previous_mnemonics):
            if len(group) > 0:
                if current_word == group[0].split(" ")[current_index]:
                    remaining_shares = storage.recovery.fetch_slip39_remaining_shares()
                    # if backup_type is not None, some share was already entered -> remaining needs to be set
                    assert remaining_shares is not None
                    if remaining_shares[i] == 0:
                        raise ThresholdReached

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
                    raise AlreadyAdded
