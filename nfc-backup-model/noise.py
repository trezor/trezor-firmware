import hmac
import logging
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256

from crypto import (
    PrivateKey,
    aead_decrypt,
    aead_encrypt,
    dh,
    generate_keypair,
    public_key,
)

logger = logging.getLogger(__name__)


class InitiatorXXPsk3State(Enum):
    READY_FOR_REQUEST1 = 1
    WAITING_FOR_RESPONSE1 = 2
    READY_FOR_REQUEST2 = 3
    HANDSHAKE_COMPLETE = 4


class ResponderXXPsk3State(Enum):
    WAITING_FOR_REQUEST1 = 1
    READY_FOR_RESPONSE1 = 2
    WAITING_FOR_REQUEST2 = 3
    HANDSHAKE_COMPLETE = 4


DHLEN = 32
HASHLEN = 32
AEAD_TAG_LEN = 16
NONCE_LIMIT = 2**64 - 1

XX_PROTOCOL_NAME = b"Noise_XXpsk3_25519_AESGCM_SHA256"


def hash(data: bytes) -> bytes:
    return sha256(data).digest()


def hmac_hash(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, sha256).digest()


def hkdf(
    chaining_key: bytes, input_key_material: bytes, num_outputs: int
) -> tuple[bytes, ...]:
    temp_key = hmac_hash(chaining_key, input_key_material)
    output1 = hmac_hash(temp_key, b"\x01")
    output2 = hmac_hash(temp_key, output1 + b"\x02")
    if num_outputs == 2:
        return (output1, output2)
    output3 = hmac_hash(temp_key, output2 + b"\x03")
    if num_outputs == 3:
        return (output1, output2, output3)
    raise ValueError()


class CipherState:
    def __init__(self, key: bytes | None = None) -> None:
        self.key = key
        self.nonce = 0

    def get_nonce_bytes(self) -> bytes:
        return self.nonce.to_bytes(8, "big")

    def encrypt_with_ad(self, ad: bytes, plaintext: bytes) -> bytes:
        if self.key is None:
            return plaintext
        if self.nonce == NONCE_LIMIT:
            raise ValueError()
        ciphertext = aead_encrypt(self.key, self.get_nonce_bytes(), plaintext, ad)
        self.nonce += 1
        return ciphertext

    def decrypt_with_ad(self, ad: bytes, ciphertext: bytes) -> bytes:
        if self.key is None:
            return ciphertext
        if self.nonce == NONCE_LIMIT:
            raise ValueError()
        plaintext = aead_decrypt(self.key, self.get_nonce_bytes(), ciphertext, ad)
        self.nonce += 1
        return plaintext


class SymmetricState:
    def __init__(self, protocol_name: bytes = XX_PROTOCOL_NAME) -> None:
        if len(protocol_name) <= HASHLEN:
            self.handshake_hash = protocol_name + b"\x00" * (
                HASHLEN - len(protocol_name)
            )
        else:
            self.handshake_hash = hash(protocol_name)
        self.chaining_key = self.handshake_hash
        self.cipher_state = CipherState()

    def mix_hash(self, data: bytes) -> None:
        self.handshake_hash = hash(self.handshake_hash + data)

    def mix_key(self, input_key_material: bytes) -> None:
        self.chaining_key, temp_k = hkdf(self.chaining_key, input_key_material, 2)
        self.cipher_state = CipherState(temp_k[:HASHLEN])

    def mix_key_and_hash(self, input_key_material: bytes) -> None:
        self.chaining_key, temp_h, temp_k = hkdf(
            self.chaining_key, input_key_material, 3
        )
        self.mix_hash(temp_h)
        self.cipher_state = CipherState(temp_k[:HASHLEN])

    def encrypt_and_hash(self, plaintext: bytes) -> bytes:
        ciphertext = self.cipher_state.encrypt_with_ad(self.handshake_hash, plaintext)
        self.mix_hash(ciphertext)
        return ciphertext

    def decrypt_and_hash(self, ciphertext: bytes) -> bytes:
        plaintext = self.cipher_state.decrypt_with_ad(self.handshake_hash, ciphertext)
        self.mix_hash(ciphertext)
        return plaintext

    def split(self) -> tuple[CipherState, CipherState]:
        temp_k1, temp_k2 = hkdf(self.chaining_key, b"", 2)
        return CipherState(temp_k1[:HASHLEN]), CipherState(temp_k2[:HASHLEN])


