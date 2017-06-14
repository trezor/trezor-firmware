from typing import *

# extmod/modtrezorconfig/modtrezorconfig.c
class Config:
    '''
    Persistent key-value storage, with 16-bit keys and bytes values.
    '''

    def __init__(self):
        '''
        Initializes the storage.
        '''

    def get(self, app: int, key: int) -> bytes:
        '''
        Gets a value of given key for given app (or empty bytes if not set).
        '''

    def set(self, app: int, key: int, value: bytes) -> None:
        '''
        Sets a value of given key for given app.
        Returns True on success.
        '''

    def wipe(self) -> None:
        '''
        Erases the whole config. Use with caution!
        '''
