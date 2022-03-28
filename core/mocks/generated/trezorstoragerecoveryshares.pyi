from typing import *


# rust/src/storagedevice/recovery_shares.rs
def get(index: int, group_index: int) -> str | None:
    """Get recovery share."""


# rust/src/storagedevice/recovery_shares.rs
def set(index: int, group_index: int, mnemonic: str) -> None:
    """Set recovery share."""


# rust/src/storagedevice/recovery_shares.rs
def fetch_group(group_index: int) -> list[str]:
    """Fetch recovery share group."""


# rust/src/storagedevice/recovery_shares.rs
def delete() -> None:
    """Delete all recovery shares."""
