import typing as t
from hashlib import sha512

from . import curve25519

_PREFIX = b"\x08\x43\x50\x61\x63\x65\x32\x35\x35\x06"
_PADDING = b"\x6f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x20"


class Cpace:
    """
    CPace, a balanced composable PAKE: https://datatracker.ietf.org/doc/draft-irtf-cfrg-cpace/
    """

    random_bytes: t.Callable[[int], bytes]

    def __init__(self, handshake_hash: bytes) -> None:
        self.handshake_hash: bytes = handshake_hash
        self.shared_secret: bytes
        self.host_private_key: bytes
        self.host_public_key: bytes

    def generate_keys_and_secret(
        self, code_code_entry: bytes, trezor_public_key: bytes
    ) -> None:
        """
        Generate ephemeral key pair and a shared secret using Elligator2 with X25519.
        """
        sha_ctx = sha512(_PREFIX)
        sha_ctx.update(code_code_entry)
        sha_ctx.update(_PADDING)
        sha_ctx.update(self.handshake_hash)
        sha_ctx.update(b"\x00")
        pregenerator = sha_ctx.digest()[:32]
        generator = curve25519.elligator2(pregenerator)
        self.host_private_key = self.random_bytes(32)
        self.host_public_key = curve25519.multiply(self.host_private_key, generator)
        self.shared_secret = curve25519.multiply(
            self.host_private_key, trezor_public_key
        )
