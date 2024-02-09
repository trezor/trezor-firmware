from micropython import const
from trezorcrypto import sha256
from typing import TYPE_CHECKING

from trezor import io, utils
from trezor.enums import BackupType
from trezor.sdcard import with_filesystem, with_sdcard
from trezor.wire import DataError, ProcessError
from trezor.messages import SdCardBackupHealth

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
    SDBACKUP_N_WRITINGS = 100  # TODO arbitrary for now
    SDBACKUP_N_VERIFY = 10
    assert SDBACKUP_N_WRITINGS >= SDBACKUP_N_VERIFY
    SDBACKUP_MAGIC = b"TRZM"
    SDBACKUP_VERSION = 0
    README_PATH = "README.txt"
    README_CONTENT = b"This is a Trezor backup SD card."
    EXPECTED_FS_CAP_B = 33_550_336  # TODO a programmatic approach to get to this number


# TODO enum might be a part of protobuf message, depends on the product
class BackupMedium(IntEnum):
    Words = 0
    SDCard = 1


@with_sdcard
def store_seed_on_sdcard(mnemonic_secret: bytes, backup_type: BackupType) -> None:
    _write_seed_unalloc(mnemonic_secret, backup_type)
    if _verify_backup(mnemonic_secret, backup_type):
        # FIXME _write_readme might raise, should handle here
        _write_readme()
    else:
        raise ProcessError("SD card verification failed")


@with_sdcard
def recover_seed_from_sdcard() -> tuple[bytes | None, BackupType | None]:
    return _read_seed_unalloc()


@with_sdcard
def is_backup_present_on_sdcard() -> bool:
    decoded_mnemonic, decoded_backup_type = _read_seed_unalloc()
    return decoded_mnemonic is not None and decoded_backup_type is not None


@with_sdcard
def check_health_of_backup_sdcard(mnemonic_secret: bytes | None) -> SdCardBackupHealth:
    def pt_check(r: SdCardBackupHealth) -> None:
        """
        Partition check:
        1) is the partition valid?
        -> if so:
        2) is the size correct?
        3) README still present with valid content?
        4) canary (TODO) still present?
        5) other files appeared? TODO
        """
        try:
            fatfs.mount()
            r.pt_is_mountable = True
            r.pt_has_correct_cap = fatfs.get_capacity() == EXPECTED_FS_CAP_B
            try:
                with fatfs.open(README_PATH, "r") as f:
                    read_data = bytearray(len(README_CONTENT))
                    f.read(read_data)
                    r.pt_readme_present = True
                    r.pt_readme_content = read_data == README_CONTENT
            except fatfs.FileNotFound:
                r.pt_readme_present = False
            except fatfs.FatFSError:
                r.pt_readme_content = False
        except fatfs.NoFilesystem:
            r.pt_is_mountable = False

    def unalloc_check(r: SdCardBackupHealth) -> None:
        """
        # Unallocated space check:
        # 1) count the number of corrupted seed writings at unallocated space
        """
        block_buffer = bytearray(SDCARD_BLOCK_SIZE_B)

        # If secret is supplied (expected for BIP-39), verify backup block against seed currently stored on the device.
        # If secret is not supplied (expected for SLIP-39), check that backup blocks have valid hashes.
        if mnemonic_secret is None:
            verify_func = lambda block_idx: _verify_backup_block_by_hash(
                block_idx, block_buffer
            )
        else:
            verify_func = lambda block_idx: _verify_backup_block_by_seed(
                mnemonic_secret, BackupType.Bip39, block_idx, block_buffer
            )

        res.unalloc_seed_corrupt = sum(
            1 for block_idx in _storage_blocks_gen() if not verify_func(block_idx)
        )

    res = SdCardBackupHealth(
        pt_is_mountable=False,
        pt_has_correct_cap=False,
        pt_readme_present=False,
        pt_readme_content=False,
        unalloc_seed_corrupt=SDBACKUP_N_WRITINGS,
    )
    pt_check(res)
    unalloc_check(res)
    return res


@with_sdcard
def refresh_backup_sdcard(mnemonic_secret: bytes | None) -> bool:
    # proceed only if backup is present
    # this also means that refresh won't be possible on complete wiped SD card
    decoded_mnemonic, decoded_backup_type = _read_seed_unalloc()
    if decoded_mnemonic is None or decoded_backup_type is None:
        return False

    if mnemonic_secret is not None and mnemonic_secret != decoded_mnemonic:
        # If secret is supplied (expected for BIP-39), we expect that the seed on the card corresponds to the one on the device.
        return False
    # If secrect is not supplied (expected for SLIP39) or the secret corresponds to the one decoded from card, refresh.
    fatfs.mkfs(True)
    store_seed_on_sdcard(decoded_mnemonic, decoded_backup_type)
    return True


