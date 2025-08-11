from trezor.crypto import elligator2, random
from trezor.crypto.curve import curve25519
from trezor.crypto.hashlib import sha512

_PREFIX = b"\x08\x43\x50\x61\x63\x65\x32\x35\x35\x06"
_PADDING = b"\x6f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x20"
_SID_STR = b"\x00"

if __debug__:
    _LEN_PRS = 6


class Cpace:
    """
    CPace, a balanced composable PAKE: https://datatracker.ietf.org/doc/draft-irtf-cfrg-cpace/
    """

    def __init__(self, handshake_hash: bytes) -> None:
        self.handshake_hash: bytes = handshake_hash
        self.shared_secret: bytes
        self.trezor_private_key: bytes
        self.trezor_public_key: bytes

    def generate_keys(self, code_code_entry: bytes) -> None:
        """
        Generate an ephemeral key pair using Elligator2 with X25519.
        """
        assert len(code_code_entry) == _LEN_PRS

        # See https://datatracker.ietf.org/doc/draft-irtf-cfrg-cpace/
        # len(DSI) = 8 (b"\x08")
        # DSI = CPace255
        # len(PRS) = 6 (b"\x06")
        # PRS = 'code_code_entry'
        # len_zpad = 111 (b"\x6f")
        # len(CI) = 32 (b"\x20")
        # CI = 'self.handshake_hash'
        # len(sid) = 0 (b"\x00)
        # sid = b""

        # fmt: off
        sha_ctx = sha512(_PREFIX)            # len(DSI) | DSI | len(PRS)
        sha_ctx.update(code_code_entry)      # PRS
        sha_ctx.update(_PADDING)             # len_zpad | zpad | len(CI)
        sha_ctx.update(self.handshake_hash)  # CI
        sha_ctx.update(_SID_STR)             # len(sid) | sid
        # fmt:on

        pregenerator = sha_ctx.digest()[:32]
        generator = elligator2.map_to_curve25519(pregenerator)
        self.trezor_private_key = random.bytes(32)
        self.trezor_public_key = curve25519.multiply(self.trezor_private_key, generator)

    def compute_shared_secret(self, host_public_key: bytes) -> None:
        """
        Compute a shared secret using host's public (cpace) key.
        Must be called after `generate_keys`.
        """
        self.shared_secret = curve25519.multiply(
            self.trezor_private_key, host_public_key
        )
