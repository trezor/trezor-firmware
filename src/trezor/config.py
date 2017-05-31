from TrezorConfig import Config

_config = Config()


def get(app: int, key: int) -> bytes:
    return _config.get(app, key)


def set(app: int, key: int, value: bytes):
    return _config.set(app, key, value)


def wipe():
    return _config.wipe()
