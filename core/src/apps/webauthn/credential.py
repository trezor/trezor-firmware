import ustruct
from micropython import const

from trezor import utils
from trezor.crypto import chacha20poly1305, hashlib, random

from apps.common import HARDENED, cbor, storage

if False:
    from typing import Optional

# Credential ID values
_CRED_ID_VERSION = const(1)
_CRED_ID_MIN_LENGTH = const(30)

# Credential ID keys
_CRED_ID_RP_ID = const(0x01)
_CRED_ID_RP_NAME = const(0x02)
_CRED_ID_USER_ID = const(0x03)
_CRED_ID_USER_NAME = const(0x04)
_CRED_ID_USER_DISPLAY_NAME = const(0x05)
_CRED_ID_CREATION_TIME = const(0x06)
_CRED_ID_HMAC_SECRET = const(0x07)

# Key paths
_FIDO_KEY_PATH = const(0xC649444F)
_FIDO_CRED_ID_KEY_PATH = b"FIDO2 Trezor Credential ID"
_FIDO_HMAC_SECRET_KEY_PATH = b"FIDO2 Trezor hmac-secret"


class Credential:
    def __init__(self) -> None:
        self.rp_id = ""  # type: str
        self.rp_name = None  # type: Optional[str]
        self.user_id = None  # type: Optional[bytes]
        self.user_name = None  # type: Optional[str]
        self.user_display_name = None  # type: Optional[str]
        self._creation_time = 0  # type: int
        self.hmac_secret = False  # type: bool
        self.id = b""  # type: bytes

    def __lt__(self, other: "Credential") -> bool:
        # Sort newest first.
        return self._creation_time > other._creation_time

    def generate_id(self) -> None:
        from apps.common import seed

        self._creation_time = storage.device.next_u2f_counter() or 0

        data = cbor.encode(
            {
                key: value
                for key, value in (
                    (_CRED_ID_RP_ID, self.rp_id),
                    (_CRED_ID_RP_NAME, self.rp_name),
                    (_CRED_ID_USER_ID, self.user_id),
                    (_CRED_ID_USER_NAME, self.user_name),
                    (_CRED_ID_USER_DISPLAY_NAME, self.user_display_name),
                    (_CRED_ID_CREATION_TIME, self._creation_time),
                    (_CRED_ID_HMAC_SECRET, self.hmac_secret),
                )
                if value
            }
        )

        key = seed.derive_slip21_node_without_passphrase([_FIDO_CRED_ID_KEY_PATH]).key()
        iv = random.bytes(12)
        ctx = chacha20poly1305(key, iv)
        ctx.auth(hashlib.sha256(self.rp_id.encode()).digest())
        ciphertext = ctx.encrypt(data)
        tag = ctx.finish()
        self.id = bytes([_CRED_ID_VERSION]) + iv + ciphertext + tag

    @staticmethod
    def from_id(cred_id: bytes, rp_id_hash: bytes) -> Optional["Credential"]:
        from apps.common import seed

        if len(cred_id) < _CRED_ID_MIN_LENGTH or cred_id[0] != _CRED_ID_VERSION:
            return None

        key = seed.derive_slip21_node_without_passphrase([_FIDO_CRED_ID_KEY_PATH]).key()
        iv = cred_id[1:13]
        ciphertext = cred_id[13:-16]
        tag = cred_id[-16:]
        ctx = chacha20poly1305(key, iv)
        ctx.auth(rp_id_hash)
        data = ctx.decrypt(ciphertext)
        if not utils.consteq(ctx.finish(), tag):
            return None

        try:
            data = cbor.decode(data)
        except Exception:
            return None

        if not isinstance(data, dict):
            return None

        cred = Credential()
        cred.rp_id = data.get(_CRED_ID_RP_ID, None)
        cred.rp_name = data.get(_CRED_ID_RP_NAME, None)
        cred.user_id = data.get(_CRED_ID_USER_ID, None)
        cred.user_name = data.get(_CRED_ID_USER_NAME, None)
        cred.user_display_name = data.get(_CRED_ID_USER_DISPLAY_NAME, None)
        cred._creation_time = data.get(_CRED_ID_CREATION_TIME, 0)
        cred.hmac_secret = data.get(_CRED_ID_HMAC_SECRET, False)
        cred.id = cred_id

        if (
            not cred.check_required()
            or not cred.check_data_types()
            or hashlib.sha256(cred.rp_id).digest() != rp_id_hash
        ):
            return None

        return cred

    def check_required(self):
        return (
            self.rp_id is not None
            and self.user_id is not None
            and self._creation_time is not None
        )

    def check_data_types(self):
        return (
            isinstance(self.rp_id, str)
            and isinstance(self.rp_name, (str, type(None)))
            and isinstance(self.user_id, (bytes, bytearray))
            and isinstance(self.user_name, (str, type(None)))
            and isinstance(self.user_display_name, (str, type(None)))
            and isinstance(self.hmac_secret, bool)
            and isinstance(self._creation_time, (int, type(None)))
            and isinstance(self.id, (bytes, bytearray))
        )

    def name(self) -> Optional[str]:
        from ubinascii import hexlify

        if self.user_name:
            return self.user_name
        elif self.user_display_name:
            return self.user_display_name
        elif self.user_id:
            return hexlify(self.user_id).decode()
        else:
            return None

    def private_key(self) -> bytes:
        from apps.common import seed

        path = [_FIDO_KEY_PATH] + [
            HARDENED | i for i in ustruct.unpack("<4L", self.id[-16:])
        ]
        node = seed.derive_node_without_passphrase(path, "nist256p1")
        return node.private_key()

    def hmac_secret_key(self) -> Optional[bytes]:
        # Returns the symmetric key for the hmac-secret extension also known as CredRandom.

        if not self.hmac_secret:
            return None

        from apps.common import seed

        node = seed.derive_slip21_node_without_passphrase(
            [_FIDO_HMAC_SECRET_KEY_PATH, self.id]
        )
        return node.key()
