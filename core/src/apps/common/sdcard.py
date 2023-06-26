from storage.sd_salt import SD_CARD_HOT_SWAPPABLE
from trezor import io, wire
from trezor.ui.layouts import confirm_action, show_error_and_raise


class SdCardUnavailable(wire.ProcessError):
    pass


async def _confirm_retry_wrong_card() -> None:
    if SD_CARD_HOT_SWAPPABLE:
        await confirm_action(
            "warning_wrong_sd",
            "SD card protection",
            "Wrong SD card.",
            "Please insert the correct SD card for this device.",
            verb="Retry",
            verb_cancel="Abort",
            exc=SdCardUnavailable("Wrong SD card."),
        )
    else:
        await show_error_and_raise(
            "warning_wrong_sd",
            "Please unplug the device and insert the correct SD card.",
            "Wrong SD card.",
            exc=SdCardUnavailable("Wrong SD card."),
        )


async def _confirm_retry_insert_card() -> None:
    if SD_CARD_HOT_SWAPPABLE:
        await confirm_action(
            "warning_no_sd",
            "SD card protection",
            "SD card required.",
            "Please insert your SD card.",
            verb="Retry",
            verb_cancel="Abort",
            exc=SdCardUnavailable("SD card required."),
        )
    else:
        await show_error_and_raise(
            "warning_no_sd",
            "Please unplug the device and insert your SD card.",
            "SD card required.",
            exc=SdCardUnavailable("SD card required."),
        )


async def _confirm_format_card() -> None:
    # Format card? yes/no
    await confirm_action(
        "warning_format_sd",
        "SD card error",
        "Unknown filesystem.",
        "Use a different card or format the SD card to the FAT32 filesystem.",
        verb="Format",
        verb_cancel="Cancel",
        exc=SdCardUnavailable("SD card not formatted."),
    )

    # Confirm formatting
    await confirm_action(
        "confirm_format_sd",
        "Format SD card",
        "All data on the SD card will be lost.",
        "Do you really want to format the SD card?",
        reverse=True,
        verb="Format SD card",
        hold=True,
        exc=SdCardUnavailable("SD card not formatted."),
    )


async def confirm_retry_sd(
    exc: wire.ProcessError = SdCardUnavailable("Error accessing SD card."),
) -> None:
    await confirm_action(
        "warning_sd_retry",
        "SD card problem",
        None,
        "There was a problem accessing the SD card.",
        verb="Retry",
        verb_cancel="Abort",
        exc=exc,
    )


async def ensure_sdcard(ensure_filesystem: bool = True) -> None:
    """Ensure a SD card is ready for use.

    This function runs the UI flow needed to ask the user to insert a SD card if there
    isn't one.

    If `ensure_filesystem` is True (the default), it also tries to mount the SD card
    filesystem, and allows the user to format the card if a filesystem cannot be
    mounted.
    """
    from trezor import sdcard

    while not sdcard.is_present():
        await _confirm_retry_insert_card()

    if not ensure_filesystem:
        return
    fatfs = io.fatfs  # local_cache_attribute
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

            await _confirm_format_card()

            # Proceed to formatting. Failure is caught by the outside OSError handler
            with sdcard.filesystem(mounted=False):
                fatfs.mkfs()
                fatfs.mount()
                fatfs.setlabel("TREZOR")

            # format and mount succeeded
            return

        except OSError:
            # formatting failed, or generic I/O error (SD card power-on failed)
            await confirm_retry_sd()


async def request_sd_salt() -> bytearray | None:
    import storage.sd_salt as storage_sd_salt

    if not storage_sd_salt.is_enabled():
        return None

    while True:
        await ensure_sdcard(ensure_filesystem=False)
        try:
            return storage_sd_salt.load_sd_salt()
        except (storage_sd_salt.WrongSdCard, io.fatfs.NoFilesystem):
            await _confirm_retry_wrong_card()
        except OSError:
            # Generic problem with loading the SD salt (hardware problem, or we could
            # not read the file, or there is a staged salt which cannot be committed).
            # In either case, there is no good way to recover. If the user clicks Retry,
            # we will try again.
            await confirm_retry_sd()
