from typing import *
from buffer_types import *


# upymod/modtrezorcrypto/modtrezorcrypto-pallas.h
def hd_account(seed: AnyBytes, account: int) -> bytes:
    """
    Derive the DarkFi account spend key sk = HD_account(seed, account)
    using DarkFi's own hierarchical-deterministic scheme (crypto/hd.rs):
    the hardened child at `account` of the master node derived from `seed`.
    `seed` is the raw BIP-39 seed (any length). Returns sk as 32
    little-endian bytes. Matches darkfi_sdk ExtendedSecretKey::account, so
    the same mnemonic restores identically in the drk wallet.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-pallas.h
def derive_ask(sk: AnyBytes) -> bytes:
    """
    Derive the spend-auth secret ask = ToScalar(Expand(sk, 0x06)).
    Returns a 32-byte little-endian scalar. Device-only secret.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-pallas.h
def derive_nk(sk: AnyBytes) -> bytes:
    """
    Derive the nullifier key nk = ToBase(Expand(sk, 0x07)).
    Returns a 32-byte little-endian base-field element. Part of the FVK.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-pallas.h
def spend_auth_pubkey(ask: AnyBytes) -> bytes:
    """
    Compute ak = ask * NullifierK, the spend-auth public key, as a 32-byte
    compressed Pallas point (DarkFi GroupEncoding).
    """


# upymod/modtrezorcrypto/modtrezorcrypto-pallas.h
def derive_ivk(sk: AnyBytes) -> bytes:
    """
    Derive ivk = poseidon([ak_x, ak_y, nk]) from the spend key, kept as a
    base-field element (a stock SecretKey). Returns 32 little-endian bytes
    (the incoming view key).
    """


# upymod/modtrezorcrypto/modtrezorcrypto-pallas.h
def address_pubkey(ivk: AnyBytes) -> bytes:
    """
    Compute the transmission key pk_d = ivk * NullifierK, as a 32-byte
    compressed Pallas point. `ivk` is a 32-byte little-endian scalar.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-pallas.h
def nullifier(nk: AnyBytes, coin: AnyBytes) -> bytes:
    """
    Compute the nullifier nf = poseidon([nk, coin]). All values are 32-byte
    little-endian base-field elements.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-pallas.h
def poseidon_hash2(a: AnyBytes, b: AnyBytes) -> bytes:
    """
    Poseidon P128Pow5T3 hash of two field elements: poseidon([a, b]).
    All values are 32-byte little-endian base-field elements.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-pallas.h
def poseidon_hash3(a: AnyBytes, b: AnyBytes, c: AnyBytes) -> bytes:
    """
    Poseidon P128Pow5T3 hash of three field elements: poseidon([a, b, c]).
    All values are 32-byte little-endian base-field elements.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-pallas.h
def sign_spend_auth(
    ask: AnyBytes,
    alpha: AnyBytes,
    message: AnyBytes,
) -> tuple[bytes, bytes, bytes]:
    """
    Produce a randomized Schnorr spend-authorization signature.

    Returns (commit, rk, response): commit and rk are 32-byte compressed
    Pallas points, response is a 32-byte little-endian scalar. The signature
    verifies against rk = (ask + alpha) * NullifierK by the stock DarkFi
    Schnorr verifier.
    """
