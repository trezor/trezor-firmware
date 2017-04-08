
# extmod/modtrezorconfig/modtrezorconfig.c
def get(app: int, key: int) -> bytes:
    '''
    Gets a value of given key for given app (or empty bytes if not set).
    '''

# extmod/modtrezorconfig/modtrezorconfig.c
def set(app: int, key: int, value: bytes) -> None:
    '''
    Sets a value of given key for given app.
    Returns True on success.
    '''

# extmod/modtrezorconfig/modtrezorconfig.c
def wipe() -> None:
    '''
    Erases the whole config (use with caution!)
    '''
