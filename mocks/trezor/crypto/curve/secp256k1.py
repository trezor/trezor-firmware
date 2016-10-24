
# ../extmod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def generate_secret() -> bytes:
    '''
    Generate secret key.
    '''

# ../extmod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def publickey(secret_key: bytes, compressed: bool=True) -> bytes:
    '''
    Computes public key from secret key.
    '''

# ../extmod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def sign(secret_key: bytes, message: bytes) -> bytes:
    '''
    Uses secret key to produce the signature of message.
    '''

# ../extmod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def verify(public_key: bytes, signature: bytes, message: bytes) -> bool:
    '''
    Uses public key to verify the signature of the message
    Returns True on success.
    '''

# ../extmod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def multiply(secret_key: bytes, public_key: bytes) -> bytes:
    '''
    Multiplies point defined by public_key with scalar defined by secret_key
    Useful for ECDH
    '''
