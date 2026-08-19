from typing import *
from buffer_types import *


# rust/src/definitions/obj.rs
def verify(digest: AnyBytes, sig: AnyBytes, sigmask: int, version: int) -> None:
    """Verify the definitions signature."""
