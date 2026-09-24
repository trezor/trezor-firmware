from typing import *
from buffer_types import *


# rust/src/micropython/miniscript.rs
def compile(descriptor: str, internal: bool, index: int) -> None:
    """Parse a Miniscript descriptor."""
