
# ../extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def publickey(secret_key: bytes, compressed: bool=True) -> bytes:
    '''
    Computes public key from secret key.
    '''

# ../extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def sign(secret_key: bytes, message: bytes) -> bytes:
    '''
    Uses secret key to produce the signature of message.
    '''

# ../extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def verify(public_key: bytes, signature: bytes, message: bytes) -> bool:
    '''
    Uses public key to verify the signature of the message
    Returns True on success.
    '''
