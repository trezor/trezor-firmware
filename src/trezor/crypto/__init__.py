from gc import collect

from trezorcrypto import (  # noqa: F401
    aes,
    bip32,
    bip39,
    chacha20poly1305,
    crc,
    monero,
    nem,
    pbkdf2,
    random,
    rfc6979,
)


class SecureContext:
    def __init__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for k in self.__dict__:
            o = getattr(self, k)
            if hasattr(o, "__del__"):
                o.__del__()
        collect()
