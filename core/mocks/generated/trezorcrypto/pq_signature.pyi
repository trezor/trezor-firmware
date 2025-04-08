from typing import *
public_key_size: int
secret_key_size: int
signature_size: int


# upymod/modtrezorcrypto/modtrezorcrypto-pq_signature.h
def generate_keypair() -> Tuple[bytes, bytes]:


# upymod/modtrezorcrypto/modtrezorcrypto-pq_signature.h
def sign(
    secret_key: bytes,
    message: bytes
) -> bytes:


# upymod/modtrezorcrypto/modtrezorcrypto-pq_signature.h
def verify(public_key: bytes, signature: bytes, message: bytes) -> bool:
