from typing import *
from buffer_types import *


# rust/src/micropython/miniscript.rs
def collect_keys(descriptor: str) -> list[tuple[int, int, int]]:
    """Collect all key expressions from a Miniscript descriptor."""


# rust/src/micropython/miniscript.rs
def compile(descriptor: str, derive_fn: Callable[[int, int, int], bytes]) -> bytes:
    """Compile a Miniscript multipath descriptor into an explicit script."""
