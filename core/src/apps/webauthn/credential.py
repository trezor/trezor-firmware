import struct
from micropython import const
from trezorcrypto import vault_chacha as _vault_chacha
from typing import TYPE_CHECKING

import storage.device as storage_device
from trezor import utils
from trezor.crypto import (
    AuthenticationError,
    chacha20poly1305_decrypt,
    chacha20poly1305_encrypt,
    der,
    hashlib,
    random,
)
from trezor.crypto.curve import ed25519, nist256p1

from apps.common import cbor, seed
from apps.common.paths import HARDENED

from .common import COSE_ALG_EDDSA, COSE_ALG_ES256, COSE_CURVE_ED25519, COSE_CURVE_P256

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from collections.abc import Iterable
    from trezorcrypto import secbytes

    from trezor.crypto import bip32


def vault_chacha(
    key: bytes | secbytes,
    nonce: AnyBytes,
    data: AnyBytes,
    aad: AnyBytes = b"",
    tag: AnyBytes | None = None,
    decrypt: bool = False,
) -> tuple[bytes, bytes]:
    if not isinstance(key, bytes):
        return _vault_chacha(key, nonce, data, aad, tag, decrypt)
    if decrypt:
        ctx = chacha20poly1305_decrypt(key, nonce)
        ctx.auth(aad)
        output = ctx.decrypt(data)
        if tag is not None:
            ctx.finish(tag)
        return output, b""
    ctx = chacha20poly1305_encrypt(key, nonce)
    ctx.auth(aad)
    return ctx.encrypt(data), ctx.finish()


# Credential ID values
_CRED_ID_VERSION = b"\xf1\xd0\x02\x00"
_CRED_ID_MIN_LENGTH = const(33)
CRED_ID_MAX_LENGTH = const(1024)
_KEY_HANDLE_LENGTH = const(64)

# Maximum user handle length in bytes.
_USER_ID_MAX_LENGTH = const(64)

# Maximum supported length of the RP name, user name or user displayName in bytes.
# Note: The WebAuthn spec allows authenticators to truncate to 64 bytes or more.
_NAME_MAX_LENGTH = const(100)

# Credential ID keys
_CRED_ID_RP_ID = const(1)
_CRED_ID_RP_NAME = const(2)
_CRED_ID_USER_ID = const(3)
_CRED_ID_USER_NAME = const(4)
_CRED_ID_USER_DISPLAY_NAME = const(5)
_CRED_ID_CREATION_TIME = const(6)
_CRED_ID_HMAC_SECRET = const(7)
_CRED_ID_USE_SIGN_COUNT = const(8)
_CRED_ID_ALGORITHM = const(9)
_CRED_ID_CURVE = const(10)

# Defaults
_DEFAULT_ALGORITHM = COSE_ALG_ES256
_DEFAULT_CURVE = COSE_CURVE_P256

# Curves
_CURVE_NAME = {
    COSE_CURVE_ED25519: "ed25519",
    COSE_CURVE_P256: "nist256p1",
}

# Key paths
_U2F_KEY_PATH = const(0x8055_3246)


class Credential:
    def __init__(self) -> None:
        self.index: int | None = None
        self.id: bytes = b""
        self.rp_id: str = ""
        self.rp_id_hash: bytes = b""
        self.user_id: bytes | None = None

    def __lt__(self, other: "Credential") -> bool:
        raise NotImplementedError

    def app_name(self) -> str:
        raise NotImplementedError

    def icon_name(self) -> str | None:
        from . import knownapps

        fido_app = knownapps.by_rp_id_hash(self.rp_id_hash)
        return None if fido_app is None else fido_app.icon_name

    def account_name(self) -> str | None:
        return None

    def public_key(self) -> bytes:
        raise NotImplementedError

    def _private_key(self) -> bytes | secbytes:
        raise NotImplementedError

    def sign(self, data: Iterable[bytes]) -> bytes:
        raise NotImplementedError

    def _u2f_sign(self, data: Iterable[AnyBytes]) -> AnyBytes:
        dig = hashlib.sha256()
        for segment in data:
            dig.update(segment)
        sig = nist256p1.sign(self._private_key(), dig.digest(), False)
        return der.encode_signature(sig)

    def bogus_signature(self) -> bytes:
        raise NotImplementedError

    def hmac_secret_key(self) -> bytes | secbytes | None:
        return None

    def next_signature_counter(self) -> int:
        return storage_device.next_u2f_counter() or 0

    @staticmethod
    def from_bytes(data: bytes, rp_id_hash: bytes) -> "Credential":
        try:
            return Fido2Credential.from_cred_id(data, rp_id_hash)
        except Exception:
            return U2fCredential.from_key_handle(data, rp_id_hash)


