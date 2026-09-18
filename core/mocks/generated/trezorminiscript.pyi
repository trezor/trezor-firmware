from typing import *
from buffer_types import *


# rust/src/micropython/miniscript.rs
def compile(descriptor: str, internal: bool, index: int) -> bytes:
    """Compile a Miniscript multipath descriptor into an explicit script."""
