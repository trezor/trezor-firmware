from trezor.crypto import aes, aesgcm, chacha20poly1305
from trezor.crypto.curve import curve25519, ed25519, nist256p1, secp256k1
from trezor.crypto.hashlib import (
    blake2b,
    blake2s,
    blake256,
    groestl512,
    ripemd160,
    sha1,
    sha3_256,
    sha3_512,
    sha256,
    sha512,
)

from .cipher_benchmark import DecryptBenchmark, EncryptBenchmark
from .common import random_bytes
from .curve_benchmark import (
    MultiplyBenchmark,
    PublickeyBenchmark,
    SignBenchmark,
    VerifyBenchmark,
)
from .hash_benchmark import HashBenchmark


# This is a wrapper above the trezor.crypto.curve.ed25519 module that satisfies SignCurve protocol, the modules uses `message` instead of `digest` in `sign()` and `verify()`
class Ed25519:
    def __init__(self) -> None:
        pass

    def generate_secret(self) -> bytes:
        return ed25519.generate_secret()

    def publickey(self, secret_key: bytes) -> bytes:
        return ed25519.publickey(secret_key)

    def sign(self, secret_key: bytes, digest: bytes) -> bytes:
        # ed25519.sign(secret_key: bytes, message: bytes, hasher: str = "") -> bytes:
        return ed25519.sign(secret_key, digest)

    def verify(self, public_key: bytes, signature: bytes, digest: bytes) -> bool:
        # ed25519.verify(public_key: bytes, signature: bytes, message: bytes) -> bool:
        return ed25519.verify(public_key, signature, digest)


benchmarks = {
    "crypto/hash/blake2b": HashBenchmark(lambda: blake2b()),
    "crypto/hash/blake2s": HashBenchmark(lambda: blake2s()),
    "crypto/hash/blake256": HashBenchmark(lambda: blake256()),
    "crypto/hash/groestl512": HashBenchmark(lambda: groestl512()),
    "crypto/hash/ripemd160": HashBenchmark(lambda: ripemd160()),
    "crypto/hash/sha1": HashBenchmark(lambda: sha1()),
    "crypto/hash/sha3_256": HashBenchmark(lambda: sha3_256()),
    "crypto/hash/sha3_512": HashBenchmark(lambda: sha3_512()),
    "crypto/hash/sha256": HashBenchmark(lambda: sha256()),
    "crypto/hash/sha512": HashBenchmark(lambda: sha512()),
    "crypto/cipher/aes128-ecb/encrypt": EncryptBenchmark(
        lambda: aes(aes.ECB, random_bytes(16), random_bytes(16)), 16
    ),
    "crypto/cipher/aes128-ecb/decrypt": DecryptBenchmark(
        lambda: aes(aes.ECB, random_bytes(16), random_bytes(16)), 16
    ),
    "crypto/cipher/aesgcm128/encrypt": EncryptBenchmark(
        lambda: aesgcm(random_bytes(16), random_bytes(16)), 16
    ),
    "crypto/cipher/aesgcm128/decrypt": DecryptBenchmark(
        lambda: aesgcm(random_bytes(16), random_bytes(16)), 16
    ),
    "crypto/cipher/aesgcm256/encrypt": EncryptBenchmark(
        lambda: aesgcm(random_bytes(32), random_bytes(16)), 16
    ),
    "crypto/cipher/aesgcm256/decrypt": DecryptBenchmark(
        lambda: aesgcm(random_bytes(32), random_bytes(16)), 16
    ),
    "crypto/cipher/chacha20poly1305/encrypt": EncryptBenchmark(
        lambda: chacha20poly1305(random_bytes(32), random_bytes(12)), 64
    ),
    "crypto/cipher/chacha20poly1305/decrypt": DecryptBenchmark(
        lambda: chacha20poly1305(random_bytes(32), random_bytes(12)), 64
    ),
    "crypto/curve/secp256k1/sign": SignBenchmark(secp256k1),
    "crypto/curve/secp256k1/verify": VerifyBenchmark(secp256k1),
    "crypto/curve/secp256k1/publickey": PublickeyBenchmark(secp256k1),
    "crypto/curve/secp256k1/multiply": MultiplyBenchmark(secp256k1),
    "crypto/curve/nist256p1/sign": SignBenchmark(nist256p1),
    "crypto/curve/nist256p1/verify": VerifyBenchmark(nist256p1),
    "crypto/curve/nist256p1/publickey": PublickeyBenchmark(nist256p1),
    "crypto/curve/nist256p1/multiply": MultiplyBenchmark(nist256p1),
    "crypto/curve/ed25519/sign": SignBenchmark(Ed25519()),
    "crypto/curve/ed25519/verify": VerifyBenchmark(Ed25519()),
    "crypto/curve/ed25519/publickey": PublickeyBenchmark(ed25519),
    "crypto/curve/curve25519/publickey": PublickeyBenchmark(curve25519),
    "crypto/curve/curve25519/multiply": MultiplyBenchmark(curve25519),
}
