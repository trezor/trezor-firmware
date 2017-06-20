from typing import *

# extmod/modtrezorconfig/modtrezorconfig.c
def init(self) -> None:
    '''
    Initializes the storage. Must be called before any other method is called from this module!
    '''

# extmod/modtrezorconfig/modtrezorconfig.c
def get(app: int, key: int) -> bytes:
    '''
    Gets a value of given key for given app (or empty bytes if not set).
    '''

# extmod/modtrezorconfig/modtrezorconfig.c
def set(app: int, key: int, value: bytes) -> None:
    '''
    Sets a value of given key for given app.
    '''

# extmod/modtrezorconfig/modtrezorconfig.c
def wipe(self) -> None:
    '''
    Erases the whole config. Use with caution!
    '''
