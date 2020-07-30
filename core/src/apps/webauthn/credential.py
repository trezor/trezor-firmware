import ustruct
from micropython import const
from ubinascii import hexlify

import storage.device
from trezor import log, utils
from trezor.crypto import bip32, chacha20poly1305, der, hashlib, hmac, random
from trezor.crypto.curve import ed25519, nist256p1

from apps.common import HARDENED, cbor, seed
from apps.webauthn import common

if False:
    from typing import Iterable, Optional

# Credential ID values
_CRED_ID_VERSION = b"\xf1\xd0\x02\x00"
CRED_ID_MIN_LENGTH = const(33)
CRED_ID_MAX_LENGTH = const(1024)
_KEY_HANDLE_LENGTH = const(64)

# Maximum user handle length in bytes.
_USER_ID_MAX_LENGTH = const(64)

# Maximum supported length of the RP name, user name or user displayName in bytes.
# Note: The WebAuthn spec allows authenticators to truncate to 64 bytes or more.
NAME_MAX_LENGTH = const(100)

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
_DEFAULT_ALGORITHM = common.COSE_ALG_ES256
_DEFAULT_CURVE = common.COSE_CURVE_P256

# Curves
_CURVE_NAME = {
    common.COSE_CURVE_ED25519: "ed25519",
    common.COSE_CURVE_P256: "nist256p1",
}

# Key paths
_U2F_KEY_PATH = const(0x80553246)


class Credential:
    def __init__(self) -> None:
        self.index = None  # type: Optional[int]
        self.id = b""  # type: bytes
        self.rp_id = ""  # type: str
        self.rp_id_hash = b""  # type: bytes
        self.user_id = None  # type: Optional[bytes]

    def __lt__(self, other: "Credential") -> bool:
        raise NotImplementedError

    def app_name(self) -> str:
        raise NotImplementedError

    def account_name(self) -> Optional[str]:
        return None

    def public_key(self) -> bytes:
        raise NotImplementedError

    def _private_key(self) -> bytes:
        raise NotImplementedError

    def sign(self, data: Iterable[bytes]) -> bytes:
        raise NotImplementedError

    def _u2f_sign(self, data: Iterable[bytes]) -> bytes:
        dig = hashlib.sha256()
        for segment in data:
            dig.update(segment)
        sig = nist256p1.sign(self._private_key(), dig.digest(), False)
        return der.encode_seq((sig[1:33], sig[33:]))

    def bogus_signature(self) -> bytes:
        raise NotImplementedError

    def hmac_secret_key(self) -> Optional[bytes]:
        return None

    def next_signature_counter(self) -> int:
        return storage.device.next_u2f_counter() or 0

    @staticmethod
    def from_bytes(data: bytes, rp_id_hash: bytes) -> "Credential":
        try:
            return Fido2Credential.from_cred_id(data, rp_id_hash)
        except Exception:
            return U2fCredential.from_key_handle(data, rp_id_hash)


