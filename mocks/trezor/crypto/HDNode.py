
# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def derive(index: int) -> None:
    '''
    Derive a BIP0032 child node in place.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def derive_path(path: list) -> None:
    '''
    Go through a list of indexes and iteratively derive a child node in place.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def serialize_public(version: int) -> str:
    '''
    Serialize the public info from HD node to base58 string.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def serialize_private(version: int) -> str:
    '''
    Serialize the private info HD node to base58 string.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def clone() -> HDNode:
    '''
    Returns a copy of the HD node.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def depth() -> int:
    '''
    Returns a depth of the HD node.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def fingerprint() -> int:
    '''
    Returns a fingerprint of the HD node (hash of the parent public key).
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def child_num() -> int:
    '''
    Returns a child index of the HD node.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def chain_code() -> bytes:
    '''
    Returns a chain code of the HD node.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def private_key() -> bytes:
    '''
    Returns a private key of the HD node.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def public_key() -> bytes:
    '''
    Returns a public key of the HD node.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def address(version: int) -> str:
    '''
    Compute a base58-encoded address string from the HD node.
    '''
