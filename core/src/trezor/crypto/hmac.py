if False:
    from typing import Protocol, Type

    class HashContext(Protocol):

        digest_size = -1  # type: int
        block_size = -1  # type: int

        def __init__(self, data: bytes = None) -> None:
            ...

        def update(self, data: bytes) -> None:
            ...

        def digest(self) -> bytes:
            ...


class Hmac:
    def __init__(self, key: bytes, msg: bytes, digestmod: Type[HashContext]):
        self.digestmod = digestmod
        self.inner = digestmod()
        self.digest_size = self.inner.digest_size
        self.block_size = self.inner.block_size

        if len(key) > self.block_size:
            key = digestmod(key).digest()
        self.key = key + bytes(self.block_size - len(key))
        self.inner.update(bytes((x ^ 0x36) for x in self.key))
        if msg is not None:
            self.update(msg)

    def update(self, msg: bytes) -> None:
        """
        Update the context with data.
        """
        self.inner.update(msg)

    def digest(self) -> bytes:
        """
        Returns the digest of processed data.
        """
        outer = self.digestmod()
        outer.update(bytes((x ^ 0x5C) for x in self.key))
        outer.update(self.inner.digest())
        return outer.digest()


def new(key: bytes, msg: bytes, digestmod: Type[HashContext]) -> Hmac:
    """
    Creates a HMAC context object.
    """
    return Hmac(key, msg, digestmod)