# SLIP-0022: FIDO2 credential ID format for HD wallets
class Fido2Credential(Credential):
    def __init__(self) -> None:
        super().__init__()
        self.rp_name = None  # type: Optional[str]
        self.user_name = None  # type: Optional[str]
        self.user_display_name = None  # type: Optional[str]
        self.creation_time = 0  # type: int
        self.hmac_secret = False  # type: bool
        self.use_sign_count = False  # type: bool
        self.algorithm = _DEFAULT_ALGORITHM  # type: int
        self.curve = _DEFAULT_CURVE  # type: int

    def __lt__(self, other: Credential) -> bool:
        # Sort FIDO2 credentials newest first amongst each other.
        if isinstance(other, Fido2Credential):
            return self.creation_time > other.creation_time

        # Sort FIDO2 credentials before U2F credentials.
        return True

    def generate_id(self) -> None:
        self.creation_time = storage.device.next_u2f_counter() or 0

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
        iv = random.bytes(12)
        ctx = chacha20poly1305(key, iv)
        ctx.auth(self.rp_id_hash)
        ciphertext = ctx.encrypt(cbor.encode(data))
        tag = ctx.finish()
        self.id = _CRED_ID_VERSION + iv + ciphertext + tag

        if len(self.id) > CRED_ID_MAX_LENGTH:
            raise AssertionError

    @classmethod
    def from_cred_id(
        cls, cred_id: bytes, rp_id_hash: Optional[bytes]
    ) -> "Fido2Credential":
        if len(cred_id) < CRED_ID_MIN_LENGTH or cred_id[0:4] != _CRED_ID_VERSION:
            raise ValueError  # invalid length or version

        key = seed.derive_slip21_node_without_passphrase(
            [b"SLIP-0022", cred_id[0:4], b"Encryption key"]
        ).key()
        iv = cred_id[4:16]
        ciphertext = cred_id[16:-16]
        tag = cred_id[-16:]

        if rp_id_hash is None:
            ctx = chacha20poly1305(key, iv)
            data = ctx.decrypt(ciphertext)
            try:
                rp_id = cbor.decode(data)[_CRED_ID_RP_ID]
            except Exception as e:
                raise ValueError from e  # CBOR decoding failed
            rp_id_hash = hashlib.sha256(rp_id).digest()

        ctx = chacha20poly1305(key, iv)
        ctx.auth(rp_id_hash)
        data = ctx.decrypt(ciphertext)
        if not utils.consteq(ctx.finish(), tag):
            raise ValueError  # inauthentic ciphertext

        try:
            data = cbor.decode(data)
        except Exception as e:
            raise ValueError from e  # CBOR decoding failed

        if not isinstance(data, dict):
            raise ValueError  # invalid CBOR data

        cred = cls()
        cred.rp_id = data.get(_CRED_ID_RP_ID, None)
        cred.rp_id_hash = rp_id_hash
        cred.rp_name = data.get(_CRED_ID_RP_NAME, None)
        cred.user_id = data.get(_CRED_ID_USER_ID, None)
        cred.user_name = data.get(_CRED_ID_USER_NAME, None)
        cred.user_display_name = data.get(_CRED_ID_USER_DISPLAY_NAME, None)
        cred.creation_time = data.get(_CRED_ID_CREATION_TIME, 0)
        cred.hmac_secret = data.get(_CRED_ID_HMAC_SECRET, False)
        cred.use_sign_count = data.get(_CRED_ID_USE_SIGN_COUNT, False)
        cred.algorithm = data.get(_CRED_ID_ALGORITHM, _DEFAULT_ALGORITHM)
        cred.curve = data.get(_CRED_ID_CURVE, _DEFAULT_CURVE)
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
        if self.rp_name:
            self.rp_name = utils.truncate_utf8(self.rp_name, NAME_MAX_LENGTH)

        if self.user_name:
            self.user_name = utils.truncate_utf8(self.user_name, NAME_MAX_LENGTH)

        if self.user_display_name:
            self.user_display_name = utils.truncate_utf8(
                self.user_display_name, NAME_MAX_LENGTH
            )

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
        from apps.webauthn import knownapps

        app = knownapps.by_rp_id_hash(self.rp_id_hash)
        if app is not None:
            return app.label

        return self.rp_id

    def account_name(self) -> Optional[str]:
        if self.user_name:
            return self.user_name
        elif self.user_display_name:
            return self.user_display_name
        elif self.user_id:
            return hexlify(self.user_id).decode()
        else:
            return None

    def _private_key(self) -> bytes:
        path = [HARDENED | 10022, HARDENED | int.from_bytes(self.id[:4], "big")] + [
            HARDENED | i for i in ustruct.unpack(">4L", self.id[-16:])
        ]
        node = seed.derive_node_without_passphrase(path, _CURVE_NAME[self.curve])
        return node.private_key()

    def public_key(self) -> bytes:
        if self.curve == common.COSE_CURVE_P256:
            pubkey = nist256p1.publickey(self._private_key(), False)
            return cbor.encode(
                {
                    common.COSE_KEY_ALG: self.algorithm,
                    common.COSE_KEY_KTY: common.COSE_KEYTYPE_EC2,
                    common.COSE_KEY_CRV: self.curve,
                    common.COSE_KEY_X: pubkey[1:33],
                    common.COSE_KEY_Y: pubkey[33:],
                }
            )
        elif self.curve == common.COSE_CURVE_ED25519:
            pubkey = ed25519.publickey(self._private_key())
            return cbor.encode(
                {
                    common.COSE_KEY_ALG: self.algorithm,
                    common.COSE_KEY_KTY: common.COSE_KEYTYPE_OKP,
                    common.COSE_KEY_CRV: self.curve,
                    common.COSE_KEY_X: pubkey,
                }
            )
        raise TypeError

    def sign(self, data: Iterable[bytes]) -> bytes:
        if (self.algorithm, self.curve) == (
            common.COSE_ALG_ES256,
            common.COSE_CURVE_P256,
        ):
            return self._u2f_sign(data)
        elif (self.algorithm, self.curve) == (
            common.COSE_ALG_EDDSA,
            common.COSE_CURVE_ED25519,
        ):
            return ed25519.sign(
                self._private_key(), b"".join(segment for segment in data)
            )

        raise TypeError

    def bogus_signature(self) -> bytes:
        if (self.algorithm, self.curve) == (
            common.COSE_ALG_ES256,
            common.COSE_CURVE_P256,
        ):
            return der.encode_seq((b"\x0a" * 32, b"\x0a" * 32))
        elif (self.algorithm, self.curve) == (
            common.COSE_ALG_EDDSA,
            common.COSE_CURVE_ED25519,
        ):
            return b"\x0a" * 64

        raise TypeError

    def hmac_secret_key(self) -> Optional[bytes]:
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
    def __init__(self) -> None:
        super().__init__()
        self.node = None  # type: Optional[bip32.HDNode]

    def __lt__(self, other: "Credential") -> bool:
        # Sort U2F credentials after FIDO2 credentials.
        if isinstance(other, Fido2Credential):
            return False

        # Sort U2F credentials lexicographically amongst each other.
        return self.id < other.id

    def _private_key(self) -> bytes:
        if self.node is None:
            return b""
        return self.node.private_key()

    def public_key(self) -> bytes:
        return nist256p1.publickey(self._private_key(), False)

    def sign(self, data: Iterable[bytes]) -> bytes:
        return self._u2f_sign(data)

    def bogus_signature(self) -> bytes:
        return der.encode_seq((b"\x0a" * 32, b"\x0a" * 32))

    def generate_key_handle(self) -> None:
        # derivation path is m/U2F'/r'/r'/r'/r'/r'/r'/r'/r'
        path = [HARDENED | random.uniform(0x80000000) for _ in range(0, 8)]
        nodepath = [_U2F_KEY_PATH] + path

        # prepare signing key from random path, compute decompressed public key
        self.node = seed.derive_node_without_passphrase(nodepath, "nist256p1")

        # first half of keyhandle is keypath
        keypath = ustruct.pack("<8L", *path)

        # second half of keyhandle is a hmac of rp_id_hash and keypath
        mac = hmac.Hmac(self.node.private_key(), self.rp_id_hash, hashlib.sha256)
        mac.update(keypath)

        self.id = keypath + mac.digest()

    def app_name(self) -> str:
        from apps.webauthn import knownapps

        app = knownapps.by_rp_id_hash(self.rp_id_hash)
        if app is not None:
            return app.label

        return "%s...%s" % (
            hexlify(self.rp_id_hash[:4]).decode(),
            hexlify(self.rp_id_hash[-4:]).decode(),
        )

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
        cred.node = node
        return cred

    @staticmethod
    def _node_from_key_handle(
        rp_id_hash: bytes, keyhandle: bytes, pathformat: str
    ) -> Optional[bip32.HDNode]:
        # unpack the keypath from the first half of keyhandle
        keypath = keyhandle[:32]
        path = ustruct.unpack(pathformat, keypath)

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
        mac = hmac.Hmac(node.private_key(), rp_id_hash, hashlib.sha256)
        mac.update(keypath)

        # verify the hmac
        if not utils.consteq(mac.digest(), keyhandle[32:]):
            if __debug__:
                log.warning(__name__, "invalid key handle")
            return None

        return node
