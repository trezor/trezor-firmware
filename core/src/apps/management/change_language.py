from typing import TYPE_CHECKING

from trezor import TR, translations
from trezor.wire import DataError, high_speed

if TYPE_CHECKING:
    from typing import Callable

    from trezor.messages import ChangeLanguage, Success
    from trezor.ui import ProgressLayout


async def change_language(msg: ChangeLanguage) -> Success:
    from trezor import utils, workflow
    from trezor.messages import Success
    from trezor.ui.layouts.progress import progress

    workflow.close_others()
    loader: ProgressLayout | None = None

    def report(value: int) -> None:
        nonlocal loader
        if loader is None:
            loader = progress(TR.language__progress)
        loader.report(value)

    if msg.data_length == 0:
        await do_unset_language(msg.show_display, report)
    else:
        await do_change_language(
            msg.data_length, msg.show_display, utils.VERSION, report
        )

    return Success(message="Language changed")


async def do_unset_language(
    show_display: bool | None, report: Callable[[int], None]
) -> None:
    current_header = translations.TranslationsHeader.load_from_flash()
    silent_install = current_header is None
    await _require_confirm_change_language(None, silent_install, show_display)

    if current_header is not None:
        report(0)
        translations.deinit()
        translations.erase()
        # translations.init() would be a no-op here
        report(1000)

    await _show_success(silent_install, show_display)


async def do_change_language(
    data_length: int,
    show_display: bool | None,
    expected_version: tuple[int, int, int, int],
    report: Callable[[int], None],
) -> None:
    import storage.device
    from trezor import utils

    from apps.common import chunked

    if data_length > translations.area_bytesize():
        raise DataError("Translations too long")

    # Getting and parsing the header
    header_data = await chunked.get_data_chunk(data_length, 0)
    try:
        header = translations.TranslationsHeader(header_data)
    except (ValueError, EOFError):
        raise DataError("Invalid translations data")

    # Verifying header information
    if header.total_len != data_length:
        raise DataError("Invalid data length")

    # Translation blob format may not change when VERSION_BUILD is bumped.
    # Compare only (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH):
    if len(header.version) != 4 or len(expected_version) != 4:
        raise DataError("Invalid version format")
    if header.version[:3] != expected_version[:3]:
        raise DataError("Translations version mismatch")

    current_header = translations.TranslationsHeader.load_from_flash()
    if current_header is None:
        # if no blob is present, but the device is set up, we consider the language
        # being ""explicitly set"" to English
        silent_install = not storage.device.is_initialized()
    else:
        # if a blob is present, it can only be silently upgraded to expected_version
        silent_install = (
            current_header.language == header.language
            and current_header.version != expected_version
        )

    # Confirm with user
    await _require_confirm_change_language(header, silent_install, show_display)

    # Initiate loader
    report(0)

    # Loading all the data at once, so we can verify its fingerprint
    # If we saved it gradually to the storage and only checked the fingerprint at the end
    # (with the idea of deleting the data if the fingerprint does not match),
    # attackers could still write some data into storage and then unplug the device.
    # Note: it may raise MemoryError in case the heap is fragmented.
    blob = utils.empty_bytearray(translations.area_bytesize())

    # Write the header
    blob.extend(header_data)

    # Requesting the data in chunks and storing them in the blob
    data_to_fetch = data_length - len(header_data)

    with high_speed:
        await chunked.get_all_chunks(
            blob, data_to_fetch, offset=len(header_data), report=report
        )

    # When the data do not match the hash, do not write anything
    try:
        translations.verify(blob)
    except Exception:
        raise DataError("Translation data verification failed.")

    translations.deinit()
    translations.erase()
    translations.write(blob, 0)
    translations.init()
    report(1000)
    await _show_success(silent_install, show_display)


async def _require_confirm_change_language(
    header: translations.TranslationsHeader | None,
    silent_install: bool,
    show_display: bool | None,
) -> None:
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_action

    lang = "en-US" if header is None else header.language

    if not silent_install and show_display is False:
        # host requested silent change but we cannot do it
        raise DataError("Cannot change language without user prompt.")

    if silent_install and show_display is not True:
        # change can be silent and host didn't explicitly request confirmation
        return

    # showing confirmation in case (a) host explicitly requests it,
    # or (b) installation is not silent
    await confirm_action(
        "set_language",
        TR.language__title,
        description=TR.language__change_to_template.format(lang),
        verb="OK",  # going for an international word, so it does not need translations
        br_code=ButtonRequestType.ProtectCall,
        prompt_screen=True,
    )


async def _show_success(silent_install: bool, show_display: bool | None) -> None:
    from trezor.ui.layouts import show_success

    if silent_install and show_display is not True:
        return

    await show_success("change_language", TR.language__changed)
