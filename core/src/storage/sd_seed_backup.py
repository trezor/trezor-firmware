from micropython import const
from typing import TYPE_CHECKING

import storage.device
from trezor import io, utils
from trezor.sdcard import with_filesystem
from trezorcrypto import crc

if utils.USE_SD_CARD:
    fatfs = io.fatfs  # global_import_cache
    sdcard = io.sdcard  # global_import_cache
    SDCARD_BLOCK_SIZE_B = sdcard.BLOCK_SIZE  # global_import_cache
    SDBACKUP_BLOCK_START = 66_138
    SDBACKUP_BLOCK_OFFSET = 130  # TODO arbitrary for now
    SDBACKUP_MAGIC = b"TRZS"
    SDBACKUP_VERSION = b"00"

# TODO with_filesystem can be just with_sdcard, unnecessary to mount FS for recovery


@with_filesystem
def store_seed_on_sdcard(mnemonic_secret: bytes) -> bool:
    _write_seed_unalloc(mnemonic_secret)
    _write_seed_plain_text(mnemonic_secret)
    if _verify_backup(mnemonic_secret):
        _write_readme()
        return True
    else:
        return False


@with_filesystem
def recover_seed_from_sdcard() -> str | None:
    return _read_seed_unalloc()


@with_filesystem
def _verify_backup(mnemonic_secret: bytes) -> bool:
    mnemonic_read_plain = _read_seed_plain_text()
    mnemonic_read_unalloc = _read_seed_unalloc()
    if mnemonic_read_plain is None:
        return False
    if mnemonic_read_unalloc is None:
        return False

    return (
        mnemonic_read_plain.encode() == mnemonic_secret
        and mnemonic_read_unalloc.encode() == mnemonic_secret
    )


@with_filesystem
def _write_seed_unalloc(mnemonic_secret: bytes) -> None:
    block_to_write = _encode_mnemonic_to_backup_block(mnemonic_secret)
    for block_idx in _storage_blocks_gen():
        # print(f"block_idx: {block_idx}, writing: {block_to_write[10:10+4]}")
        sdcard.write(block_idx, block_to_write)


@with_filesystem
def _read_seed_unalloc() -> str | None:
    block_buffer = bytearray(SDCARD_BLOCK_SIZE_B)
    for block_idx in _storage_blocks_gen():
        try:
            sdcard.read(block_idx, block_buffer)
            mnemonic_read = _decode_mnemonic_from_backup_block(block_buffer)
            if mnemonic_read is not None:
                break
        except fatfs.FatFSError:
            return None
    # print(f"_read_seed_unalloc: block_read: {block_read}")
    mnemonic_read_decoded = mnemonic_read.decode("utf-8").rstrip("\x00")
    # print(f"_read_seed_unalloc: mnemonic_read_decoded: {mnemonic_read_decoded}")
    return mnemonic_read_decoded


def _storage_blocks_gen() -> Generator:
    cap = sdcard.capacity()
    if cap == 0:
        raise ProcessError
    BLOCK_END = cap // SDCARD_BLOCK_SIZE_B - 1
    return range(SDBACKUP_BLOCK_START, BLOCK_END, SDBACKUP_BLOCK_OFFSET)

"""
Backup Memory Block Layout:
+----------------------+----------------------+----------------------+-------------------------------+
| SDBACKUP_MAGIC (4B) | SDBACKUP_VERSION (2B)| SEED_LENGTH (4B)      | MNEMONIC (variable length)    |
+----------------------+----------------------+----------------------+-------------------------------+
| CHECKSUM (4B)                                                              | Padding (variable)         |
+----------------------------------------------------------------------------+----------------------------+

- SDBACKUP_MAGIC: 4 bytes magic number identifying the backup block
- SDBACKUP_VERSION: 2 bytes representing the version of the backup format
- SEED_LENGTH: 4 bytes (big-endian) indicating the length of the mnemonic
- MNEMONIC: Variable length field containing the mnemonic
- CHECKSUM: 4 bytes CRC32 checksum of all previous fields
- Padding: Remaining bytes of the block (if any) are padding

The total size of the block is defined by SDCARD_BLOCK_SIZE_B.
"""
# Constants for offsets and lengths
MAGIC_OFFSET = 0
MAGIC_LENGTH = 4
VERSION_OFFSET = MAGIC_OFFSET + MAGIC_LENGTH
VERSION_LENGTH = 2
SEED_LEN_OFFSET = VERSION_OFFSET + VERSION_LENGTH
SEED_LEN_LENGTH = 4
MNEMONIC_OFFSET = SEED_LEN_OFFSET + SEED_LEN_LENGTH
CHECKSUM_LENGTH = 4


def _encode_mnemonic_to_backup_block(mnemonic: bytes) -> bytes:
    ret = bytearray(SDCARD_BLOCK_SIZE_B)
    magic = SDBACKUP_MAGIC + SDBACKUP_VERSION
    seed_len = len(mnemonic)
    ret[MAGIC_OFFSET : MAGIC_OFFSET + MAGIC_LENGTH] = magic
    ret[SEED_LEN_OFFSET : SEED_LEN_OFFSET + SEED_LEN_LENGTH] = seed_len.to_bytes(
        SEED_LEN_LENGTH, "big"
    )
    ret[MNEMONIC_OFFSET : MNEMONIC_OFFSET + seed_len] = mnemonic
    checksum = crc.crc32(ret[: MNEMONIC_OFFSET + seed_len])
    ret[
        MNEMONIC_OFFSET + seed_len : MNEMONIC_OFFSET + seed_len + CHECKSUM_LENGTH
    ] = checksum.to_bytes(CHECKSUM_LENGTH, "big")
    return bytes(ret)


def _decode_mnemonic_from_backup_block(block: bytes) -> bytes | None:
    assert len(block) == SDCARD_BLOCK_SIZE_B
    if len(block) != SDCARD_BLOCK_SIZE_B:
        return None
    if block[MAGIC_OFFSET : MAGIC_OFFSET + MAGIC_LENGTH] != SDBACKUP_MAGIC:
        return None
    seed_len = int.from_bytes(
        block[SEED_LEN_OFFSET : SEED_LEN_OFFSET + SEED_LEN_LENGTH], "big"
    )
    checksum_expected = crc.crc32(block[: MNEMONIC_OFFSET + seed_len])
    checksum_read = int.from_bytes(
        block[
            MNEMONIC_OFFSET + seed_len : MNEMONIC_OFFSET + seed_len + CHECKSUM_LENGTH
        ],
        "big",
    )
    if checksum_expected == checksum_read:
        return block[MNEMONIC_OFFSET : MNEMONIC_OFFSET + seed_len]
    else:
        return None


@with_filesystem
def _write_readme() -> None:
    with fatfs.open("README.txt", "w") as f:
        f.write("This is a Trezor backup SD card.")


@with_filesystem
def _write_seed_plain_text(mnemonic_secret: bytes) -> None:
    # TODO to be removed, just for testing purposes
    fatfs.mkdir("/trezor", True)
    with fatfs.open("/trezor/seed.txt", "w") as f:
        f.write(mnemonic_secret)


@with_filesystem
def _read_seed_plain_text() -> str | None:
    # TODO to be removed, just for testing purposes
    mnemonic_read = bytearray(SDCARD_BLOCK_SIZE_B)
    try:
        with fatfs.open("/trezor/seed.txt", "r") as f:
            f.read(mnemonic_read)
    except fatfs.FatFSError:
        return None
    # print(f"_read_seed_plain_text: mnemonic_read: {mnemonic_read}")
    return mnemonic_read.decode("utf-8").rstrip("\x00")
