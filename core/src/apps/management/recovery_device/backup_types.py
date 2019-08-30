from trezor.messages import BackupType

# possible backup types based on the number of words
TYPES = {
    12: [BackupType.Bip39],
    18: [BackupType.Bip39],
    24: [BackupType.Bip39],
    20: [BackupType.Slip39_Basic, BackupType.Slip39_Advanced],
    33: [BackupType.Slip39_Basic, BackupType.Slip39_Advanced],
}


def get(word_count: int) -> int:
    """
    Returns possible backup types inferred from the word count.
    """
    if word_count not in TYPES:
        raise RuntimeError("Recovery: Unknown words count")
    return TYPES[word_count]


def is_slip39(backup: list) -> bool:
    return BackupType.Slip39_Basic in backup or BackupType.Slip39_Advanced in backup
