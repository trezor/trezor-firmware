from micropython import const

from trezor import io, ui, wire
from trezor.crypto import hmac
from trezor.crypto.hashlib import sha256
from trezor.ui.confirm import CONFIRMED, Confirm
from trezor.ui.text import Text
from trezor.utils import consteq

from apps.common import storage
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
        btn_confirm = "Retry"
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
        btn_confirm = "Retry"
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
    return "/trezor/device_%s" % storage.device.get_device_id().lower()


def _get_salt_path(new: bool = False) -> str:
    if new:
        return "%s/salt.new" % _get_device_dir()
    else:
        return "%s/salt" % _get_device_dir()


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

            # Load salt if it exists.
            salt = None  # type: Optional[bytearray]
            try:
                with fs.open(salt_path, "r") as f:
                    salt = bytearray(SD_SALT_LEN_BYTES)
                    salt_tag = bytearray(SD_SALT_AUTH_TAG_LEN_BYTES)
                    f.read(salt)
                    f.read(salt_tag)
            except OSError:
                salt = None

            if salt is not None and consteq(
                hmac.new(salt_auth_key, salt, sha256).digest()[
                    :SD_SALT_AUTH_TAG_LEN_BYTES
                ],
                salt_tag,
            ):
                return salt

            # Load salt.new if it exists.
            new_salt = None  # type: Optional[bytearray]
            try:
                with fs.open(new_salt_path, "r") as f:
                    new_salt = bytearray(SD_SALT_LEN_BYTES)
                    new_salt_tag = bytearray(SD_SALT_AUTH_TAG_LEN_BYTES)
                    f.read(new_salt)
                    f.read(new_salt_tag)
            except OSError:
                new_salt = None

            if new_salt is not None and consteq(
                hmac.new(salt_auth_key, new_salt, sha256).digest()[
                    :SD_SALT_AUTH_TAG_LEN_BYTES
                ],
                new_salt_tag,
            ):
                # SD salt regeneration was interrupted earlier. Bring into consistent state.
                # TODO Possibly overwrite salt file with random data.
                try:
                    fs.unlink(salt_path)
                except OSError:
                    pass
                fs.rename(new_salt_path, salt_path)
                return new_salt
        finally:
            fs.unmount()
            sd.power(False)

        await _wrong_card_dialog(ctx)


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
        raise IOError

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
        raise IOError

    try:
        fs.mount()
        # TODO Possibly overwrite salt file with random data.
        fs.unlink(salt_path)
    finally:
        fs.unmount()
        sd.power(False)
