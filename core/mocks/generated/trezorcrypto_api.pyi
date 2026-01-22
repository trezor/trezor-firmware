from typing import *
from buffer_types import *


# rust/src/crypto/api/firmware_micropython.rs
def process_crypto_message(
    *,
    data: bytes,
) -> bytes:
    """Process an IPC message by deserializing it and dispatching to the appropriate crypto function.
        The response is serialized and returned as bytes.
    """


# rust/src/crypto/api/firmware_micropython.rs
def deserialize_derivation_path(
    *,
    data: bytes,
) -> list[int]:
    """Deserialize a derivation path from bytes and return it as a list of integers.
    """


# rust/src/crypto/api/firmware_micropython.rs
def serialize_crypto_result(
    *,
    result: Obj,
) -> bytes:
    """Serialize a crypto result into a compact binary format."""
