class Hmac:
    def __init__(self, key, msg, digest_cons):
        self._digest_cons = digest_cons
        self._inner = digest_cons()
        self.digest_size = self._inner.digest_size
        self.block_size = self._inner.block_size
        if len(key) > self.block_size:
            key = digest_cons(key).digest()
        self._key = key + bytes(self.block_size - len(key))
        self._inner.update(bytes((x ^ 0x36) for x in self._key))
        if msg is not None:
            self.update(msg)

    def update(self, msg):
        self._inner.update(msg)

    def digest(self):
        outer = self._digest_cons()
        outer.update(bytes((x ^ 0x5C) for x in self._key))
        outer.update(self._inner.digest())
        return outer.digest()

def new(key, msg, digest_cons):
    return Hmac(key, msg, digest_cons)
