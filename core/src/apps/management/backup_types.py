from trezor.crypto.slip39 import Share
from trezor.enums import BackupType

_BIP39_WORD_COUNTS = (12, 18, 24)
_SLIP39_WORD_COUNTS = (20, 33)


def is_slip39_word_count(word_count: int) -> bool:
    """
    Returns True for SLIP-39 and False for BIP-39.
    Raise RuntimeError otherwise.
    """
    if word_count in _SLIP39_WORD_COUNTS:
        return True
    elif word_count in _BIP39_WORD_COUNTS:
        return False
    # Unknown word count.
    raise RuntimeError


def is_slip39_backup_type(backup_type: BackupType) -> bool:
    return backup_type in (BackupType.Slip39_Basic, BackupType.Slip39_Advanced)


def infer_backup_type(is_slip39: bool, share: Share | None = None) -> BackupType:
    if not is_slip39:  # BIP-39
        return BackupType.Bip39
    elif not share or share.group_count < 1:  # invalid parameters
        raise RuntimeError
    elif share.group_count == 1:
        return BackupType.Slip39_Basic
    else:
        return BackupType.Slip39_Advanced
