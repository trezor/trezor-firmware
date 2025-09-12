from typing import *
from buffer_types import *


# upymod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def generate_secret() -> bytes:
    """
    Generate secret key.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def publickey(secret_key: AnyBytes) -> bytes:
    """
    Computes public key from secret key.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def sign(secret_key: AnyBytes, message: AnyBytes, hasher: str = "") -> bytes:
    """
    Uses secret key to produce the signature of message.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def sign_ext(
    secret_scalar: AnyBytes, secret_extension: AnyBytes, message: AnyBytes
) -> bytes:
    """
    Uses extended secret key to produce the cardano signature of message.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def verify(public_key: AnyBytes, signature: AnyBytes, message: AnyBytes) -> bool:
    """
    Uses public key to verify the signature of the message.
    Returns True on success.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def cosi_combine_publickeys(public_keys: Sequence[AnyBytes]) -> bytes:
    """
    Combines a list of public keys used in COSI cosigning scheme.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def cosi_combine_signatures(R: AnyBytes, signatures: Sequence[AnyBytes]) -> bytes:
    """
    Combines a list of signatures used in COSI cosigning scheme.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def cosi_commit() -> tuple[bytes, bytes]:
    """
    Generate a nonce and commitment for the CoSi cosigning scheme.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def cosi_sign(
    secret_key: AnyBytes,
    message: AnyBytes,
    nonce: AnyBytes,
    sigR: AnyBytes,
    combined_pubkey: AnyBytes,
) -> bytes:
    """
    Produce signature of message using COSI cosigning scheme.
    """
