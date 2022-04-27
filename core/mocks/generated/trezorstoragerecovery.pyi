from typing import *


# rust/src/storagedevice/recovery.rs
def is_in_progress() -> bool:
    """Whether recovery is in progress."""


# rust/src/storagedevice/recovery.rs
def set_in_progress(val: bool) -> None:
    """Set in progress."""


# rust/src/storagedevice/recovery.rs
def is_dry_run() -> bool:
    """Whether recovery is dry - just a test."""


# rust/src/storagedevice/recovery.rs
def set_dry_run(val: bool) -> None:
    """Set the dry run."""


# rust/src/storagedevice/recovery.rs
def get_slip39_identifier() -> int | None:
    """Get slip39 identifier."""


# rust/src/storagedevice/recovery.rs
def set_slip39_identifier(identifier: int) -> None:
    """Set slip39 identifier."""


# rust/src/storagedevice/recovery.rs
def get_slip39_iteration_exponent() -> int | None:
    """Get slip39 iteration exponent."""


# rust/src/storagedevice/recovery.rs
def set_slip39_iteration_exponent(exponent: int) -> None:
    """Set slip39 iteration exponent."""


# rust/src/storagedevice/recovery.rs
def get_slip39_group_count() -> int:
    """Get slip39 group count."""


# rust/src/storagedevice/recovery.rs
def set_slip39_group_count(group_count: int) -> None:
    """Set slip39 group count."""


# rust/src/storagedevice/recovery.rs
def get_slip39_remaining_shares(group_index: int) -> int | None:
    """Get slip39 remaining shares."""


# rust/src/storagedevice/recovery.rs
def fetch_slip39_remaining_shares() -> list[int] | None:
    """Fetch slip39 remaining shares."""


# rust/src/storagedevice/recovery.rs
def set_slip39_remaining_shares(shares_remaining: int, group_index: int) -> None:
    """Set slip39 remaining shares."""


# rust/src/storagedevice/recovery.rs
def end_progress() -> None:
    """Finish recovery."""
