
# extmod/modtrezorcrypto/modtrezorcrypto-aes.h
class AES:
    '''
    AES context.
    '''

    def __init__(self, mode: int, key: bytes, iv: bytes = None) -> None:
        '''
        Initialize AES context.
        '''

    def encrypt(self, data: bytes) -> bytes:
        '''
        Encrypt data and update AES context.
        '''

    def decrypt(self, data: bytes) -> bytes:
        '''
        Decrypt data and update AES context.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-blake256.h
class Blake256:
    '''
    Blake256 context.
    '''

    def __init__(self, data: bytes = None) -> None:
        '''
        Creates a hash context object.
        '''

    def update(self, data: bytes) -> None:
        '''
        Update the hash context with hashed data.
        '''

    def digest(self) -> bytes:
        '''
        Returns the digest of hashed data.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-blake2b.h
class Blake2b:
    '''
    Blake2b context.
    '''

    def __init__(self, data: bytes = None, outlen: int = Blake2b.digest_size, personal: bytes = None) -> None:
        '''
        Creates a hash context object.
        '''

    def update(self, data: bytes) -> None:
        '''
        Update the hash context with hashed data.
        '''

    def digest(self) -> bytes:
        '''
        Returns the digest of hashed data.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-blake2s.h
class Blake2s:
    '''
    Blake2s context.
    '''

    def __init__(self, data: bytes = None, outlen: int = Blake2s.digest_size, key: bytes = None, personal: bytes = None) -> None:
        '''
        Creates a hash context object.
        '''

    def update(self, data: bytes) -> None:
        '''
        Update the hash context with hashed data.
        '''

    def digest(self) -> bytes:
        '''
        Returns the digest of hashed data.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-chacha20poly1305.h
class ChaCha20Poly1305:
    '''
    ChaCha20Poly1305 context.
    '''

    def __init__(self, key: bytes, nonce: bytes) -> None:
        '''
        Initialize the ChaCha20 + Poly1305 context for encryption or decryption
        using a 32 byte key and 12 byte nonce as in the RFC 7539 style.
        '''

    def encrypt(self, data: bytes) -> bytes:
        '''
        Encrypt data (length of data must be divisible by 64 except for the final value).
        '''

    def decrypt(self, data: bytes) -> bytes:
        '''
        Decrypt data (length of data must be divisible by 64 except for the final value).
        '''

    def auth(self, data: bytes) -> None:
        '''
        Include authenticated data in the Poly1305 MAC using the RFC 7539
        style with 16 byte padding. This must only be called once and prior
        to encryption or decryption.
        '''

    def finish(self) -> bytes:
        '''
        Compute RFC 7539-style Poly1305 MAC.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-groestl.h
class Groestl512:
    '''
    GROESTL512 context.
    '''

    def __init__(self, data: bytes = None) -> None:
        '''
        Creates a hash context object.
        '''

    def update(self, data: bytes) -> None:
        '''
        Update the hash context with hashed data.
        '''

    def digest(self) -> bytes:
        '''
        Returns the digest of hashed data.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-pbkdf2.h
class Pbkdf2:
    '''
    PBKDF2 context.
    '''

    def __init__(self, prf: int, password: bytes, salt: bytes, iterations: int = None, blocknr: int = 1) -> None:
        '''
        Create a PBKDF2 context.
        '''

    def update(self, iterations: int) -> None:
        '''
        Update a PBKDF2 context.
        '''

    def key(self) -> bytes:
        '''
        Retrieve derived key.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-rfc6979.h
class Rfc6979:
    '''
    RFC6979 context.
    '''

    def __init__(self, secret_key: bytes, hash: bytes) -> None:
        '''
        Initialize RFC6979 context from secret key and a hash.
        '''

    def next(self) -> bytes:
        '''
        Compute next 32-bytes of pseudorandom data.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-ripemd160.h
class Ripemd160:
    '''
    RIPEMD160 context.
    '''

    def __init__(self, data: bytes = None) -> None:
        '''
        Creates a hash context object.
        '''

    def update(self, data: bytes) -> None:
        '''
        Update the hash context with hashed data.
        '''

    def digest(self) -> bytes:
        '''
        Returns the digest of hashed data.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-sha1.h
class Sha1:
    '''
    SHA1 context.
    '''

    def __init__(self, data: bytes = None) -> None:
        '''
        Creates a hash context object.
        '''

    def update(self, data: bytes) -> None:
        '''
        Update the hash context with hashed data.
        '''

    def digest(self) -> bytes:
        '''
        Returns the digest of hashed data.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-sha256.h
class Sha256:
    '''
    SHA256 context.
    '''

    def __init__(self, data: bytes = None) -> None:
        '''
        Creates a hash context object.
        '''

    def update(self, data: bytes) -> None:
        '''
        Update the hash context with hashed data.
        '''

    def digest(self) -> bytes:
        '''
        Returns the digest of hashed data.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-sha3-256.h
class Sha3_256:
    '''
    SHA3_256 context.
    '''

    def __init__(self, data: bytes = None, keccak = False) -> None:
        '''
        Creates a hash context object.
        '''

    def update(self, data: bytes) -> None:
        '''
        Update the hash context with hashed data.
        '''

    def digest(self) -> bytes:
        '''
        Returns the digest of hashed data.
        '''

    def copy(self) -> sha3:
        '''
        Returns the copy of the digest object with the current state
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-sha3-512.h
class Sha3_512:
    '''
    SHA3_512 context.
    '''

    def __init__(self, data: bytes = None, keccak = False) -> None:
        '''
        Creates a hash context object.
        '''

    def update(self, data: bytes) -> None:
        '''
        Update the hash context with hashed data.
        '''

    def digest(self) -> bytes:
        '''
        Returns the digest of hashed data.
        '''

    def copy(self) -> sha3:
        '''
        Returns the copy of the digest object with the current state
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-sha512.h
class Sha512:
    '''
    SHA512 context.
    '''

    def __init__(self, data: bytes = None) -> None:
        '''
        Creates a hash context object.
        '''

    def hash(self, data: bytes) -> None:
        '''
        Update the hash context with hashed data.
        '''

    def digest(self) -> bytes:
        '''
        Returns the digest of hashed data.
        '''
