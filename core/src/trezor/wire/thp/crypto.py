import ustruct
from micropython import const
from trezorcrypto import aesgcm, bip32, curve25519, hmac
from typing import TYPE_CHECKING

from storage import device
from trezor import log, utils
from trezor.crypto.hashlib import sha256
from trezor.wire.thp import ThpDecryptionError

if TYPE_CHECKING:
    from buffer_types import AnyBuffer, AnyBytes

# The HARDENED flag is taken from apps.common.paths
# It is not imported to save on resources
HARDENED = const(0x8000_0000)
PUBKEY_LENGTH = const(32)

if __debug__:
    from trezor.utils import hexlify_if_bytes


def enc(buffer: AnyBuffer, key: bytes, nonce: int, auth_data: bytes = b"") -> bytes:
    """
    Encrypts the provided `buffer` with AES-GCM (in place).
    Returns a 16-byte long encryption tag.
    """
    if __debug__:
        log.debug(__name__, "enc (key: %s, nonce: %d)", hexlify_if_bytes(key), nonce)
    iv = _get_iv_from_nonce(nonce)
    aes_ctx = aesgcm(key, iv)
    aes_ctx.auth(auth_data)
    aes_ctx.encrypt_in_place(buffer)
    return aes_ctx.finish()


def dec(
    buffer: AnyBuffer,
    tag: AnyBytes,
    key: AnyBytes,
    nonce: int,
    auth_data: AnyBytes = b"",
) -> bool:
    """
    Decrypts the provided buffer (in place). Returns `True` if the provided authentication `tag` is the same as
    the tag computed in decryption, otherwise it returns `False`.
    """
    iv = _get_iv_from_nonce(nonce)
    if __debug__:
        log.debug(__name__, "dec (key: %s, nonce: %d)", hexlify_if_bytes(key), nonce)
    aes_ctx = aesgcm(key, iv)
    aes_ctx.auth(auth_data)
    aes_ctx.decrypt_in_place(buffer)
    computed_tag = aes_ctx.finish()
    return computed_tag == tag


class BusyDecoder:

    def __init__(self, key: bytes, nonce: int, auth_data: bytes = b"") -> None:
        iv = _get_iv_from_nonce(nonce)
        self.aes_ctx = aesgcm(key, iv)
        self.aes_ctx.auth(auth_data)

    def decrypt_part(self, part: AnyBuffer) -> None:
        self.aes_ctx.decrypt_in_place(part)

    def finish_and_check_tag(self, tag: bytes) -> bool:
        computed_tag = self.aes_ctx.finish()
        return computed_tag == tag


PROTOCOL_NAME = b"Noise_XX_25519_AESGCM_SHA256\x00\x00\x00\x00"
IV_1 = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
IV_2 = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"


