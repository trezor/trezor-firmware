from typing import *
from buffer_types import *


# rust/src/crypto_api.rs
def send_crypto_result(
    *,
    result: str | bytes | bool,
    ipc_cb: Callable[[bytes], None],
) -> None:
    """Serialize a crypto result into bytes and send it back via the ipc_cb callback.
    A failed operation is sent as `False`.
    """


# rust/src/crypto_api.rs
def deserialize_crypto_message(
    *,
    data: bytes,
) -> Obj:
    """Deserialize a crypto message from bytes and return it as a MicroPython object."""
