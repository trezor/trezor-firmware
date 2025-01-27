from trezor.crypto import elligator2, random
from trezor.crypto.curve import curve25519
from trezor.crypto.hashlib import sha512

_PREFIX = b"\x08\x43\x50\x61\x63\x65\x32\x35\x35\x06"
_PADDING = b"\x6f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x20"


class Cpace:
    """
    CPace, a balanced composable PAKE: https://datatracker.ietf.org/doc/draft-irtf-cfrg-cpace/
    """

    def __init__(self, handshake_hash: bytes) -> None:
        self.handshake_hash: bytes = handshake_hash
        self.shared_secret: bytes
        self.trezor_private_key: bytes
        self.trezor_public_key: bytes

    def generate_keys_and_secret(self, code_code_entry: bytes) -> None:
        """
        Generate ephemeral key pair and a shared secret using Elligator2 with X25519.
        """
        sha_ctx = sha512(_PREFIX)
        sha_ctx.update(code_code_entry)
        sha_ctx.update(_PADDING)
        sha_ctx.update(self.handshake_hash)
        sha_ctx.update(b"\x00")
        pregenerator = sha_ctx.digest()[:32]
        generator = elligator2.map_to_curve25519(pregenerator)
        self.trezor_private_key = random.bytes(32)
        self.trezor_public_key = curve25519.multiply(self.trezor_private_key, generator)

    def compute_shared_secret(self, host_public_key: bytes) -> None:
        self.shared_secret = curve25519.multiply(
            self.trezor_private_key, host_public_key
        )
