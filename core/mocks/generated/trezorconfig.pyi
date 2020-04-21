from typing import *


# extmod/modtrezorconfig/modtrezorconfig.c
def init(
   ui_wait_callback: Callable[[int, int, str], bool] = None
) -> None:
    """
    Initializes the storage.  Must be called before any other method is
    called from this module!
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def unlock(pin: int, ext_salt: Optional[bytes]) -> bool:
    """
    Attempts to unlock the storage with the given PIN and external salt.
    Returns True on success, False on failure.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def check_pin(pin: int, ext_salt: Optional[bytes]) -> bool:
    """
    Check the given PIN with the given external salt.
    Returns True on success, False on failure.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def lock() -> None:
    """
    Locks the storage.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def is_unlocked() -> bool:
    """
    Returns True if storage is unlocked, False otherwise.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def has_pin() -> bool:
    """
    Returns True if storage has a configured PIN, False otherwise.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def get_pin_rem() -> int:
    """
    Returns the number of remaining PIN entry attempts.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def change_pin(
    oldpin: int,
    newpin: int,
    old_ext_salt: Optional[bytes],
    new_ext_salt: Optional[bytes],
) -> bool:
    """
    Change PIN and external salt. Returns True on success, False on failure.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def ensure_not_wipe_code(pin: int) -> None:
    """
    Wipes the device if the entered PIN is the wipe code.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def has_wipe_code() -> bool:
    """
    Returns True if storage has a configured wipe code, False otherwise.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def change_wipe_code(
    pin: int,
    ext_salt: Optional[bytes],
    wipe_code: int,
) -> bool:
    """
    Change wipe code. Returns True on success, False on failure.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def get(app: int, key: int, public: bool = False) -> Optional[bytes]:
    """
    Gets the value of the given key for the given app (or None if not set).
    Raises a RuntimeError if decryption or authentication of the stored
    value fails.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def set(app: int, key: int, value: bytes, public: bool = False) -> None:
    """
    Sets a value of given key for given app.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def delete(app: int, key: int, public: bool = False) -> bool:
    """
    Deletes the given key of the given app.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def set_counter(
    app: int, key: int, count: int, writable_locked: bool = False
) -> bool:
    """
    Sets the given key of the given app as a counter with the given value.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def next_counter(
   app: int, key: int, writable_locked: bool = False,
) -> Optional[int]:
    """
    Increments the counter stored under the given key of the given app and
    returns the new value.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def wipe() -> None:
    """
    Erases the whole config. Use with caution!
    """
