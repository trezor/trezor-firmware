"""Contact address attestation (pay-to-contact).

The receiver's Trezor signs an address that it derived and showed itself with
the contact identity key (the NIP-06 nostr key at m/44'/1237'/0'/0/0). The
payer's Trezor verifies that signature while it signs a transaction and looks
the identity up in WARD.

The signed message is a BIP-340 tagged hash, never a nostr event, so a
signature from NostrSignEvent can never pass as an address attestation.

This module must not import `apps.nostr`: the bitcoin app uses it, and nostr
is not part of every build.
"""

from micropython import const
from typing import TYPE_CHECKING

from apps.common.paths import HARDENED

if TYPE_CHECKING:
    from apps.common.paths import Bip32Path

# m/44'/1237'/0'/0/0, the NIP-06 nostr identity key (same as NostrGetPubkey)
IDENTITY_PATH = [44 | HARDENED, 1237 | HARDENED, HARDENED, 0, 0]
_IDENTITY_SLIP44 = const(1237)
_IDENTITY_CURVE = "secp256k1"

_TAG = b"trezor/contact-address/v1"
_MAX_ADDRESS_LEN = const(90)
# Only the first receive addresses of an account can be attested, so that an
# attested address is always found by the receiver's own wallet discovery.
_MAX_ADDRESS_INDEX = const(1000)


def is_attestable_address(address: str) -> bool:
    """Address charset accepted by both the producer and the verifier."""
    if not 1 <= len(address) <= _MAX_ADDRESS_LEN:
        return False
    for ch in address:
        if not ("0" <= ch <= "9" or "a" <= ch <= "z" or "A" <= ch <= "Z"):
            return False
    return True


def is_attestable_path(address_n: Bip32Path) -> bool:
    """A BIP-44-shaped receive path: purpose'/coin'/account'/0/index < 1000.

    Rejects change addresses, deeper (e.g. SLIP-25 coinjoin) and unhardened
    account paths. The caller still checks the path against the script type.
    """
    if len(address_n) != 5:
        return False
    for i in range(3):
        if not address_n[i] & HARDENED:
            return False
    return address_n[3] == 0 and address_n[4] < _MAX_ADDRESS_INDEX


def attestation_digest(slip44: int, address: str) -> bytes:
    """SHA256(SHA256(tag) || SHA256(tag) || u32_be(slip44) || utf8(address))."""
    from trezor.crypto.hashlib import sha256

    tag_digest = sha256(_TAG).digest()
    ctx = sha256(tag_digest)
    ctx.update(tag_digest)
    ctx.update(slip44.to_bytes(4, "big"))
    ctx.update(address.encode())
    return ctx.digest()


def encode_npub(pubkey: bytes) -> str:
    """bech32 `npub1...` (NIP-19) of a 32-byte x-only public key."""
    from trezor.crypto import bech32
    from trezor.wire import DataError

    if len(pubkey) != 32:
        raise DataError("Invalid contact pubkey")
    data = bech32.convertbits(pubkey, 8, 5)
    return bech32.bech32_encode("npub", data, bech32.Encoding.BECH32)


def verify_attestation(
    pubkey: bytes, signature: bytes, slip44: int, address: str
) -> bool:
    from trezor.crypto.curve import bip340

    if len(pubkey) != 32 or len(signature) != 64:
        return False
    if not is_attestable_address(address):
        return False
    return bip340.verify(pubkey, signature, attestation_digest(slip44, address))


async def sign_address(slip44: int, address: str) -> tuple[bytes, bytes]:
    """Sign an attestation of `address` with the identity key.

    Returns (signature, x-only pubkey). The caller must have derived and shown
    the address itself and obtained the user's consent.
    """
    from trezor.crypto.curve import bip340
    from trezor.wire import DataError

    from apps.common.keychain import get_keychain
    from apps.common.paths import PATTERN_BIP44, PathSchema

    if not is_attestable_address(address):
        raise DataError("Address cannot be attested")

    schema = PathSchema.parse(PATTERN_BIP44, _IDENTITY_SLIP44)
    keychain = await get_keychain(_IDENTITY_CURVE, [schema])
    with keychain:
        node = keychain.derive(IDENTITY_PATH)
        pubkey = node.public_key()[-32:]
        signature = bip340.sign(node.private_key(), attestation_digest(slip44, address))
    return signature, pubkey
