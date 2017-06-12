
class Hmac:

    def __init__(self, key, msg, digestmod):
        self.__digestmod = digestmod
        self.__inner = digestmod()
        self.digest_size = self.__inner.digest_size
        self.block_size = self.__inner.block_size
        if len(key) > self.block_size:
            key = digestmod(key).digest()
        self.__key = key + bytes(self.block_size - len(key))
        self.__inner.update(bytes((x ^ 0x36) for x in self.__key))
        if msg is not None:
            self.update(msg)

    def update(self, msg: bytes) -> None:
        '''
        Update the context with data.
        '''
        self.__inner.update(msg)

    def digest(self) -> bytes:
        '''
        Returns the digest of processed data.
        '''
        outer = self.__digestmod()
        outer.update(bytes((x ^ 0x5C) for x in self.__key))
        outer.update(self.__inner.digest())
        return outer.digest()


def new(key, msg, digestmod) -> Hmac:
    '''
    Creates a HMAC context object.
    '''
    return Hmac(key, msg, digestmod)
