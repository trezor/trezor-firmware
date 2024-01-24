from typing import *


# rust/src/translations/micropython.rs
class TranslationsHeader:
    """Metadata about the translations blob."""

    language_name: str
    version: tuple[int, int, int, int]
    change_language_title: str
    change_language_prompt: str
    header_length: int
    data_length: int

    def __init__(self, header_bytes: bytes) -> None:
        """Parse header from bytes.
        The header has variable length.
        """
    @staticmethod
    def load_from_flash() -> TranslationsHeader | None:
        """Load translations from flash."""
from trezortranslate_keys import TR  # noqa: F401
"""Translation object with attributes."""
