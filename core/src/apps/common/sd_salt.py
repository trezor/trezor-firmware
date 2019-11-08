import storage.sd_salt
from storage.sd_salt import SD_CARD_HOT_SWAPPABLE
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


async def insert_card_dialog(ctx: wire.GenericContext) -> bool:
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

    return await confirm(ctx, text, confirm=btn_confirm, cancel=btn_cancel)


async def sd_problem_dialog(ctx: wire.GenericContext) -> bool:
    text = Text("SD card protection", ui.ICON_WRONG, ui.RED)
    text.normal("There was a problem", "accessing the SD card.")
    return await confirm(ctx, text, confirm="Retry", cancel="Abort")


async def ensure_sd_card(ctx: wire.GenericContext) -> None:
    sd = io.SDCard()
    while not sd.present():
        if not await insert_card_dialog(ctx):
            raise SdProtectCancelled


async def request_sd_salt(
    ctx: wire.GenericContext = wire.DUMMY_CONTEXT
) -> Optional[bytearray]:
    while True:
        ensure_sd_card(ctx)
        try:
            return storage.sd_salt.load_sd_salt()
        except storage.sd_salt.WrongSdCard:
            if not await _wrong_card_dialog(ctx):
                raise SdProtectCancelled
        except OSError:
            # Either the SD card did not power on, or the filesystem could not be
            # mounted (card is not formatted?), or there is a staged salt file and
            # we could not commit it.
            # In either case, there is no good way to recover. If the user clicks Retry,
            # we will try again.
            if not await sd_problem_dialog(ctx):
                raise
