from typing import *
from buffer_types import *


# rust/src/crypto/api/firmware_micropython.rs
def process_crypto_message(
    *,
    data: bytes,
    ipc_cb: Callable[[bytes], None],
) -> bytes:
    """Process an IPC message by deserializing it and dispatching to the appropriate crypto function.
        The response is serialized and sent via the ipc_cb callback.
    """


# rust/src/crypto/api/firmware_micropython.rs
def send_crypto_result(
    *,
    result: CryptoResult,
    ipc_cb: Callable[[bytes], None],
) -> bytes:
    """Serialize a crypto result (e.g. CryptoResult) into bytes and send it back via the ipc_cb callback."""


# rust/src/crypto/api/firmware_micropython.rs
def deserialize_derivation_path(
    *,
    data: bytes,
) -> List[int]:
    """Deserialize a derivation path from bytes and return it as a list of integers."""


# rust/src/crypto/api/firmware_micropython.rs
def deserialize_crypto_message(
    *,
    data: bytes,
) -> Obj:
    """Deserialize a crypto message from bytes and return it as a MicroPython object."""
