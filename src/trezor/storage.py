from TrezorStorage import Storage

_storage = Storage()


def get(name, defval=None):
    return _storage.get(name, defval)


def set(name, value):
    return _storage.set(name, value)
