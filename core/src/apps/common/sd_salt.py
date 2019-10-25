import storage.sd_salt
from storage.sd_salt import SD_CARD_HOT_SWAPPABLE, SdSaltMismatch
from trezor import io, ui, wire
from trezor.ui.text import Text

from apps.common.confirm import confirm

if False:
    from typing import Optional


class SdProtectCancelled(Exception):
    pass


async def _wrong_card_dialog(ctx: wire.GenericContext) -> bool:
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

    return await confirm(ctx, text, confirm=btn_confirm, cancel=btn_cancel)


async def _insert_card_dialog(ctx: wire.GenericContext) -> None:
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

    if not await confirm(ctx, text, confirm=btn_confirm, cancel=btn_cancel):
        raise SdProtectCancelled


async def sd_write_failed_dialog(ctx: wire.GenericContext) -> bool:
    text = Text("SD card protection", ui.ICON_WRONG, ui.RED)
    text.normal("Failed to write data to", "the SD card.")
    return await confirm(ctx, text, confirm="Retry", cancel="Abort")


async def ensure_sd_card(ctx: wire.GenericContext) -> None:
    sd = io.SDCard()
    while not sd.power(True):
        await _insert_card_dialog(ctx)


async def request_sd_salt(
    ctx: wire.GenericContext = wire.DUMMY_CONTEXT
) -> Optional[bytearray]:
    while True:
        ensure_sd_card(ctx)
        try:
            return storage.sd_salt.load_sd_salt()
        except SdSaltMismatch as e:
            if not await _wrong_card_dialog(ctx):
                raise SdProtectCancelled from e
        except OSError:
            # This happens when there is both old and new salt file, and we can't move
            # new salt over the old salt. If the user clicks Retry, we will try again.
            if not await sd_write_failed_dialog(ctx):
                raise
