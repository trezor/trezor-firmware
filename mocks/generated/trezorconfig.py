from typing import *

# extmod/modtrezorconfig/modtrezorconfig.c
def init() -> None:
    '''
    Initializes the storage.  Must be called before any other method is
    called from this module!
    '''

# extmod/modtrezorconfig/modtrezorconfig.c
def check_pin(pin: int, waitcallback: (int, int -> None)) -> bool:
    '''
    Check the given PIN. Returns True on success, False on failure.
    '''

# extmod/modtrezorconfig/modtrezorconfig.c
def unlock(pin: int, waitcallback: (int, int -> None)) -> bool:
    '''
    Attempts to unlock the storage with given PIN.  Returns True on
    success, False on failure.
    '''

# extmod/modtrezorconfig/modtrezorconfig.c
def has_pin() -> bool:
    '''
    Returns True if storage has a configured PIN, False otherwise.
    '''

# extmod/modtrezorconfig/modtrezorconfig.c
def change_pin(pin: int, newpin: int, waitcallback: (int, int -> None)) -> bool:
    '''
    Change PIN. Returns True on success, False on failure.
    '''

# extmod/modtrezorconfig/modtrezorconfig.c
def get(app: int, key: int, public: bool=False) -> bytes:
    '''
    Gets a value of given key for given app (or empty bytes if not set).
    '''

# extmod/modtrezorconfig/modtrezorconfig.c
def set(app: int, key: int, value: bytes, public: bool=False) -> None:
    '''
    Sets a value of given key for given app.
    '''

# extmod/modtrezorconfig/modtrezorconfig.c
def wipe() -> None:
    '''
    Erases the whole config. Use with caution!
    '''
