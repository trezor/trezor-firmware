from typing import *


# rust/src/storagedevice/storagedevice.rs
def is_version_stored() -> bool:
    """Whether version is in storage."""


# rust/src/storagedevice/storagedevice.rs
def is_initialized() -> bool:
    """Whether device is initialized."""


# rust/src/storagedevice/storagedevice.rs
def get_version() -> bytes:
    """Get version."""


# rust/src/storagedevice/storagedevice.rs
def set_version(value: bytes) -> bool:
    """Set version."""


# rust/src/storagedevice/storagedevice.rs
def get_rotation() -> int:
    """Get rotation."""


# rust/src/storagedevice/storagedevice.rs
def set_rotation(value: int) -> bool:
    """Set rotation."""


# rust/src/storagedevice/storagedevice.rs
def get_label() -> str:
    """Get label."""


# rust/src/storagedevice/storagedevice.rs
def set_label(value: str) -> bool:
    """Set label."""


# rust/src/storagedevice/storagedevice.rs
def get_mnemonic_secret() -> bytes:
    """Get mnemonic secret."""