@with_sdcard
def wipe_backup_sdcard() -> None:
    empty_block = bytes([0xFF] * SDCARD_BLOCK_SIZE_B)
    # erase first 1MiB to erase filesystem partition table
    for block_idx in range(2048 // SDCARD_BLOCK_SIZE_B):
        sdcard.write(block_idx, empty_block)
    # erase backup blocks
    for block_idx in _storage_blocks_gen():
        sdcard.write(block_idx, empty_block)


def _verify_backup(mnemonic_secret: bytes, backup_type: BackupType) -> bool:
    # verify SDBACKUP_N_VERIFY blocks at random
    from trezor.crypto import random

    block_buffer = bytearray(SDCARD_BLOCK_SIZE_B)
    all_backup_blocks = list(_storage_blocks_gen())
    for _ in range(SDBACKUP_N_VERIFY):
        rand_idx = random.uniform(len(all_backup_blocks))
        if not _verify_backup_block_by_seed(
            mnemonic_secret, backup_type, all_backup_blocks[rand_idx], block_buffer
        ):
            return False
    return True


def _verify_backup_block_by_seed(
    mnemonic_secret: bytes, backup_type: BackupType, block_idx: int, buf: bytearray
) -> bool:
    sdcard.read(block_idx, buf)
    decoded_mnemonic, decoded_backup_type = _decode_backup_block(buf)
    if decoded_mnemonic is None or decoded_backup_type is None:
        return False
    if decoded_mnemonic != mnemonic_secret or decoded_backup_type != backup_type:
        return False
    return True


def _verify_backup_block_by_hash(block_idx: int, buf: bytearray) -> bool:
    sdcard.read(block_idx, buf)
    return _decode_backup_block(buf) != (None, None)


def _write_seed_unalloc(mnemonic_secret: bytes, backup_type: BackupType) -> None:
    # TODO: should we re-raise if sdcard.write fails?
    block_to_write = _encode_backup_block(mnemonic_secret, backup_type)
    for block_idx in _storage_blocks_gen():
        sdcard.write(block_idx, block_to_write)


def _read_seed_unalloc() -> tuple[bytes | None, BackupType | None]:
    block_buffer = bytearray(SDCARD_BLOCK_SIZE_B)
    (decoded_mnemonic, decoded_backup_type) = (None, None)
    for block_idx in _storage_blocks_gen():
        try:
            sdcard.read(block_idx, block_buffer)
            decoded_mnemonic, decoded_backup_type = _decode_backup_block(block_buffer)
            if (decoded_mnemonic, decoded_backup_type) != (None, None):
                break
        except Exception:
            return (None, None)
    return (decoded_mnemonic, decoded_backup_type)


def _storage_blocks_gen() -> Generator[int, None, None]:
    cap = sdcard.capacity()
    if cap == 0:
        raise ProcessError("SD card operation failed")
    BLOCK_END = cap // SDCARD_BLOCK_SIZE_B - 1
    return (
        SDBACKUP_BLOCK_START
        + n * (BLOCK_END - SDBACKUP_BLOCK_START) // (SDBACKUP_N_WRITINGS - 1)
        for n in range(SDBACKUP_N_WRITINGS)
    )


def _write_readme() -> None:
    fatfs.mount()
    with fatfs.open(README_PATH, "x") as f:
        f.write(README_CONTENT)
    fatfs.unmount()


# Backup Memory Block Layout:
# +----------------------+------------------------+--------------------+-------------------------------+
# | SDBACKUP_MAGIC (4B)  | SDBACKUP_VERSION (2B)  | BACKUP_TYPE (1B)   | SEED_LENGTH (2B)              |
# +----------------------+------------------------+--------------------+-------------------------------+
# | MNEMONIC (variable length)                    | HASH (32B)         | Padding (variable)            |
# +-----------------------------------------------+--------------------+-------------------------------+
#
# - SDBACKUP_MAGIC: 4 bytes magic number identifying the backup block
# - SDBACKUP_VERSION: 2 bytes representing the version of the backup format (for future compatibility)
# - BACKUP_TYPE: 1 bytes representing the version of the backup format
# - SEED_LENGTH: 2 bytes (big-endian) indicating the length of the mnemonic
# - MNEMONIC: Variable length field containing the mnemonic
# - HASH: 32 bytes sha256 hash of all previous fields
# - Padding: Remaining bytes of the block (if any) are padding
#
# The total size of the block is defined by SDCARD_BLOCK_SIZE_B.

MAGIC_LEN = const(4)
VERSION_LEN = const(2)
BACKUPTYPE_LEN = const(1)
SEEDLEN_LEN = const(2)
HASH_LEN = const(32)


def _encode_backup_block(mnemonic: bytes, backup_type: BackupType) -> bytes:
    ret = utils.empty_bytearray(SDCARD_BLOCK_SIZE_B)
    ret.extend(SDBACKUP_MAGIC)
    ret.extend(SDBACKUP_VERSION.to_bytes(VERSION_LEN, "big"))
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


def _decode_backup_block(block: bytes) -> tuple[bytes | None, BackupType | None]:
    from trezor.enums import BackupType

    assert len(block) == SDCARD_BLOCK_SIZE_B
    try:
        r = utils.BufferReader(block)
        if r.read_memoryview(MAGIC_LEN) != SDBACKUP_MAGIC:
            return (None, None)
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
            return (None, None)

    except (ValueError, EOFError):
        raise DataError("Trying to decode invalid SD card block.")
