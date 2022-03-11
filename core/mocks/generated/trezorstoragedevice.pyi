from typing import *


# rust/src/storagedevice/storagedevice.rs
def is_version_stored() -> bool:
    """Whether version is in storage."""


# rust/src/storagedevice/storagedevice.rs
def is_initialized() -> bool:
    """Whether device is initialized."""


# rust/src/storagedevice/storagedevice.rs
def get_version() -> bytes:
    """Get from storage."""


# rust/src/storagedevice/storagedevice.rs
def set_version(version: bytes) -> bool:
    """Save to storage."""
