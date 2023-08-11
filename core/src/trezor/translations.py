from trezor import config

DEFAULT_LANGUAGE = "en-US"


def get_language() -> str:
    from trezortranslate import language_name

    translation_lang = language_name()
    if translation_lang:
        return translation_lang
    return DEFAULT_LANGUAGE


def write(data: bytes | bytearray, offset: int) -> None:
    from trezor import wire

    if offset + len(data) > data_max_size():
        raise wire.DataError("Language data too long")

    config.translations_set(data, offset)


def wipe() -> None:
    config.translations_wipe()


def data_max_size() -> int:
    return config.translations_max_bytesize()
