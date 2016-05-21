from TrezorStorage import Storage

_storage = Storage()


def get(name):
    return _storage.get(name)


def set(name, value):
    return _storage.set(name, value)
