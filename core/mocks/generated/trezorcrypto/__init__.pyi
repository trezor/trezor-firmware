from typing import *
from buffer_types import *


# upymod/modtrezorcrypto/modtrezorcrypto-aes.h
class aes:
    """
    AES context.
    """
    ECB: int
    CBC: int
    CFB: int
    OFB: int
    CTR: int

    def __init__(
        self,
        mode: int,
        key: AnyBytes,
        iv: AnyBytes | None = None,
    ) -> None:
        """
        Initialize AES context.
        """

    def encrypt(self, data: AnyBytes) -> bytes:
        """
        Encrypt data and update AES context.
        """

    def decrypt(self, data: AnyBytes) -> bytes:
        """
        Decrypt data and update AES context.
        """


# upymod/modtrezorcrypto/modtrezorcrypto-aesgcm.h
class aesgcm_encrypt:
    """
    AES-GCM context for encryption.
    """

    def __init__(self, key: AnyBytes, iv: AnyBytes) -> None:
        """
        Initialize the AES-GCM context for encryption.
        """

    def auth(self, data: AnyBytes) -> None:
        """
        Include authenticated data chunk in the GCM authentication tag. This can
        be called repeatedly to add authenticated data at any point before
        finish().
        """

    def reset(self, iv: AnyBytes) -> None:
        """
        Reset the IV for encryption.
        """

    def encrypt(self, data: AnyBytes) -> bytes:
        """
        Encrypt data chunk.
        """

    def encrypt_in_place(self, data: AnyBuffer) -> int:
        """
        Encrypt data chunk in place. Returns the length of the encrypted data.
        """

    def finish(self) -> bytes:
        """
        Compute the GCM authentication tag.
        """


# upymod/modtrezorcrypto/modtrezorcrypto-aesgcm.h
class aesgcm_decrypt:
    """
    AES-GCM context for decryption.
    """

    def __init__(self, key: AnyBytes, iv: AnyBytes) -> None:
        """
        Initialize the AES-GCM context for decryption.
        """

    def auth(self, data: AnyBytes) -> None:
        """
        Include authenticated data chunk in the GCM authentication tag. This can
        be called repeatedly to add authenticated data at any point before
        finish().
        """

    def reset(self, iv: AnyBytes) -> None:
        """
        Reset the IV for decryption.
        """

    def decrypt(self, data: AnyBytes) -> bytes:
        """
        Decrypt data chunk.
        """

    def decrypt_in_place(self, data: AnyBuffer) -> int:
        """
        Decrypt data chunk in place. Returns the length of the decrypted data.
        """

    def finish(self, expected_tag: AnyBytes) -> None:
        """
        Verify the GCM authentication tag.
        """


# upymod/modtrezorcrypto/modtrezorcrypto-blake256.h
class blake256:
    """
    Blake256 context.
    """
    block_size: int
    digest_size: int

    def __init__(self, __data: StrOrBytes | None = None) -> None:
        """
        Creates a hash context object.
        """

    def update(self, __data: StrOrBytes) -> None:
        """
        Update the hash context with hashed data.
        """

    def digest(self) -> bytes:
        """
        Returns the digest of hashed data.
        """


# upymod/modtrezorcrypto/modtrezorcrypto-blake2b.h
class blake2b:
    """
    Blake2b context.
    """
    block_size: int
    digest_size: int

    def __init__(
        self,
        data: AnyBytes | None = None,
        outlen: int = blake2b.digest_size,
        key: AnyBytes | None = None,
        personal: AnyBytes | None = None,
    ) -> None:
        """
        Creates a hash context object.
        """

    def update(self, __data: StrOrBytes) -> None:
        """
        Update the hash context with hashed data.
        """

    def digest(self) -> bytes:
        """
        Returns the digest of hashed data.
        """


# upymod/modtrezorcrypto/modtrezorcrypto-blake2s.h
class blake2s:
    """
    Blake2s context.
    """
    block_size: int
    digest_size: int

    def __init__(
        self,
        data: AnyBytes | None = None,
        outlen: int = blake2s.digest_size,
        key: AnyBytes | None = None,
        personal: AnyBytes | None = None,
    ) -> None:
        """
        Creates a hash context object.
        """

    def update(self, __data: StrOrBytes) -> None:
        """
        Update the hash context with hashed data.
        """

    def digest(self) -> bytes:
        """
        Returns the digest of hashed data.
        """