@dataclass
class TransportState:
    send_cipher_state: CipherState
    receive_cipher_state: CipherState
    handshake_hash: bytes


class InitiatorXXPsk3:
    def __init__(self, static_private: PrivateKey, prologue: bytes, psk: bytes) -> None:
        self.state = InitiatorXXPsk3State.READY_FOR_REQUEST1
        self.symmetric_state = SymmetricState()
        self.static_private = static_private
        self.static_public = public_key(static_private)
        self.symmetric_state.mix_hash(prologue)
        self.psk = psk

        self.ephemeral_private: bytes | None = None
        self.remote_ephemeral_public: bytes | None = None
        self.remote_static_public: bytes | None = None
        self.transport_state: TransportState | None = None

    def get_transport_state(self) -> TransportState:
        if self.state is not InitiatorXXPsk3State.HANDSHAKE_COMPLETE:
            raise ValueError()
        assert self.transport_state is not None

        return self.transport_state

    def create_request1(self, payload: bytes = b"") -> bytes:
        logger.info("InitiatorXXPsk3.create_request1()")
        if self.state is not InitiatorXXPsk3State.READY_FOR_REQUEST1:
            raise ValueError()
        self.state = InitiatorXXPsk3State.WAITING_FOR_RESPONSE1

        logger.debug("e")
        self.ephemeral_private, ephemeral_public = generate_keypair()

        logger.debug("payload")
        self.symmetric_state.mix_hash(ephemeral_public)
        encrypted_payload = self.symmetric_state.encrypt_and_hash(payload)

        return ephemeral_public + encrypted_payload

    def handle_response1(self, message: bytes) -> bytes:
        logger.info("InitiatorXXPsk3.handle_response1()")
        if self.state is not InitiatorXXPsk3State.WAITING_FOR_RESPONSE1:
            raise ValueError()
        self.state = InitiatorXXPsk3State.READY_FOR_REQUEST2
        assert self.ephemeral_private is not None

        logger.debug("e")
        self.remote_ephemeral_public = message[:DHLEN]
        self.symmetric_state.mix_hash(self.remote_ephemeral_public)

        logger.debug("ee")
        self.symmetric_state.mix_key(
            dh(self.ephemeral_private, self.remote_ephemeral_public)
        )

        logger.debug("s")
        encrypted_remote_static_public = message[DHLEN : DHLEN + DHLEN + AEAD_TAG_LEN]
        self.remote_static_public = self.symmetric_state.decrypt_and_hash(
            encrypted_remote_static_public
        )

        logger.debug("es")
        self.symmetric_state.mix_key(
            dh(self.ephemeral_private, self.remote_static_public)
        )

        logger.debug("payload")
        encrypted_payload = message[DHLEN + DHLEN + AEAD_TAG_LEN :]
        payload = self.symmetric_state.decrypt_and_hash(encrypted_payload)

        return payload

    def create_request2(self, payload: bytes = b"") -> bytes:
        logger.info("InitiatorXXPsk3.create_request2()")
        if self.state is not InitiatorXXPsk3State.READY_FOR_REQUEST2:
            raise ValueError()
        self.state = InitiatorXXPsk3State.HANDSHAKE_COMPLETE
        assert self.remote_ephemeral_public is not None

        logger.debug("s")
        encrypted_static_public = self.symmetric_state.encrypt_and_hash(
            self.static_public
        )

        logger.debug("se")
        self.symmetric_state.mix_key(
            dh(self.static_private, self.remote_ephemeral_public)
        )

        logger.debug("psk")
        self.symmetric_state.mix_key_and_hash(self.psk)

        logger.debug("payload")
        encrypted_payload = self.symmetric_state.encrypt_and_hash(payload)

        c1, c2 = self.symmetric_state.split()
        self.transport_state = TransportState(
            send_cipher_state=c1,
            receive_cipher_state=c2,
            handshake_hash=self.symmetric_state.handshake_hash,
        )
        return encrypted_static_public + encrypted_payload


