from typing import *
from buffer_types import *


# upymod/modtrezorcrypto/modtrezorcrypto-sphincsplus.h
def derive_public_key(
    master_seed: AnyBytes, account_index: int, variant: int
) -> bytes:
    """
    Derive SPHINCS+ public key from master seed and account index.
    The secret key is computed in a stack-local buffer and zeroized
    before this function returns — it is never exposed to Python.
    Returns the public key bytes.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-sphincsplus.h
def derive_and_sign(
    master_seed: AnyBytes, account_index: int, variant: int, message: AnyBytes
) -> tuple[bytes, bytes]:
    """
    Derive a SPHINCS+ keypair, sign `message`, and return
    (public_key, signature). The secret key is computed in a stack-local
    buffer and zeroized before this function returns — it is never exposed
    to Python. A sign-then-verify check is performed internally to guard
    against fault-injection attacks; if verification fails, ValueError is
    raised and no signature is returned.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-sphincsplus.h
def verify(
    public_key: AnyBytes, signature: AnyBytes, message: AnyBytes, variant: int
) -> bool:
    """
    Verify a SPHINCS+ signature of `message` under `public_key`. `message`
    must already carry whatever domain wrapping the signer applied.
    """