class Handshake:
    """
    `Handshake` holds (temporary) values and keys that are used during the creation of an encrypted channel.
    The following values should be saved for future use before disposing of this object:
    - `h` - handshake hash, can be used to bind other values to the channel
    - `key_receive` - key for decrypting incoming communication
    - `key_send` - key for encrypting outgoing communication
    """

    def __init__(self) -> None:
        self.trezor_ephemeral_private_key: bytes
        self.ck: bytes
        self.k: bytes
        self.h: bytes
        self.key_receive: bytes
        self.key_send: bytes

    def handle_th1_crypto(
        self,
        device_properties: AnyBytes,
        host_ephemeral_public_key: AnyBytes,
    ) -> tuple[bytes, bytes, bytes]:

        trezor_static_private_key, trezor_static_public_key = _derive_static_key_pair()
        self.trezor_ephemeral_private_key = curve25519.generate_secret()
        trezor_ephemeral_public_key = curve25519.publickey(
            self.trezor_ephemeral_private_key
        )
        self.h = _hash_of_two(PROTOCOL_NAME, device_properties)
        self.h = _hash_of_two(self.h, host_ephemeral_public_key)
        self.h = _hash_of_two(self.h, b"")
        self.h = _hash_of_two(self.h, trezor_ephemeral_public_key)
        point = curve25519.multiply(
            self.trezor_ephemeral_private_key, host_ephemeral_public_key
        )
        self.ck, self.k = _hkdf(PROTOCOL_NAME, point)
        mask = _hash_of_two(trezor_static_public_key, trezor_ephemeral_public_key)
        trezor_masked_static_public_key = curve25519.multiply(
            mask, trezor_static_public_key
        )
        aes_ctx = aesgcm(self.k, IV_1)
        encrypted_trezor_static_public_key = aes_ctx.encrypt(
            trezor_masked_static_public_key
        )
        if __debug__:
            log.debug(
                __name__,
                "th1 - enc (key: %s, nonce: %d, handshake_hash %s)",
                hexlify_if_bytes(self.k),
                0,
                hexlify_if_bytes(self.h),
            )

        aes_ctx.auth(self.h)
        tag_to_encrypted_key = aes_ctx.finish()
        encrypted_trezor_static_public_key = (
            encrypted_trezor_static_public_key + tag_to_encrypted_key
        )
        self.h = _hash_of_two(self.h, encrypted_trezor_static_public_key)
        point = curve25519.multiply(
            trezor_static_private_key, host_ephemeral_public_key
        )
        self.ck, self.k = _hkdf(self.ck, curve25519.multiply(mask, point))
        aes_ctx = aesgcm(self.k, IV_1)
        aes_ctx.auth(self.h)
        tag = aes_ctx.finish()
        self.h = _hash_of_two(self.h, tag)
        return (trezor_ephemeral_public_key, encrypted_trezor_static_public_key, tag)

    def handle_th2_crypto(
        self,
        encrypted_host_static_public_key: AnyBuffer,
        encrypted_payload: AnyBuffer,
    ) -> None:

        aes_ctx = aesgcm(self.k, IV_2)

        # The new value of hash `h` MUST be computed before the `encrypted_host_static_public_key` is decrypted.
        # However, decryption of `encrypted_host_static_public_key` MUST use the previous value of `h` for
        # authentication of the gcm tag.
        aes_ctx.auth(self.h)  # Authenticate with the previous value of `h`
        self.h = _hash_of_two(
            self.h, encrypted_host_static_public_key
        )  # Compute new value
        aes_ctx.decrypt_in_place(
            memoryview(encrypted_host_static_public_key)[:PUBKEY_LENGTH]
        )
        if __debug__:
            log.debug(
                __name__, "th2 - dec (key: %s, nonce: %d)", hexlify_if_bytes(self.k), 1
            )
        host_static_public_key = memoryview(encrypted_host_static_public_key)[
            :PUBKEY_LENGTH
        ]
        tag = aes_ctx.finish()
        if tag != encrypted_host_static_public_key[-16:]:
            raise ThpDecryptionError()

        self.ck, self.k = _hkdf(
            self.ck,
            curve25519.multiply(
                self.trezor_ephemeral_private_key, host_static_public_key
            ),
        )
        aes_ctx = aesgcm(self.k, IV_1)
        aes_ctx.auth(self.h)
        self.h = _hash_of_two(self.h, memoryview(encrypted_payload))
        aes_ctx.decrypt_in_place(memoryview(encrypted_payload)[:-16])
        if __debug__:
            log.debug(
                __name__, "th2 - dec (key: %s, nonce: %d)", hexlify_if_bytes(self.k), 0
            )
        tag = aes_ctx.finish()
        if tag != encrypted_payload[-16:]:
            raise ThpDecryptionError()

        self.key_receive, self.key_send = _hkdf(self.ck, b"")
        if __debug__:
            log.debug(
                __name__,
                "(key_receive: %s, key_send: %s)",
                hexlify_if_bytes(self.key_receive),
                hexlify_if_bytes(self.key_send),
            )

    def get_handshake_completion_response(self, trezor_state: bytes) -> bytes:
        aes_ctx = aesgcm(self.key_send, IV_1)
        encrypted_trezor_state = aes_ctx.encrypt(trezor_state)
        tag = aes_ctx.finish()
        return encrypted_trezor_state + tag


def _derive_static_key_pair() -> tuple[bytes, bytes]:
    node_int = HARDENED | int.from_bytes(b"\x00THP", "big")
    node = bip32.from_seed(device.get_device_secret(), "curve25519")
    node.derive(node_int)

    trezor_static_private_key = node.private_key()
    trezor_static_public_key = node.public_key()[1:33]
    # Note: the first byte (\x01) of the public key is removed, as it
    # only indicates the type of the elliptic curve used

    return trezor_static_private_key, trezor_static_public_key


def get_trezor_static_public_key() -> bytes:
    _, public_key = _derive_static_key_pair()
    return public_key


def _hkdf(chaining_key: bytes, input: bytes) -> tuple[bytes, bytes]:
    temp_key = hmac(hmac.SHA256, chaining_key, input).digest()
    output_1 = hmac(hmac.SHA256, temp_key, b"\x01").digest()
    ctx_output_2 = hmac(hmac.SHA256, temp_key, output_1)
    ctx_output_2.update(b"\x02")
    output_2 = ctx_output_2.digest()
    return (output_1, output_2)


def _hash_of_two(part_1: AnyBytes, part_2: AnyBytes) -> bytes:
    ctx = sha256(part_1)
    ctx.update(part_2)
    return ctx.digest()


def _get_iv_from_nonce(nonce: int) -> bytes:
    utils.ensure(nonce <= 0xFFFFFFFFFFFFFFFF, "Nonce overflow, terminate the channel")
    return ustruct.pack(">4sQ", b"\x00\x00\x00\x00", nonce)
