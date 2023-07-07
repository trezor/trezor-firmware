from typing import *
def generate_secret() -> bytes:
    """
    Generate secret key.
    """
def publickey(secret_key: bytes) -> bytes:
    """
    Computes public key from secret key.
    """
def sign(secret_key: bytes, message: bytes, hasher: str = "") -> bytes:
    """
    Uses secret key to produce the signature of message.
    """
def sign_ext(
    secret_key: bytes, secret_extension: bytes, message: bytes
) -> bytes:
    """
    Uses secret key to produce the cardano signature of message.
    """
def verify(public_key: bytes, signature: bytes, message: bytes) -> bool:
    """
    Uses public key to verify the signature of the message.
    Returns True on success.
    """
def cosi_combine_publickeys(public_keys: list[bytes]) -> bytes:
    """
    Combines a list of public keys used in COSI cosigning scheme.
    """
def cosi_combine_signatures(R: bytes, signatures: list[bytes]) -> bytes:
    """
    Combines a list of signatures used in COSI cosigning scheme.
    """
def cosi_commit() -> tuple[bytes, bytes]:
    """
    Generate a nonce and commitment for the CoSi cosigning scheme.
    """
def cosi_sign(
    secret_key: bytes,
    message: bytes,
    nonce: bytes,
    sigR: bytes,
    combined_pubkey: bytes,
) -> bytes:
    """
    Produce signature of message using COSI cosigning scheme.
    """
