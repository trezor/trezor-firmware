
# ../extmod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def generate_secret() -> bytes:
    '''
    Generate secret key.
    '''

# ../extmod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def publickey(secret_key: bytes) -> bytes:
    '''
    Computes public key from secret key.
    '''

# ../extmod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def sign(secret_key: bytes, message: bytes) -> bytes:
    '''
    Uses secret key to produce the signature of message.
    '''

# ../extmod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def verify(public_key: bytes, signature: bytes, message: bytes) -> bool:
    '''
    Uses public key to verify the signature of the message.
    Returns True on success.
    '''
