from typing import *
from buffer_types import *


# rust/src/micropython/miniscript.rs
def compile(descriptor: str, change: bool, index: int) -> bytes:
    """Parse a Bitcoin multipath ranged output descriptor
       and return the witness script bytes."""
