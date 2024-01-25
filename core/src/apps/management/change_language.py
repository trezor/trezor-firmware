from micropython import const
from typing import TYPE_CHECKING

from trezor.wire import DataError

if TYPE_CHECKING:
    from trezor.messages import ChangeLanguage, Success

_CHUNK_SIZE = const(1024)


async def change_language(msg: ChangeLanguage) -> Success:
    from trezor import translations, utils
    from trezor.messages import Success
    from trezor.ui.layouts.progress import progress

    data_length = msg.data_length  # local_cache_attribute

    # When empty data, reverting the language to default (english)
    if data_length == 0:
        await _require_confirm_change_language(
            "Change language", "Do you want to change language to English?"
        )
        translations.deinit()
        translations.erase()
        # translations.init() would be a no-op here
        return Success(message="Language reverted to default")

    if data_length > translations.area_bytesize():
        raise DataError("Translations too long")
    if data_length < translations.MAX_HEADER_LEN:
        raise DataError("Translations too short")

    # Getting and parsing the header
    header_data = await get_data_chunk(msg.data_length, 0)
    try:
        header = translations.TranslationsHeader(header_data)
    except ValueError as e:
        if e.args:
            raise DataError("Invalid header: " + e.args[0]) from None
        else:
            raise DataError("Invalid header") from None

    # Verifying header information
    if header.total_len != data_length:
        raise DataError("Invalid header data length")

    # TODO: how to handle the version updates - numbers have to be bumped in cs.json and others
    # (or have this logic in a separate blob-creating tool)
    # (have some static check in make gen_check?)
    if header.version != (
        utils.VERSION_MAJOR,
        utils.VERSION_MINOR,
        utils.VERSION_PATCH,
        0,
    ):
        raise DataError("Invalid translations version")

    # Confirm with user
    await _require_confirm_change_language(
        header.change_language_title, header.change_language_prompt
    )

    # Initiate loader
    loader = progress(None, None)
    loader.report(0)

    # Loading all the data at once, so we can verify its fingerprint
    # If we saved it gradually to the storage and only checked the fingerprint at the end
    # (with the idea of deleting the data if the fingerprint does not match),
    # attackers could still write some data into storage and then unplug the device.
    blob = utils.empty_bytearray(translations.area_bytesize())

    # Write the header
    blob.extend(header_data)

    # Requesting the data in chunks and storing them in the blob
    # Also checking the hash of the data for consistency
    data_to_fetch = data_length - len(header_data)
    data_left = data_to_fetch
    offset = len(header_data)
    while data_left > 0:
        data_chunk = await get_data_chunk(data_left, offset)
        loader.report(len(blob) * 1000 // data_length)
        blob.extend(data_chunk)
        data_left -= len(data_chunk)
        offset += len(data_chunk)

    # When the data do not match the hash, do not write anything
    try:
        translations.verify(blob)
    except Exception:
        raise DataError("Translation data verification failed.")

    translations.deinit()
    translations.erase()
    translations.write(blob, 0)
    translations.init()
    loader.report(1000)

    return Success(message="Language changed")


async def get_data_chunk(data_left: int, offset: int) -> bytes:
    from trezor.messages import TranslationDataAck, TranslationDataRequest
    from trezor.wire.context import call

    data_length = min(data_left, _CHUNK_SIZE)
    req = TranslationDataRequest(data_length=data_length, data_offset=offset)
    res = await call(req, TranslationDataAck)
    return res.data_chunk


async def _require_confirm_change_language(title: str, description: str) -> None:
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        "set_language",
        title,
        description=description,
        verb="OK",  # going for an international word, so it does not need translations
        br_code=ButtonRequestType.ProtectCall,
    )