class Fido2Credential(Credential):
    """
    This class implements the SLIP-0022 FIDO2 Credential ID format for HD wallets, see
    https://github.com/satoshilabs/slips/blob/master/slip-0022.md.
    """

    def __init__(self) -> None:
        super().__init__()
        self.rp_name: str | None = None
        self.user_name: str | None = None
        self.user_display_name: str | None = None
        self.creation_time: int = 0
        self.hmac_secret: bool = False
        self.use_sign_count: bool = False
        self.algorithm: int = _DEFAULT_ALGORITHM
        self.curve: int = _DEFAULT_CURVE

    def __lt__(self, other: Credential) -> bool:
        # Sort FIDO2 credentials newest first amongst each other.
        if isinstance(other, Fido2Credential):
            return self.creation_time > other.creation_time

        # Sort FIDO2 credentials before U2F credentials.
        return True

    def generate_id(self) -> None:
        self.creation_time = storage_device.next_u2f_counter() or 0

        if not self.check_required_fields():
            raise AssertionError

        data = {
            key: value
            for key, value in (
                (_CRED_ID_RP_ID, self.rp_id),
                (_CRED_ID_RP_NAME, self.rp_name),
                (_CRED_ID_USER_ID, self.user_id),
                (_CRED_ID_USER_NAME, self.user_name),
                (_CRED_ID_USER_DISPLAY_NAME, self.user_display_name),
                (_CRED_ID_CREATION_TIME, self.creation_time),
                (_CRED_ID_HMAC_SECRET, self.hmac_secret),
                (_CRED_ID_USE_SIGN_COUNT, self.use_sign_count),
            )
            if value
        }

        if self.algorithm != _DEFAULT_ALGORITHM or self.curve != _DEFAULT_CURVE:
            data[_CRED_ID_ALGORITHM] = self.algorithm
            data[_CRED_ID_CURVE] = self.curve

        key = seed.derive_slip21_node_without_passphrase(
            [b"SLIP-0022", _CRED_ID_VERSION, b"Encryption key"]
        ).key()
        iv = random.bytes(chacha20poly1305_encrypt.nonce_size)
        ciphertext, tag = vault_chacha(key, iv, cbor.encode(data), self.rp_id_hash)
        self.id = _CRED_ID_VERSION + iv + ciphertext + tag

        if len(self.id) > CRED_ID_MAX_LENGTH:
            raise AssertionError

    @classmethod
    def from_cred_id(
        cls, cred_id: bytes, rp_id_hash: bytes | None
    ) -> "Fido2Credential":
        if len(cred_id) < _CRED_ID_MIN_LENGTH or cred_id[0:4] != _CRED_ID_VERSION:
            raise ValueError  # invalid length or version

        key = seed.derive_slip21_node_without_passphrase(
            [b"SLIP-0022", cred_id[0:4], b"Encryption key"]
        ).key()
        iv_end = len(_CRED_ID_VERSION) + chacha20poly1305_decrypt.nonce_size
        iv = cred_id[len(_CRED_ID_VERSION) : iv_end]
        ciphertext = cred_id[iv_end : -chacha20poly1305_decrypt.tag_size]
        tag = cred_id[-chacha20poly1305_decrypt.tag_size :]

        if rp_id_hash is None:
            data, _ = vault_chacha(key, iv, ciphertext, b"", None, True)
            try:
                rp_id = cbor.decode(data)[_CRED_ID_RP_ID]
            except Exception as e:
                raise ValueError from e  # CBOR decoding failed
            rp_id_hash = hashlib.sha256(rp_id).digest()

        try:
            data, _ = vault_chacha(key, iv, ciphertext, rp_id_hash, tag, True)
        except AuthenticationError:
            raise ValueError  # inauthentic ciphertext

        try:
            data = cbor.decode(data)
        except Exception as e:
            raise ValueError from e  # CBOR decoding failed

        if not isinstance(data, dict):
            raise ValueError  # invalid CBOR data

        get = data.get  # local_cache_attribute

        cred = cls()
        cred.rp_id = get(_CRED_ID_RP_ID, "")
        cred.rp_id_hash = rp_id_hash
        cred.rp_name = get(_CRED_ID_RP_NAME, None)
        cred.user_id = get(_CRED_ID_USER_ID, None)
        cred.user_name = get(_CRED_ID_USER_NAME, None)
        cred.user_display_name = get(_CRED_ID_USER_DISPLAY_NAME, None)
        cred.creation_time = get(_CRED_ID_CREATION_TIME, 0)
        cred.hmac_secret = get(_CRED_ID_HMAC_SECRET, False)
        cred.use_sign_count = get(_CRED_ID_USE_SIGN_COUNT, False)
        cred.algorithm = get(_CRED_ID_ALGORITHM, _DEFAULT_ALGORITHM)
        cred.curve = get(_CRED_ID_CURVE, _DEFAULT_CURVE)
        cred.id = cred_id

        if (
            (_CRED_ID_ALGORITHM in data) != (_CRED_ID_CURVE in data)
            or not cred.check_required_fields()
            or not cred.check_data_types()
            or hashlib.sha256(cred.rp_id).digest() != rp_id_hash
        ):
            raise ValueError  # data consistency check failed

        return cred

    def truncate_names(self) -> None:
        for name in ("rp_name", "user_name", "user_display_name"):
            value = getattr(self, name)
            if value:
                if value.isspace():
                    # Don't store blank names.
                    value = None
                else:
                    # If the name is stored then the WebAuthn spec allows truncation.
                    value = utils.truncate_utf8(value, _NAME_MAX_LENGTH)
                setattr(self, name, value)

    def check_required_fields(self) -> bool:
        return (
            self.rp_id is not None
            and self.user_id is not None
            and len(self.user_id) <= _USER_ID_MAX_LENGTH
            and self.creation_time is not None
        )

    def check_data_types(self) -> bool:
        return (
            isinstance(self.rp_id, str)
            and isinstance(self.rp_name, (str, type(None)))
            and isinstance(self.user_id, bytes)
            and isinstance(self.user_name, (str, type(None)))
            and isinstance(self.user_display_name, (str, type(None)))
            and isinstance(self.hmac_secret, bool)
            and isinstance(self.use_sign_count, bool)
            and isinstance(self.creation_time, (int, type(None)))
            and isinstance(self.algorithm, (int, type(None)))
            and isinstance(self.curve, (int, type(None)))
            and isinstance(self.id, bytes)
        )

    def app_name(self) -> str:
        from . import knownapps

        app = knownapps.by_rp_id_hash(self.rp_id_hash)
        if app is not None:
            return app.label

        return self.rp_id

    def account_name(self) -> str | None:
        if self.user_name:
            return self.user_name
        elif self.user_display_name:
            return self.user_display_name
        elif self.user_id:
            return self.user_id.hex()
        else:
            return None

    def _private_key(self) -> bytes | secbytes:
        path = [HARDENED | 10022, HARDENED | int.from_bytes(self.id[:4], "big")] + [
            HARDENED | i for i in struct.unpack(">4L", self.id[-16:])
        ]
        node = seed.derive_node_without_passphrase(path, _CURVE_NAME[self.curve])
        return node.private_key()

    def public_key(self) -> bytes:
        from . import common

        curve = self.curve  # local_cache_attribute

        if curve == COSE_CURVE_P256:
            pubkey = nist256p1.publickey(self._private_key(), False)
            return cbor.encode(
                {
                    common.COSE_KEY_ALG: self.algorithm,
                    common.COSE_KEY_KTY: common.COSE_KEYTYPE_EC2,
                    common.COSE_KEY_CRV: curve,
                    common.COSE_KEY_X: pubkey[1:33],
                    common.COSE_KEY_Y: pubkey[33:],
                }
            )
        elif curve == COSE_CURVE_ED25519:
            pubkey = ed25519.publickey(self._private_key())
            return cbor.encode(
                {
                    common.COSE_KEY_ALG: self.algorithm,
                    common.COSE_KEY_KTY: common.COSE_KEYTYPE_OKP,
                    common.COSE_KEY_CRV: curve,
                    common.COSE_KEY_X: pubkey,
                }
            )
        raise TypeError

    def sign(self, data: Iterable[bytes]) -> AnyBytes:
        if (self.algorithm, self.curve) == (
            COSE_ALG_ES256,
            COSE_CURVE_P256,
        ):
            return self._u2f_sign(data)
        elif (self.algorithm, self.curve) == (
            COSE_ALG_EDDSA,
            COSE_CURVE_ED25519,
        ):
            return ed25519.sign(
                self._private_key(), b"".join(segment for segment in data)
            )

        raise TypeError

    def bogus_signature(self) -> AnyBytes:
        if (self.algorithm, self.curve) == (
            COSE_ALG_ES256,
            COSE_CURVE_P256,
        ):
            return der.encode_signature(b"\x0a" * 64)
        elif (self.algorithm, self.curve) == (
            COSE_ALG_EDDSA,
            COSE_CURVE_ED25519,
        ):
            return b"\x0a" * 64

        raise TypeError

    def hmac_secret_key(self) -> bytes | secbytes | None:
        # Returns the symmetric key for the hmac-secret extension also known as CredRandom.

        if not self.hmac_secret:
            return None

        node = seed.derive_slip21_node_without_passphrase(
            [b"SLIP-0022", self.id[0:4], b"hmac-secret", self.id]
        )

        return node.key()

    def next_signature_counter(self) -> int:
        if not self.use_sign_count:
            return 0
        return super().next_signature_counter()


