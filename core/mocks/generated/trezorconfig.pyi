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
def unlock(pin: int) -> bool:
    """
    Attempts to unlock the storage with given PIN.  Returns True on
    success, False on failure.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def check_pin(pin: int) -> bool:
    """
    Check the given PIN. Returns True on success, False on failure.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def lock() -> None:
    """
    Locks the storage.
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
def change_pin(pin: int, newpin: int) -> bool:
    """
    Change PIN. Returns True on success, False on failure.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def get(app: int, key: int, public: bool = False) -> bytes:
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
def next_counter(app: int, key: int, writable_locked: bool = False) -> bool:
    """
    Increments the counter stored under the given key of the given app and
    returns the new value.
    """


# extmod/modtrezorconfig/modtrezorconfig.c
def wipe() -> None:
    """
    Erases the whole config. Use with caution!
    """
