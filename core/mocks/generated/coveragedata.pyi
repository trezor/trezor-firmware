from typing import *
from buffer_types import *


# rust/src/coverage/mod.rs
def add(file: str, line: int) -> None:
    """
    Mark file line as covered.
    """


# rust/src/coverage/mod.rs
def get() -> list[tuple[str, int]]:
    """
    Return a list of all covered file lines.
    """
