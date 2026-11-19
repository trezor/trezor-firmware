from typing import *
from buffer_types import *


# rust/src/crypto_api.rs
def serialize_crypto_result(
    *,
    result: str | bytes | bool,
) -> bytes:
    """Serialize a crypto result into bytes to send to the app."""


# rust/src/crypto_api.rs
def deserialize_crypto_message(
    *,
    data: bytes,
) -> Obj:
    """Deserialize a crypto message from bytes and return it as a MicroPython object."""
