"""Get CKB SPHINCS+ post-quantum address."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.messages import CKBSphincsPlusAddress, CKBSphincsPlusGetAddress


# Multisig configuration header [S, R, M, N] of the CKB all-in-one
# quantum-resistant lock script, in its documented single-sig form `80 01 01 01`.
# Hashed into lock_args; the witness must carry the same bytes (the on-chain
# script rehashes them), and hosts must use them to derive matching addresses.
_MULTISIG_HEADER = bytes([0x80, 0x01, 0x01, 0x01])

# Deployed code hashes of the CKB SPHINCS+ on-chain lock script.
_CODE_HASH_MAINNET = (
    b"\x30\x2d\x35\x98\x2f\x86\x5e\xbc"
    b"\xbe\xdb\x9a\x93\x60\xe4\x05\x30"
    b"\xed\x32\xad\xb8\xe1\x0b\x42\xfb"
    b"\xbe\x70\xd8\x31\x2f\xf7\xce\xdf"
)
_CODE_HASH_TESTNET = (
    b"\x14\x7e\xcb\xb5\xc5\x12\x7d\x98"
    b"\x2e\xe1\x36\x2d\x2c\x2b\xb4\x26"
    b"\x78\x03\xda\x2e\xb0\x06\xd1\x50"
    b"\xe8\x8a\xf6\xca\xaa\x0a\x7e\xaf"
)

# Hash type byte for the CKB full address payload: mainnet "type" = 0x01,
# testnet "data1" = 0x02.
_HASH_TYPE_MAINNET = 0x01
_HASH_TYPE_TESTNET = 0x02

# Valid SPHINCS+ variant IDs (matching ParamId in ckb-fips205-utils).
_VALID_VARIANTS = (48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59)

# Upper bound for account_index: keeps the HKDF info string within the C-side
# 64-byte buffer and the derivation path enumerable.
_MAX_ACCOUNT_INDEX = 1_000_000

# Canonical variant-to-N (security parameter) mapping, shared with
# sign_sphincs_tx to avoid divergent tables. Rows group the variants by N.
# fmt: off
_VARIANT_SPX_N: dict[int, int] = {
    48: 16, 49: 16, 54: 16, 55: 16,
    50: 24, 51: 24, 56: 24, 57: 24,
    52: 32, 53: 32, 58: 32, 59: 32,
}


# Mirrors the table in crypto/sphincsplus_dispatch.c. Rows are the SHA2 and the
# SHAKE half of the table, in variant order.
_VARIANT_SIG_BYTES: dict[int, int] = {
    48: 17088, 49: 7856, 50: 35664, 51: 16224, 52: 49856, 53: 29792,
    54: 17088, 55: 7856, 56: 35664, 57: 16224, 58: 49856, 59: 29792,
}
# fmt: on


def _variant_spx_n(variant: int) -> int:
    """Return the SPHINCS+ security parameter N for a given variant ID."""
    from trezor.wire import DataError

    n = _VARIANT_SPX_N.get(variant)
    if n is None:
        raise DataError("Unsupported SPHINCS+ variant")
    return n


def _split_extended_mnemonic_to_seed(mnemonic_bytes: bytes) -> bytearray:
    """Convert an extended BIP-39 mnemonic into 3*n bytes of raw entropy.

    SPHINCS+ keygen needs 3*n bytes (n = 16/24/32). Only 36/54/72-word extended
    mnemonics carry that much; standard mnemonics are rejected with a clear
    message. Returns a mutable bytearray so the caller can wipe it after use.
    """
    from trezor.crypto import bip39
    from trezor.utils import consteq
    from trezor.wire import DataError

    # Decoding to str would scatter unwipeable copies of the mnemonic.
    words = mnemonic_bytes.split(b" ")
    word_count = len(words)
    if word_count not in (36, 54, 72):
        raise DataError("SPHINCS+ requires an extended mnemonic (36, 54 or 72 words)")

    sub_len = word_count // 3
    entropy_per_sub = (sub_len // 3) * 4
    seed = bytearray()
    for i in range(3):
        sub_phrase = b" ".join(words[i * sub_len : (i + 1) * sub_len])
        seed.extend(bip39.mnemonic_to_bits(sub_phrase)[:entropy_per_sub])

    # Nothing else catches a mnemonic that repeats a sub-phrase.
    part_1 = seed[0:entropy_per_sub]
    part_2 = seed[entropy_per_sub : 2 * entropy_per_sub]
    part_3 = seed[2 * entropy_per_sub :]
    # consteq and |, not == and or: must not branch on secret contents.
    degenerate = (
        consteq(part_1, part_2) | consteq(part_1, part_3) | consteq(part_2, part_3)
    )
    _wipe(part_1)
    _wipe(part_2)
    _wipe(part_3)
    if degenerate:
        _wipe(seed)
        raise DataError(
            "Unsafe SPHINCS+ mnemonic: the three sub-phrases must all differ"
        )
    return seed


def _compute_lock_args(public_key: "AnyBytes", variant: int) -> bytes:
    """Compute the 32-byte CKB lock_args from a SPHINCS+ public key.

    Per the lock script's multisig configuration hashing:
        blake2b_256(personal="ckb-sphincs+-sct",
                    data=[0x80, 0x01, 0x01, 0x01, variant << 1] || public_key)
    """
    from trezor.crypto.hashlib import blake2b

    sign_flag = (variant << 1) & 0xFF
    h = blake2b(outlen=32, personal=b"ckb-sphincs+-sct")
    h.update(_MULTISIG_HEADER + bytes([sign_flag]))
    h.update(public_key)
    return h.digest()


def _require_sphincs_mnemonic(variant: int) -> bytearray:
    """Validate the device backup and return the 3*n raw-entropy seed.

    Enforces the SPHINCS+ preconditions shared by every handler: BIP-39 extended
    mnemonic, no passphrase, and a strength matching the requested variant.
    """
    import storage.device as storage_device
    from trezor.wire import DataError

    from apps.common import mnemonic

    # The HKDF derivation reads the mnemonic via get_secret(), bypassing the
    # BIP-39 PBKDF2 passphrase mixing. Until the passphrase is folded into the
    # derivation on both device and host, a passphrase would silently yield the
    # same keys as none, breaking the hidden-wallet guarantee.
    if storage_device.is_passphrase_enabled():
        raise DataError(
            "SPHINCS+ does not yet support BIP-39 passphrase. "
            "Disable passphrase protection to use SPHINCS+."
        )

    # SLIP-39 stores a binary EMS, not words; reject before .decode().
    if not mnemonic.is_bip39():
        raise DataError(
            "SPHINCS+ requires a BIP-39 extended mnemonic (36, 54 or 72 words)."
        )

    mnemonic_secret = mnemonic.get_secret()
    if mnemonic_secret is None:
        raise DataError("Device not initialized")

    seed = _split_extended_mnemonic_to_seed(mnemonic_secret)
    if len(seed) != 3 * _variant_spx_n(variant):
        raise DataError("SPHINCS+ variant does not match the stored mnemonic strength")
    return seed


def _wipe(buf: bytearray) -> None:
    """Zero a mutable buffer in place."""
    for i in range(len(buf)):
        buf[i] = 0


def _address_from_pubkey(public_key: "AnyBytes", variant: int, network: str) -> str:
    """Derive the CKB SPHINCS+ full (Bech32m) address from a public key."""
    from .helpers import encode_address_full

    lock_args = _compute_lock_args(public_key, variant)
    if network == "Mainnet":
        code_hash, hash_type = _CODE_HASH_MAINNET, _HASH_TYPE_MAINNET
    else:
        code_hash, hash_type = _CODE_HASH_TESTNET, _HASH_TYPE_TESTNET
    return encode_address_full(code_hash, hash_type, lock_args, network)


async def get_sphincs_address(
    msg: "CKBSphincsPlusGetAddress",
) -> "CKBSphincsPlusAddress":
    from trezor import TR
    from trezor.crypto import sphincsplus
    from trezor.messages import CKBSphincsPlusAddress
    from trezor.ui.layouts import show_address
    from trezor.wire import DataError

    from .helpers import encode_address_full

    variant = msg.variant if msg.variant is not None else 49
    if variant not in _VALID_VARIANTS:
        raise DataError("Invalid SPHINCS+ variant")
    if msg.network not in ("Mainnet", "Testnet"):
        raise DataError("Invalid CKB network")

    account_index = msg.account_index if msg.account_index is not None else 0
    if account_index < 0 or account_index > _MAX_ACCOUNT_INDEX:
        raise DataError("Invalid SPHINCS+ account index")

    seed = _require_sphincs_mnemonic(variant)
    try:
        # The secret key never leaves C: it is computed in a stack-local buffer
        # and zeroized inside derive_public_key.
        public_key = sphincsplus.derive_public_key(seed, account_index, variant)
        lock_args = _compute_lock_args(public_key, variant)
    finally:
        _wipe(seed)

    if msg.network == "Mainnet":
        code_hash = _CODE_HASH_MAINNET
        hash_type = _HASH_TYPE_MAINNET
    else:
        code_hash = _CODE_HASH_TESTNET
        hash_type = _HASH_TYPE_TESTNET

    address = encode_address_full(code_hash, hash_type, lock_args, msg.network)

    # Silent when show_display is unset, matching get_address and every other
    # address handler: the public key and the address it encodes are not secret,
    # so a host may read them to build a transaction without prompting.
    if msg.show_display:
        await show_address(
            address,
            subtitle=TR.address__coin_address_template.format("CKB SPHINCS+"),
            path=f"QP/{account_index}/v{variant}",
            chunkify=bool(msg.chunkify),
        )

    return CKBSphincsPlusAddress(
        address=address,
        lock_args=lock_args,
        public_key=public_key,
        variant=variant,
    )