class U2fCredential(Credential):
    def __lt__(self, other: "Credential") -> bool:
        # Sort U2F credentials after FIDO2 credentials.
        if isinstance(other, Fido2Credential):
            return False

        # Sort U2F credentials lexicographically amongst each other.
        return self.id < other.id

    def _private_key(self) -> bytes | secbytes:
        # HID polling and the confirmation workflow have separate owners.
        # Keep the authenticated public handle, never an old request's node.
        node = self._node_from_key_handle(self.rp_id_hash, self.id, "<8L")
        if node is None:
            node = self._node_from_key_handle(self.rp_id_hash, self.id, ">8L")
        if node is None:
            raise ValueError("Invalid credential key handle")
        return node.private_key()

    def public_key(self) -> bytes:
        return nist256p1.publickey(self._private_key(), False)

    def sign(self, data: Iterable[bytes]) -> AnyBytes:
        return self._u2f_sign(data)

    def bogus_signature(self) -> AnyBytes:
        return der.encode_signature(b"\x0a" * 64)

    def generate_key_handle(self) -> None:
        # derivation path is m/U2F'/r'/r'/r'/r'/r'/r'/r'/r'
        path = [HARDENED | random.uniform(0x8000_0000) for _ in range(0, 8)]
        nodepath = [_U2F_KEY_PATH] + path

        # prepare signing key from random path, compute decompressed public key
        node = seed.derive_node_without_passphrase(nodepath, "nist256p1")

        # first half of keyhandle is keypath
        keypath = struct.pack("<8L", *path)

        # second half of keyhandle is a hmac of rp_id_hash and keypath
        mac = seed.slip21_mac(node.private_key(), self.rp_id_hash + keypath)
        self.id = keypath + mac

    def app_name(self) -> str:
        from . import knownapps

        app = knownapps.by_rp_id_hash(self.rp_id_hash)
        if app is not None:
            return app.label

        start = self.rp_id_hash[:4].hex()
        end = self.rp_id_hash[-4:].hex()
        return f"{start}...{end}"

    @staticmethod
    def from_key_handle(key_handle: bytes, rp_id_hash: bytes) -> "U2fCredential":
        if len(key_handle) != _KEY_HANDLE_LENGTH:
            raise ValueError  # key length mismatch

        # check the keyHandle and generate the signing key
        node = U2fCredential._node_from_key_handle(rp_id_hash, key_handle, "<8L")
        if node is None:
            # prior to firmware version 2.0.8, keypath was serialized in a
            # big-endian manner, instead of little endian, like in trezor-mcu.
            # try to parse it as big-endian now and check the HMAC.
            node = U2fCredential._node_from_key_handle(rp_id_hash, key_handle, ">8L")
        if node is None:
            # specific error logged in msg_authenticate_genkey
            raise ValueError  # failed to parse key handle in either direction

        cred = U2fCredential()
        cred.id = key_handle
        cred.rp_id_hash = rp_id_hash
        return cred

    @staticmethod
    def _node_from_key_handle(
        rp_id_hash: bytes, keyhandle: bytes, pathformat: str
    ) -> bip32.HDNode | None:
        from trezor import log

        # unpack the keypath from the first half of keyhandle
        keypath = keyhandle[:32]
        path = struct.unpack(pathformat, keypath)

        # check high bit for hardened keys
        for i in path:
            if not i & HARDENED:
                if __debug__:
                    log.warning(__name__, "invalid key path")
                return None

        # derive the signing key
        nodepath = [_U2F_KEY_PATH] + list(path)
        node = seed.derive_node_without_passphrase(nodepath, "nist256p1")

        # second half of keyhandle is a hmac of rp_id_hash and keypath
        mac = seed.slip21_mac(node.private_key(), rp_id_hash + keypath)

        # verify the hmac
        if not utils.consteq(mac, keyhandle[32:]):
            if __debug__:
                log.warning(__name__, "invalid key handle")
            return None

        return node
