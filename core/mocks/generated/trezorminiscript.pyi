from typing import *
from buffer_types import *


# rust/src/miniscript_bridge.rs
def compile(descriptor: str) -> bytes:
    """Parse a Bitcoin output descriptor (with concrete public keys)
    and return the witness script bytes."""
