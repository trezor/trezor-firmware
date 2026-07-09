from trezor import TR, io, wire
from trezor.ui.layouts import confirm_action, show_error_and_raise
from trezor.utils import sd_hotswap_enabled


class SdCardUnavailable(wire.ProcessError):
    pass


async def _confirm_retry_wrong_card() -> None:
    if sd_hotswap_enabled():
        await confirm_action(
            "warning_wrong_sd",
            TR.sd_card__title,
            TR.sd_card__wrong_sd_card,
            TR.sd_card__insert_correct_card,
            verb=TR.buttons__retry,
            verb_cancel=TR.buttons__abort,
            exc=SdCardUnavailable("Wrong SD card."),
        )
    else:
        await show_error_and_raise(
            "warning_wrong_sd",
            TR.sd_card__unplug_and_insert_correct,
            TR.sd_card__wrong_sd_card,
            exc=SdCardUnavailable("Wrong SD card."),
        )


async def _confirm_retry_insert_card() -> None:
    if sd_hotswap_enabled():
        await confirm_action(
            "warning_no_sd",
            TR.sd_card__title,
            TR.sd_card__card_required,
            TR.sd_card__please_insert,
            verb=TR.buttons__retry,
            verb_cancel=TR.buttons__abort,
            exc=SdCardUnavailable("SD card required."),
        )
    else:
        await show_error_and_raise(
            "warning_no_sd",
            TR.sd_card__please_unplug_and_insert,
            TR.sd_card__card_required,
            exc=SdCardUnavailable("SD card required."),
        )


async def _confirm_format_card() -> None:
    # Format card? yes/no
    await confirm_action(
        "warning_format_sd",
        TR.sd_card__error,
        TR.sd_card__unknown_filesystem,
        TR.sd_card__use_different_card,
        verb=TR.buttons__format,
        verb_cancel=TR.buttons__cancel,
        exc=SdCardUnavailable("SD card not formatted."),
    )

    # Confirm formatting
    await confirm_action(
        "confirm_format_sd",
        TR.sd_card__format_card,
        TR.sd_card__all_data_will_be_lost,
        TR.sd_card__wanna_format,
        reverse=True,
        verb=TR.sd_card__format_card,
        hold=True,
        exc=SdCardUnavailable("SD card not formatted."),
    )


async def confirm_retry_sd(
    exc: wire.ProcessError = SdCardUnavailable("Error accessing SD card."),
) -> None:
    await confirm_action(
        "warning_sd_retry",
        TR.sd_card__title_problem,
        None,
        TR.sd_card__problem_accessing,
        verb=TR.buttons__retry,
        verb_cancel=TR.buttons__abort,
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
    from trezor.ui.layouts.progress import progress

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
                progress_obj = progress()
                progress_obj.start()
                fatfs.mkfs(progress_obj.report)
                fatfs.mount()
                fatfs.setlabel("TREZOR")
                progress_obj.stop()

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