# upymod/modtrezorcrypto/modtrezorcrypto-chacha20poly1305.h
class chacha20poly1305_encrypt:
    """
    ChaCha20Poly1305 context for encryption.
    """
    key_size: int
    nonce_size: int
    block_size: int
    tag_size: int

    def __init__(self, key: AnyBytes, nonce: AnyBytes) -> None:
        """
        Initialize the ChaCha20 + Poly1305 context for encryption
        using a 32 byte key and 12 byte nonce as in the RFC 7539 style.
        """

    def auth(self, data: AnyBytes) -> None:
        """
        Include authenticated data in the Poly1305 MAC using the RFC 7539
        style with 16 byte padding. This must only be called once and prior
        to encryption.
        """

    def encrypt(self, data: AnyBytes) -> bytes:
        """
        Encrypt data (length of data must be divisible by 64 except for the
        final value).
        """

    def finish(self) -> bytes:
        """
        Compute RFC 7539-style Poly1305 MAC.
        """


# upymod/modtrezorcrypto/modtrezorcrypto-chacha20poly1305.h
class chacha20poly1305_decrypt:
    """
    ChaCha20Poly1305 context for decryption.
    """
    key_size: int
    nonce_size: int
    block_size: int
    tag_size: int

    def __init__(self, key: AnyBytes, nonce: AnyBytes) -> None:
        """
        Initialize the ChaCha20 + Poly1305 context for decryption
        using a 32 byte key and 12 byte nonce as in the RFC 7539 style.
        """

    def auth(self, data: AnyBytes) -> None:
        """
        Include authenticated data in the Poly1305 MAC using the RFC 7539
        style with 16 byte padding. This must only be called once and prior
        to decryption.
        """

    def decrypt(self, data: AnyBytes) -> bytes:
        """
        Decrypt data (length of data must be divisible by 64 except for the
        final value).
        """

    def finish(self, expected_mac: AnyBytes) -> None:
        """
        Verify RFC 7539-style Poly1305 MAC.
        """