class ResponderXXPsk3:
    def __init__(self, static_private: PrivateKey, prologue: bytes, psk: bytes) -> None:
        self.state = ResponderXXPsk3State.WAITING_FOR_REQUEST1
        self.symmetric_state = SymmetricState()
        self.static_private = static_private
        self.static_public = public_key(static_private)
        self.symmetric_state.mix_hash(prologue)
        self.psk = psk

        self.ephemeral_private: bytes | None = None
        self.remote_ephemeral_public: bytes | None = None
        self.remote_static_public: bytes | None = None
        self.transport_state: TransportState | None = None

    def get_transport_state(self) -> TransportState:
        if self.state is not ResponderXXPsk3State.HANDSHAKE_COMPLETE:
            raise ValueError()
        assert self.transport_state is not None

        return self.transport_state

    def handle_request1(self, message: bytes) -> bytes:
        logger.info("ResponderXXPsk3.handle_request1()")
        if self.state is not ResponderXXPsk3State.WAITING_FOR_REQUEST1:
            raise ValueError()
        self.state = ResponderXXPsk3State.READY_FOR_RESPONSE1

        self.remote_ephemeral_public, encrypted_payload = (
            message[:DHLEN],
            message[DHLEN:],
        )

        logger.debug("e")
        self.symmetric_state.mix_hash(self.remote_ephemeral_public)

        logger.debug("payload")
        payload = self.symmetric_state.decrypt_and_hash(encrypted_payload)

        return payload

    def create_response1(self, payload: bytes = b"") -> bytes:
        logger.info("ResponderXXPsk3.create_response1()")
        if self.state is not ResponderXXPsk3State.READY_FOR_RESPONSE1:
            raise ValueError()
        self.state = ResponderXXPsk3State.WAITING_FOR_REQUEST2
        assert self.remote_ephemeral_public is not None

        logger.debug("e")
        self.ephemeral_private, ephemeral_public = generate_keypair()
        self.symmetric_state.mix_hash(ephemeral_public)

        logger.debug("ee")
        self.symmetric_state.mix_key(
            dh(self.ephemeral_private, self.remote_ephemeral_public)
        )

        logger.debug("s")
        encrypted_static_public = self.symmetric_state.encrypt_and_hash(
            self.static_public
        )

        logger.debug("se")
        self.symmetric_state.mix_key(
            dh(self.static_private, self.remote_ephemeral_public)
        )

        logger.debug("payload")
        encrypted_payload = self.symmetric_state.encrypt_and_hash(payload)

        return ephemeral_public + encrypted_static_public + encrypted_payload

    def handle_request2(self, message: bytes) -> bytes:
        logger.info("ResponderXXPsk3.handle_request2()")
        if self.state is not ResponderXXPsk3State.WAITING_FOR_REQUEST2:
            raise ValueError()
        self.state = ResponderXXPsk3State.HANDSHAKE_COMPLETE
        assert self.ephemeral_private is not None

        logger.debug("s")
        encrypted_remote_static_public = message[: DHLEN + AEAD_TAG_LEN]
        self.remote_static_public = self.symmetric_state.decrypt_and_hash(
            encrypted_remote_static_public
        )

        logger.debug("se")
        self.symmetric_state.mix_key(
            dh(self.ephemeral_private, self.remote_static_public)
        )

        logger.debug("psk")
        self.symmetric_state.mix_key_and_hash(self.psk)

        logger.debug("payload")
        encrypted_payload = message[DHLEN + AEAD_TAG_LEN :]
        payload = self.symmetric_state.decrypt_and_hash(encrypted_payload)

        c1, c2 = self.symmetric_state.split()
        self.transport_state = TransportState(
            send_cipher_state=c2,
            receive_cipher_state=c1,
            handshake_hash=self.symmetric_state.handshake_hash,
        )
        return payload
