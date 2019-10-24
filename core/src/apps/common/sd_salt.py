from micropython import const

from trezor import io, ui, wire
from trezor.crypto import hmac
from trezor.crypto.hashlib import sha256
from trezor.ui.confirm import CONFIRMED, Confirm
from trezor.ui.text import Text
from trezor.utils import consteq

from apps.common.confirm import confirm

if False:
    from typing import Optional


class SdProtectCancelled(Exception):
    pass


SD_CARD_HOT_SWAPPABLE = False
SD_SALT_LEN_BYTES = const(32)
SD_SALT_AUTH_TAG_LEN_BYTES = const(16)
SD_SALT_AUTH_KEY_LEN_BYTES = const(16)


async def _wrong_card_dialog(ctx: Optional[wire.Context]) -> None:
    text = Text("SD card protection", ui.ICON_WRONG)
    text.bold("Wrong SD card.")
    text.br_half()
    if SD_CARD_HOT_SWAPPABLE:
        text.normal("Please insert the", "correct SD card for", "this device.")
        btn_confirm = "Retry"  # type: Optional[str]
        btn_cancel = "Abort"
    else:
        text.normal("Please unplug the", "device and insert the", "correct SD card.")
        btn_confirm = None
        btn_cancel = "Close"

    if ctx is None:
        if await Confirm(text, confirm=btn_confirm, cancel=btn_cancel) is not CONFIRMED:
            raise SdProtectCancelled
    else:
        if not await confirm(ctx, text, confirm=btn_confirm, cancel=btn_cancel):
            raise wire.ProcessError("Wrong SD card.")


async def _insert_card_dialog(ctx: Optional[wire.Context]) -> None:
    text = Text("SD card protection", ui.ICON_WRONG)
    text.bold("SD card required.")
    text.br_half()
    if SD_CARD_HOT_SWAPPABLE:
        text.normal("Please insert your", "SD card.")
        btn_confirm = "Retry"  # type: Optional[str]
        btn_cancel = "Abort"
    else:
        text.normal("Please unplug the", "device and insert your", "SD card.")
        btn_confirm = None
        btn_cancel = "Close"

    if ctx is None:
        if await Confirm(text, confirm=btn_confirm, cancel=btn_cancel) is not CONFIRMED:
            raise SdProtectCancelled
    else:
        if not await confirm(ctx, text, confirm=btn_confirm, cancel=btn_cancel):
            raise wire.ProcessError("SD card required.")


async def _write_failed_dialog(ctx: Optional[wire.Context]) -> None:
    text = Text("SD card protection", ui.ICON_WRONG, ui.RED)
    text.normal("Failed to write data to", "the SD card.")
    if ctx is None:
        if await Confirm(text, confirm="Retry", cancel="Abort") is not CONFIRMED:
            raise OSError
    else:
        if not await confirm(ctx, text, confirm="Retry", cancel="Abort"):
            raise wire.ProcessError("Failed to write to SD card.")


def _get_device_dir() -> str:
    from apps.common.storage.device import get_device_id

    return "/trezor/device_%s" % get_device_id().lower()


def _get_salt_path(new: bool = False) -> str:
    if new:
        return "%s/salt.new" % _get_device_dir()
    else:
        return "%s/salt" % _get_device_dir()


def _load_salt(fs: io.FatFS, auth_key: bytes, path: str) -> Optional[bytearray]:
    # Load the salt file if it exists.
    try:
        with fs.open(path, "r") as f:
            salt = bytearray(SD_SALT_LEN_BYTES)
            stored_tag = bytearray(SD_SALT_AUTH_TAG_LEN_BYTES)
            f.read(salt)
            f.read(stored_tag)
    except OSError:
        return None

    # Check the salt's authentication tag.
    computed_tag = hmac.new(auth_key, salt, sha256).digest()[
        :SD_SALT_AUTH_TAG_LEN_BYTES
    ]
    if not consteq(computed_tag, stored_tag):
        return None

    return salt


async def request_sd_salt(
    ctx: Optional[wire.Context], salt_auth_key: bytes
) -> bytearray:
    salt_path = _get_salt_path()
    new_salt_path = _get_salt_path(True)

    while True:
        sd = io.SDCard()
        fs = io.FatFS()
        while not sd.power(True):
            await _insert_card_dialog(ctx)

        try:
            fs.mount()
            salt = _load_salt(fs, salt_auth_key, salt_path)
            if salt is not None:
                return salt

            # Check if there is a new salt.
            salt = _load_salt(fs, salt_auth_key, new_salt_path)
            if salt is not None:
                # SD salt regeneration was interrupted earlier. Bring into consistent state.
                # TODO Possibly overwrite salt file with random data.
                try:
                    fs.unlink(salt_path)
                except OSError:
                    pass

                try:
                    fs.rename(new_salt_path, salt_path)
                except OSError:
                    error_dialog = _write_failed_dialog(ctx)
                else:
                    return salt
            else:
                # No valid salt file on this SD card.
                error_dialog = _wrong_card_dialog(ctx)
        finally:
            fs.unmount()
            sd.power(False)

        await error_dialog


async def set_sd_salt(
    ctx: Optional[wire.Context], salt: bytes, salt_tag: bytes, new: bool = False
) -> None:
    salt_path = _get_salt_path(new)

    while True:
        sd = io.SDCard()
        while not sd.power(True):
            await _insert_card_dialog(ctx)

        try:
            fs = io.FatFS()
            fs.mount()
            fs.mkdir("/trezor", True)
            fs.mkdir(_get_device_dir(), True)
            with fs.open(salt_path, "w") as f:
                f.write(salt)
                f.write(salt_tag)
            break
        except Exception:
            fs.unmount()
            sd.power(False)
            await _write_failed_dialog(ctx)

    fs.unmount()
    sd.power(False)


async def stage_sd_salt(
    ctx: Optional[wire.Context], salt: bytes, salt_tag: bytes
) -> None:
    await set_sd_salt(ctx, salt, salt_tag, True)


async def commit_sd_salt(ctx: Optional[wire.Context]) -> None:
    salt_path = _get_salt_path()
    new_salt_path = _get_salt_path(True)

    sd = io.SDCard()
    fs = io.FatFS()
    if not sd.power(True):
        raise OSError

    try:
        fs.mount()
        # TODO Possibly overwrite salt file with random data.
        try:
            fs.unlink(salt_path)
        except OSError:
            pass
        fs.rename(new_salt_path, salt_path)
    finally:
        fs.unmount()
        sd.power(False)


async def remove_sd_salt(ctx: Optional[wire.Context]) -> None:
    salt_path = _get_salt_path()

    sd = io.SDCard()
    fs = io.FatFS()
    if not sd.power(True):
        raise OSError

    try:
        fs.mount()
        # TODO Possibly overwrite salt file with random data.
        fs.unlink(salt_path)
    finally:
        fs.unmount()
        sd.power(False)
