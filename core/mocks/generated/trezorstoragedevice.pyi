from typing import *


# extmod/rustmods/modtrezorstoragedevice.c
def is_version_stored() -> bool:
    """Whether version is in storage."""


# extmod/rustmods/modtrezorstoragedevice.c
def get_version() -> bytes:
    """Get from storage."""


# extmod/rustmods/modtrezorstoragedevice.c
def set_version(version: bytes) -> bool:
    """Save to storage."""
