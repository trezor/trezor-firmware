from trezor import io, utils
from trezor.sdcard import with_filesystem

if utils.USE_SD_CARD:
    fatfs = io.fatfs  # global_import_cache


async def sdcard_backup_seed(mnemonic_secret: bytes) -> None:
    from apps.common.sdcard import ensure_sdcard

    await ensure_sdcard()
    _write_seed_plain_text(mnemonic_secret)


async def sdcard_recover_seed() -> str | None:
    from apps.common.sdcard import ensure_sdcard

    await ensure_sdcard(ensure_filesystem=False)
    return _read_seed_plain_text()


def sdcard_verify_backup(mnemonic_secret: bytes) -> bool:
    mnemonic_read = _read_seed_plain_text()
    if mnemonic_read is None:
        return False

    return mnemonic_read.encode() == mnemonic_secret

@with_filesystem
def _write_seed_plain_text(mnemonic_secret: bytes) -> None:
    # TODO to be removed, just for testing purposes
    fatfs.mkdir("/trezor", True)
    with fatfs.open("/trezor/seed.txt", "w") as f:
        f.write(mnemonic_secret)

@with_filesystem
def _read_seed_plain_text() -> str | None:
    # TODO to be removed, just for testing purposes
    mnemonic_read = bytearray(512)
    try:
        with fatfs.open("/trezor/seed.txt", "r") as f:
            f.read(mnemonic_read)
    except fatfs.FatFSError:
        return None
    return mnemonic_read.decode('utf-8').rstrip('\x00')
