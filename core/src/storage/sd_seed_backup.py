from micropython import const
from trezorcrypto import sha256
from typing import TYPE_CHECKING

from trezor import io, utils
from trezor.enums import BackupType
from trezor.sdcard import with_filesystem, with_sdcard
from trezor.wire import DataError, ProcessError

if TYPE_CHECKING:
    from enum import IntEnum
    from typing import Generator
else:
    IntEnum = object

if utils.USE_SD_CARD:
    fatfs = io.fatfs  # global_import_cache
    sdcard = io.sdcard  # global_import_cache
    SDCARD_BLOCK_SIZE_B = sdcard.BLOCK_SIZE  # global_import_cache
    SDBACKUP_BLOCK_START = sdcard.BACKUP_BLOCK_START  # global_import_cache
    SDBACKUP_BLOCK_OFFSET = 130  # TODO arbitrary for now
    SDBACKUP_N_WRITINGS = 100  # TODO decide between offset/writings
    SDBACKUP_MAGIC = b"TRZM"
    SDBACKUP_VERSION = b"0"


class BackupMedium(IntEnum):
    Words = 0
    SDCard = 1


@with_filesystem
def store_seed_on_sdcard(mnemonic_secret: bytes, backup_type: BackupType) -> bool:
    _write_seed_unalloc(mnemonic_secret, backup_type)
    if _verify_backup(mnemonic_secret, backup_type):
        _write_readme()
        return True
    else:
        return False


@with_sdcard
def recover_seed_from_sdcard() -> tuple[bytes | None, BackupType | None]:
    return _read_seed_unalloc()


def _verify_backup(mnemonic_secret: bytes, backup_type: BackupType) -> bool:
    decoded_mnemonic, decoded_backup_type = _read_seed_unalloc()
    if decoded_mnemonic is None or decoded_backup_type is None:
        return False
    return decoded_mnemonic == mnemonic_secret and decoded_backup_type == backup_type


def _write_seed_unalloc(mnemonic_secret: bytes, backup_type: BackupType) -> None:
    block_to_write = _encode_backup_block(mnemonic_secret, backup_type)
    for block_idx in _storage_blocks_gen():
        sdcard.write(block_idx, block_to_write)


def _read_seed_unalloc() -> tuple[bytes | None, BackupType | None]:
    block_buffer = bytearray(SDCARD_BLOCK_SIZE_B)
    restored_block = None
    for block_idx in _storage_blocks_gen():
        try:
            sdcard.read(block_idx, block_buffer)
            restored_block = _decode_backup_block(block_buffer)
            if restored_block is not None:
                break
        except Exception:
            return (None, None)
    if restored_block is None:
        return (None, None)
    decoded_mnemonic, decoded_backup_type = restored_block
    return (decoded_mnemonic, decoded_backup_type)


def _storage_blocks_gen() -> Generator:
    return _storage_blocks_gen_by_n()


def _storage_blocks_gen_by_offset() -> Generator[int, None, None]:
    cap = sdcard.capacity()
    if cap == 0:
        raise ProcessError("SD card operation failed")
    BLOCK_END = cap // SDCARD_BLOCK_SIZE_B - 1
    for i in range(SDBACKUP_BLOCK_START, BLOCK_END, SDBACKUP_BLOCK_OFFSET):
        yield i


def _storage_blocks_gen_by_n() -> Generator[int, None, None]:
    cap = sdcard.capacity()
    if cap == 0:
        raise ProcessError("SD card operation failed")
    BLOCK_END = cap // SDCARD_BLOCK_SIZE_B - 1
    return (
        SDBACKUP_BLOCK_START
        + n * (BLOCK_END - SDBACKUP_BLOCK_START) // (SDBACKUP_N_WRITINGS - 1)
        for n in range(SDBACKUP_N_WRITINGS)
    )


# Backup Memory Block Layout:
# +----------------------+------------------------+--------------------+-------------------------------+
# | SDBACKUP_MAGIC (4B)  | SDBACKUP_VERSION (1B)  | BACKUP_TYPE (1B)   | SEED_LENGTH (4B)              |
# +----------------------+------------------------+--------------------+-------------------------------+
# | MNEMONIC (variable length)                    | HASH (32B)         | Padding (variable)            |
# +-----------------------------------------------+--------------------+-------------------------------+
#
# - SDBACKUP_MAGIC: 4 bytes magic number identifying the backup block
# - SDBACKUP_VERSION: 1 bytes representing the version of the backup format (for future compatibility)
# - BACKUP_TYPE: 1 bytes representing the version of the backup format
# - SEED_LENGTH: 4 bytes (big-endian) indicating the length of the mnemonic
# - MNEMONIC: Variable length field containing the mnemonic
# - HASH: 32 bytes sha256 hash of all previous fields
# - Padding: Remaining bytes of the block (if any) are padding
#
# The total size of the block is defined by SDCARD_BLOCK_SIZE_B.

MAGIC_LEN = const(4)
VERSION_LEN = const(1)
BACKUPTYPE_LEN = const(1)
SEEDLEN_LEN = const(4)
HASH_LEN = const(32)


def _encode_backup_block(mnemonic: bytes, backup_type: BackupType) -> bytes:
    ret = utils.empty_bytearray(SDCARD_BLOCK_SIZE_B)
    ret.extend(SDBACKUP_MAGIC)
    ret.extend(SDBACKUP_VERSION)
    ret.extend(backup_type.to_bytes(BACKUPTYPE_LEN, "big"))
    seed_len = len(mnemonic)
    ret.extend(seed_len.to_bytes(SEEDLEN_LEN, "big"))
    ret.extend(mnemonic)
    blockhash = sha256(ret[:]).digest()
    ret.extend(blockhash)
    assert len(ret) <= SDCARD_BLOCK_SIZE_B
    padding_len = SDCARD_BLOCK_SIZE_B - len(ret)
    ret.extend(b"\x00" * padding_len)
    return bytes(ret)


def _decode_backup_block(block: bytes) -> tuple[bytes, BackupType] | None:
    from trezor.enums import BackupType

    assert len(block) == SDCARD_BLOCK_SIZE_B
    try:
        r = utils.BufferReader(block)
        if r.read_memoryview(MAGIC_LEN) != SDBACKUP_MAGIC:
            return None
        r.read_memoryview(VERSION_LEN)  # skip the version for now
        backup_type = int.from_bytes(r.read_memoryview(BACKUPTYPE_LEN), "big")
        seed_len = int.from_bytes(r.read_memoryview(SEEDLEN_LEN), "big")
        mnemonic = r.read(seed_len)
        blockhash_read = r.read(HASH_LEN)
        r.seek(0)
        blockhash_expected = sha256(
            r.read_memoryview(
                MAGIC_LEN + VERSION_LEN + BACKUPTYPE_LEN + SEEDLEN_LEN + seed_len
            )
        ).digest()
        if blockhash_read == blockhash_expected and backup_type in (
            BackupType.Bip39,
            BackupType.Slip39_Basic,
            BackupType.Slip39_Advanced,
        ):
            return (mnemonic, backup_type)
        else:
            return None

    except (ValueError, EOFError):
        raise DataError("Trying to decode invalid SD card block.")


def _write_readme() -> None:
    with fatfs.open("README.txt", "w") as f:
        f.write(b"This is a Trezor backup SD card.")
