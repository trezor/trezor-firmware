from trezor.crypto import elligator2, random
from trezor.crypto.curve import curve25519
from trezor.crypto.hashlib import sha512

_PREFIX = b"\x08\x43\x50\x61\x63\x65\x32\x35\x35\x06"
_PADDING = b"\x50\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x20"


class Cpace:
    """
    CPace, a balanced composable PAKE: https://datatracker.ietf.org/doc/draft-irtf-cfrg-cpace/
    """

    def __init__(self, cpace_host_public_key: bytes) -> None:
        self.host_public_key: bytes = cpace_host_public_key
        self.trezor_private_key: bytes
        self.trezor_public_key: bytes
        self.shared_secret: bytes

    def generate_keys_and_secret(self, code_code_entry: bytes) -> None:
        """
        Generate ephemeral key pair and a shared secret using Elligator2 with X25519.
        """
        pregenerator = sha512(_PREFIX + code_code_entry + _PADDING).digest()[
            :32
        ]  # TODO add handshake hash
        generator = elligator2.map_to_curve25519(pregenerator)
        self.trezor_private_key = random.bytes(32)
        if __debug__:
            self.trezor_private_key = b"\xf8\xb9\xa1\x3a\xe1\x30\xb3\xe1\x5b\x8e\xd5\x80\x85\x4f\xfc\xaf\x63\x4d\x6b\x0a\x10\xfd\xe7\xba\xde\xfd\xc3\xd1\x8d\x1a\x83\xf5"
        self.trezor_public_key = curve25519.multiply(self.trezor_private_key, generator)
        self.shared_secret = curve25519.multiply(
            self.trezor_private_key, self.host_public_key
        )
