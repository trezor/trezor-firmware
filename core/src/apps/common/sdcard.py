import storage.sd_salt
from storage.sd_salt import SD_CARD_HOT_SWAPPABLE
from trezor import io, sdcard, ui, wire
from trezor.ui.layouts import confirm_action, show_error_and_raise


class SdCardUnavailable(wire.ProcessError):
    pass


async def _confirm_retry_wrong_card(ctx: wire.GenericContext) -> None:
    if SD_CARD_HOT_SWAPPABLE:
        await confirm_action(
            ctx,
            "warning_wrong_sd",
            "SD card protection",
            action="Wrong SD card.",
            description="Please insert the correct SD card for this device.",
            verb="Retry",
            verb_cancel="Abort",
            icon=ui.ICON_WRONG,
            larger_vspace=True,
            exc=SdCardUnavailable("Wrong SD card."),
        )
    else:
        await show_error_and_raise(
            ctx,
            "warning_wrong_sd",
            header="SD card protection",
            subheader="Wrong SD card.",
            content="Please unplug the\ndevice and insert the correct SD card.",
            exc=SdCardUnavailable("Wrong SD card."),
        )


async def _confirm_retry_insert_card(ctx: wire.GenericContext) -> None:
    if SD_CARD_HOT_SWAPPABLE:
        await confirm_action(
            ctx,
            "warning_no_sd",
            "SD card protection",
            action="SD card required.",
            description="Please insert your SD card.",
            verb="Retry",
            verb_cancel="Abort",
            icon=ui.ICON_WRONG,
            larger_vspace=True,
            exc=SdCardUnavailable("SD card required."),
        )
    else:
        await show_error_and_raise(
            ctx,
            "warning_no_sd",
            header="SD card protection",
            subheader="SD card required.",
            content="Please unplug the\ndevice and insert your SD card.",
            exc=SdCardUnavailable("SD card required."),
        )


async def _confirm_format_card(ctx: wire.GenericContext) -> None:
    # Format card? yes/no
    await confirm_action(
        ctx,
        "warning_format_sd",
        "SD card error",
        action="Unknown filesystem.",
        description="Use a different card or format the SD card to the FAT32 filesystem.",
        icon=ui.ICON_WRONG,
        icon_color=ui.RED,
        verb="Format",
        verb_cancel="Cancel",
        larger_vspace=True,
        exc=SdCardUnavailable("SD card not formatted."),
    )

    # Confirm formatting
    await confirm_action(
        ctx,
        "confirm_format_sd",
        "Format SD card",
        action="All data on the SD card will be lost.",
        description="Do you really want to format the SD card?",
        reverse=True,
        verb="Format SD card",
        icon=ui.ICON_WIPE,
        icon_color=ui.RED,
        hold=True,
        larger_vspace=True,
        exc=SdCardUnavailable("SD card not formatted."),
    )


async def confirm_retry_sd(
    ctx: wire.GenericContext,
    exc: wire.ProcessError = SdCardUnavailable("Error accessing SD card."),
) -> None:
    await confirm_action(
        ctx,
        "warning_sd_retry",
        "SD card problem",
        action=None,
        description="There was a problem accessing the SD card.",
        icon=ui.ICON_WRONG,
        icon_color=ui.RED,
        verb="Retry",
        verb_cancel="Abort",
        exc=exc,
    )


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
        await _confirm_retry_insert_card(ctx)

    if not ensure_filesystem:
        return

    while True:
        try:
            try:
                with sdcard.filesystem(mounted=False):
                    io.fatfs.mount()
            except io.fatfs.NoFilesystem:
                # card not formatted. proceed out of the except clause
                pass
            else:
                # no error when mounting
                return

            await _confirm_format_card(ctx)

            # Proceed to formatting. Failure is caught by the outside OSError handler
            with sdcard.filesystem(mounted=False):
                io.fatfs.mkfs()
                io.fatfs.mount()
                io.fatfs.setlabel("TREZOR")

            # format and mount succeeded
            return

        except OSError:
            # formatting failed, or generic I/O error (SD card power-on failed)
            await confirm_retry_sd(ctx)


async def request_sd_salt(
    ctx: wire.GenericContext = wire.DUMMY_CONTEXT,
) -> bytearray | None:
    if not storage.sd_salt.is_enabled():
        return None

    while True:
        await ensure_sdcard(ctx, ensure_filesystem=False)
        try:
            return storage.sd_salt.load_sd_salt()
        except (storage.sd_salt.WrongSdCard, io.fatfs.NoFilesystem):
            await _confirm_retry_wrong_card(ctx)
        except OSError:
            # Generic problem with loading the SD salt (hardware problem, or we could
            # not read the file, or there is a staged salt which cannot be committed).
            # In either case, there is no good way to recover. If the user clicks Retry,
            # we will try again.
            await confirm_retry_sd(ctx)