# upymod/modtrezorcrypto/modtrezorcrypto-common.h
class AuthenticationError(Exception):
    """
    Authentication failed.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-groestl.h
class groestl512:
    """
    GROESTL512 context.
    """
    block_size: int
    digest_size: int

    def __init__(self, __data: StrOrBytes | None = None) -> None:
        """
        Creates a hash context object.
        """

    def update(self, __data: StrOrBytes) -> None:
        """
        Update the hash context with hashed data.
        """

    def digest(self) -> bytes:
        """
        Returns the digest of hashed data.
        """


# upymod/modtrezorcrypto/modtrezorcrypto-hmac.h
class hmac:
    """
    HMAC context.
    """
    SHA256: int
    SHA512: int

    def __init__(
        self,
        hashtype: int,
        key: AnyBytes,
        message: AnyBytes | None = None,
    ) -> None:
        """
        Create a HMAC context.
        """

    def update(self, message: AnyBytes) -> None:
        """
        Update a HMAC context.
        """

    def digest(self) -> bytes:
        """
        Return the digest of processed data so far.
        """

    @staticmethod
    def tag(hashtype: int, key: secbytes, message: AnyBytes) -> bytes:
        """Compute a public authentication tag in the kernel. Message is limited
        to 256 bytes. For public MACs only; not a secret-output KDF
        interface."""


# upymod/modtrezorcrypto/modtrezorcrypto-pbkdf2.h
class pbkdf2:
    """
    PBKDF2 context.
    """
    HMAC_SHA256: int
    HMAC_SHA512: int

    def __init__(
        self,
        prf: int,
        password: AnyBytes,
        salt: AnyBytes,
        iterations: int | None = None,
        blocknr: int = 1,
    ) -> None:
        """
        Create a PBKDF2 context.
        """

    def update(self, iterations: int) -> None:
        """
        Update a PBKDF2 context.
        """

    def key(self) -> bytes:
        """
        Retrieve derived key.
        """


# upymod/modtrezorcrypto/modtrezorcrypto-ripemd160.h
class ripemd160:
    """
    RIPEMD160 context.
    """
    block_size: int
    digest_size: int

    def __init__(self, __data: StrOrBytes | None = None) -> None:
        """
        Creates a hash context object.
        """

    def update(self, __data: StrOrBytes) -> None:
        """
        Update the hash context with hashed data.
        """

    def digest(self) -> bytes:
        """
        Returns the digest of hashed data.
        """


# upymod/modtrezorcrypto/modtrezorcrypto-secbytes.h
class secbytes:
    """Opaque immutable native secret. No buffer or plaintext interface.
    Every value has a key type, which decides what the vault may do with
    it."""
    SEED: int
    SLIP21_NODE: int
    SYMMETRIC: int
    SECP256K1: int
    NIST256P1: int
    ED25519_SEED: int
    X25519: int
    THP_DEVICE: int
    CARDANO_SECRET: int

    def __init__(self, value: AnyBytes | None, arg: int = ...) -> None:
        """Copy existing plaintext; this does not erase its Python source.
        arg is its key type, SYMMETRIC by default. None makes an empty
        holder for a long-lived slot, see take(); arg then limits its
        capacity, 160 by default, and populated values use their actual
        size."""

    def destroy(self) -> None:
        """Erase this value. Idempotent."""

    def take(self, other: secbytes) -> None:
        """Erase this value, then move other's secret into this object, leaving
        other empty. Lets long-lived holders change value without allocating.
        An oversized move raises ValueError and leaves both values unchanged;
        populated objects have capacity equal to their initial secret length."""

    def empty(self) -> bool:
        """Return whether this object holds no secret (local check only)."""


# upymod/modtrezorcrypto/modtrezorcrypto-secbytes.h
def authorize_locked_session(authorized: bool) -> None:
    """Grant/revoke the current session's confirmed CoinJoin permission.
    Granting requires unlocked storage and a live request."""


# upymod/modtrezorcrypto/modtrezorcrypto-secbytes.h
def begin_preauthorized_request() -> None:
    """Delegate a confirmed CoinJoin session grant to this request. It
    survives consuming the last round until this request is torn down."""


# upymod/modtrezorcrypto/modtrezorcrypto-secbytes.h
def begin_confirmed_request() -> None:
    """Allow this confirmed request's crypto to finish after autolock.
    A new grant requires unlocked storage and does not authorize a
    session."""


# upymod/modtrezorcrypto/modtrezorcrypto-secbytes.h
def revoke_secrets() -> None:
    """Erase all native owners and entries; emergency teardown only."""


# upymod/modtrezorcrypto/modtrezorcrypto-secbytes.h
def slip21_derive(
    source: secbytes,
    path: Sequence[AnyBytes],
    root: bool = False,
    key: bool = False,
) -> secbytes:
    """SLIP-0021 in the vault: derive from a seed (root) or a 64-byte node
    along path. Return the sealed node or, with key, its sealed key."""


# upymod/modtrezorcrypto/modtrezorcrypto-secbytes.h
def slip21_export(seed: secbytes, path: Sequence[AnyBytes]) -> bytes:
    """Return a SLIP-0021 node in plaintext, for protocols that hand it to
    the host. The kernel allows only the Evolu namespace."""


# upymod/modtrezorcrypto/modtrezorcrypto-secbytes.h
class SecretOwner:
    """Explicit native session owner, or request owner beneath a session."""

    def __init__(
        self, parent: SecretOwner | None = None, bound: bool = True
    ) -> None:
        """Allocate a bounded, generation-checked owner identity. With
        bound=False, make an unbound holder for a long-lived slot, see renew().
        """

    def destroy(self) -> None:
        """Erase this owner and its descendants without allocating."""

    def renew(self, parent: SecretOwner | None = None) -> None:
        """Erase the current identity and bind a fresh one in place, so a
        long-lived holder never needs a new heap object."""

    def valid(self) -> bool:
        """Return whether this owner is still live."""


# upymod/modtrezorcrypto/modtrezorcrypto-secbytes.h
def _secret_owner_activate(owner: SecretOwner | None) -> None:
    """Scheduler hook; None disables secret operations. Lifetime only, not
    isolation."""


# upymod/modtrezorcrypto/modtrezorcrypto-secret-lifecycle.h
def _secret_task_register(task: Any, owner: SecretOwner | None) -> None:
    """Bind a request root, or inherit the active request for a child."""


# upymod/modtrezorcrypto/modtrezorcrypto-secret-lifecycle.h
def _secret_task_rebind(task: Any, owner: SecretOwner) -> None:
    """Start a fresh request after an explicit storage reset. Existing
    bindings may be replaced only after their old owner was revoked."""


# upymod/modtrezorcrypto/modtrezorcrypto-secret-lifecycle.h
def _secret_task_enter(task: Any) -> bool:
    """Activate task ownership. False means the task has been revoked."""


# upymod/modtrezorcrypto/modtrezorcrypto-secret-lifecycle.h
def _secret_task_finish(task: Any) -> None:
    """Revoke roots before callbacks; children release only their
    binding."""


# upymod/modtrezorcrypto/modtrezorcrypto-secret-lifecycle.h
def _secret_tasks_clear() -> None:
    """Erase request owners and forget tasks, preserving sessions."""


# upymod/modtrezorcrypto/modtrezorcrypto-sha256.h
class sha256:
    """
    SHA256 context.
    """
    block_size: int
    digest_size: int

    def __init__(self, __data: StrOrBytes | None = None) -> None:
        """
        Creates a hash context object.
        """

    def update(self, __data: StrOrBytes) -> None:
        """
        Update the hash context with hashed data.
        """

    def digest(self) -> bytes:
        """
        Returns the digest of hashed data.
        """


# upymod/modtrezorcrypto/modtrezorcrypto-sha3-256.h
class sha3_256:
    """
    SHA3_256 context.
    """
    block_size: int
    digest_size: int

    def __init__(
        self,
        data: AnyBytes | None = None,
        keccak: bool = False,
    ) -> None:
        """
        Creates a hash context object.
        """

    def update(self, __data: StrOrBytes) -> None:
        """
        Update the hash context with hashed data.
        """

    def digest(self) -> bytes:
        """
        Returns the digest of hashed data.
        """

    def copy(self) -> sha3_256:
        """
        Returns the copy of the digest object with the current state
        """


# upymod/modtrezorcrypto/modtrezorcrypto-sha3-512.h
class sha3_512:
    """
    SHA3_512 context.
    """
    block_size: int
    digest_size: int

    def __init__(
        self,
        data: AnyBytes | None = None,
        keccak: bool = False,
    ) -> None:
        """
        Creates a hash context object.
        """

    def update(self, __data: StrOrBytes) -> None:
        """
        Update the hash context with hashed data.
        """

    def digest(self) -> bytes:
        """
        Returns the digest of hashed data.
        """

    def copy(self) -> sha3_512:
        """
        Returns the copy of the digest object with the current state
        """


# upymod/modtrezorcrypto/modtrezorcrypto-sha512.h
class sha512:
    """
    SHA512 context.
    """
    block_size: int
    digest_size: int

    def __init__(self, __data: StrOrBytes | None = None) -> None:
        """
        Creates a hash context object.
        """

    def update(self, __data: StrOrBytes) -> None:
        """
        Update the hash context with hashed data.
        """

    def digest(self) -> bytes:
        """
        Returns the digest of hashed data.
        """


# upymod/modtrezorcrypto/modtrezorcrypto.c
def retain_secret(value: Any, owner: SecretOwner | None = None) -> None:
    """Explicitly transfer a node or snapshot from this request to its
    session, optionally requiring that exact cache owner."""


# upymod/modtrezorcrypto/modtrezorcrypto.c
def vault_chacha(
    key: secbytes, nonce: AnyBytes, data: AnyBytes,
    aad: AnyBytes = b"", tag: AnyBytes | None = None,
    decrypt: bool = False,
) -> tuple[bytes, bytes]:
    """Encrypt/decrypt public credential data with an opaque key.
    With decrypt=True and tag=None the result is unauthenticated metadata;
    callers must authenticate before using it as a credential."""
from trezorcrypto.bip32 import HDNode


# upymod/modtrezorcrypto/modtrezorcrypto.c
def cipher_key_value(
    node: HDNode, label: AnyBytes, value: AnyBytes, encrypt: bool,
    ask_on_encrypt: bool, ask_on_decrypt: bool, iv: AnyBytes = b"",
) -> bytes:
    """SLIP-0011 key derivation and AES-CBC with a protected HDNode."""
