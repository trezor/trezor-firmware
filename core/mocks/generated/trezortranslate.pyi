from typing import *
from trezortranslate_keys import TR as TR  # noqa: F401
"""Translation object with attributes."""


# rust/src/translations/obj.rs
def area_bytesize() -> int:
    """Maximum size of the translation blob that can be stored."""


# rust/src/translations/obj.rs
def get_language() -> str:
    """Get the current language."""


# rust/src/translations/obj.rs
def init() -> None:
    """Initialize the translations system.
    Loads and verifies translation data from flash. If the verification passes,
    Trezor UI is translated from that point forward.
    """


# rust/src/translations/obj.rs
def deinit() -> None:
    """Deinitialize the translations system.
    Translations must be deinitialized before erasing or writing to flash.
    """


# rust/src/translations/obj.rs
def erase() -> None:
    """Erase the translations blob from flash."""


# rust/src/translations/obj.rs
def write(data: bytes, offset: int) -> None:
    """Write data to the translations blob in flash."""


# rust/src/translations/obj.rs
def verify(data: bytes) -> None:
    """Verify the translations blob."""


# rust/src/translations/obj.rs
class TranslationsHeader:
    """Metadata about the translations blob."""
    language: str
    version: tuple[int, int, int, int]
    data_len: int
    data_hash: bytes
    total_len: int
    def __init__(self, header_bytes: bytes) -> None:
        """Parse header from bytes.
        The header has variable length.
        """
    @staticmethod
    def load_from_flash() -> TranslationsHeader | None:
        """Load translations from flash."""
