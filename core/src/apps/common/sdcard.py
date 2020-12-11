import storage.sd_salt
from storage.sd_salt import SD_CARD_HOT_SWAPPABLE
from trezor import fatfs, sdcard, ui, wire
from trezor.ui.components.tt.text import Text

from apps.common.confirm import confirm, hold_to_confirm

if False:
    from typing import Optional


class SdCardUnavailable(wire.ProcessError):
    pass


async def _wrong_card_dialog(ctx: wire.GenericContext) -> bool:
    text = Text("SD card protection", ui.ICON_WRONG)
    text.bold("Wrong SD card.")
    text.br_half()
    if SD_CARD_HOT_SWAPPABLE:
        text.normal("Please insert the", "correct SD card for", "this device.")
        btn_confirm: Optional[str] = "Retry"
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
        btn_confirm: Optional[str] = "Retry"
        btn_cancel = "Abort"
    else:
        text.normal("Please unplug the", "device and insert your", "SD card.")
        btn_confirm = None
        btn_cancel = "Close"

    return await confirm(ctx, text, confirm=btn_confirm, cancel=btn_cancel)


async def format_card_dialog(ctx: wire.GenericContext) -> bool:
    # Format card? yes/no
    text = Text("SD card error", ui.ICON_WRONG, ui.RED)
    text.bold("Unknown filesystem.")
    text.br_half()
    text.normal("Use a different card or")
    text.normal("format the SD card to")
    text.normal("the FAT32 filesystem.")
    if not await confirm(ctx, text, confirm="Format", cancel="Cancel"):
        return False

    # Confirm formatting
    text = Text("Format SD card", ui.ICON_WIPE, ui.RED)
    text.normal("Do you really want to", "format the SD card?")
    text.br_half()
    text.bold("All data on the SD card", "will be lost.")
    return await hold_to_confirm(ctx, text, confirm="Format SD card")


async def sd_problem_dialog(ctx: wire.GenericContext) -> bool:
    text = Text("SD card problem", ui.ICON_WRONG, ui.RED)
    text.normal("There was a problem", "accessing the SD card.")
    return await confirm(ctx, text, confirm="Retry", cancel="Abort")


async def ensure_sdcard(
    ctx: wire.GenericContext, ensure_filesystem: bool = True
) -> None:
    """Ensure a SD card is ready for use.

    This function runs the UI flow needed to ask the user to insert a SD card if there
    isn't one.

    If `ensure_filesystem` is True (the default), it also tries to mount the SD card
    filesystem, and allows the user to format the card if a filesystem cannot be
    mounted.
    """
    while not sdcard.is_present():
        if not await insert_card_dialog(ctx):
            raise SdCardUnavailable("SD card required.")

    if not ensure_filesystem:
        return

    while True:
        try:
            try:
                with sdcard.filesystem(mounted=False):
                    fatfs.mount()
            except fatfs.NoFilesystem:
                # card not formatted. proceed out of the except clause
                pass
            else:
                # no error when mounting
                return

            if not await format_card_dialog(ctx):
                raise SdCardUnavailable("SD card not formatted.")

            # Proceed to formatting. Failure is caught by the outside OSError handler
            with sdcard.filesystem(mounted=False):
                fatfs.mkfs()
                fatfs.mount()
                fatfs.setlabel("TREZOR")

            # format and mount succeeded
            return

        except OSError:
            # formatting failed, or generic I/O error (SD card power-on failed)
            if not await sd_problem_dialog(ctx):
                raise SdCardUnavailable("Error accessing SD card.")


async def request_sd_salt(
    ctx: wire.GenericContext = wire.DUMMY_CONTEXT,
) -> Optional[bytearray]:
    if not storage.sd_salt.is_enabled():
        return None

    while True:
        await ensure_sdcard(ctx, ensure_filesystem=False)
        try:
            return storage.sd_salt.load_sd_salt()
        except (storage.sd_salt.WrongSdCard, fatfs.NoFilesystem):
            if not await _wrong_card_dialog(ctx):
                raise SdCardUnavailable("Wrong SD card.")
        except OSError:
            # Generic problem with loading the SD salt (hardware problem, or we could
            # not read the file, or there is a staged salt which cannot be committed).
            # In either case, there is no good way to recover. If the user clicks Retry,
            # we will try again.
            if not await sd_problem_dialog(ctx):
                raise SdCardUnavailable("Error accessing SD card.")
