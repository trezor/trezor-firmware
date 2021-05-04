from trezor.crypto.hashlib import blake256, ripemd160, sha256


class sha256_ripemd160(sha256):
    def digest(self) -> bytes:
        return ripemd160(super().digest()).digest()


class blake256_ripemd160(blake256):
    def digest(self) -> bytes:
        return ripemd160(super().digest()).digest()
