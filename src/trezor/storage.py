from TrezorStorage import Storage

_storage = Storage()

def get(key, defval=None):
    return _storage.get(key, defval)


def set(key, value):
    return _storage.set(key, value)
