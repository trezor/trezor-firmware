from typing import *

# extmod/modtrezorcrypto/modtrezorcrypto-aes.h
class AES:
    '''
    AES context.
    '''

    def __init__(self, mode: int, key: bytes, iv: bytes = None) -> None:
        '''
        Initialize AES context.
        '''

    def update(self, data: bytes) -> bytes:
        '''
        Update AES context with data.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
class HDNode:
    '''
    BIP0032 HD node structure.
    '''

    def __init__(self,
                 depth: int,
                 fingerprint: int,
                 child_num: int,
                 chain_code: bytes,
                 private_key: bytes = None,
                 public_key: bytes = None,
                 curve_name: str = None) -> None:
        '''
        '''

    def derive(self, index: int, public: bool=False) -> None:
        '''
        Derive a BIP0032 child node in place.
        '''

    def derive_path(self, path: List[int]) -> None:
        '''
        Go through a list of indexes and iteratively derive a child node in place.
        '''

    def serialize_public(self, version: int) -> str:
        '''
        Serialize the public info from HD node to base58 string.
        '''

    def serialize_private(self, version: int) -> str:
        '''
        Serialize the private info HD node to base58 string.
        '''

    def clone(self) -> HDNode:
        '''
        Returns a copy of the HD node.
        '''

    def depth(self) -> int:
        '''
        Returns a depth of the HD node.
        '''

    def fingerprint(self) -> int:
        '''
        Returns a fingerprint of the HD node (hash of the parent public key).
        '''

    def child_num(self) -> int:
        '''
        Returns a child index of the HD node.
        '''

    def chain_code(self) -> bytes:
        '''
        Returns a chain code of the HD node.
        '''

    def private_key(self) -> bytes:
        '''
        Returns a private key of the HD node.
        '''

    def public_key(self) -> bytes:
        '''
        Returns a public key of the HD node.
        '''

    def address(self, version: int) -> str:
        '''
        Compute a base58-encoded address string from the HD node.
        '''

    def nem_address(self, network: int) -> str:
        '''
        Compute a NEM address string from the HD node.
        '''

    def nem_encrypt(self, transfer_public_key: bytes, iv: bytes, salt: bytes, payload: bytes) -> bytes:
        '''
        Encrypts payload using the transfer's public key
        '''

    def ethereum_pubkeyhash(self) -> bytes:
        '''
        Compute an Ethereum pubkeyhash (aka address) from the HD node.
        '''

    def deserialize(self, value: str, version_public: int, version_private: int) -> HDNode:
        '''
        Construct a BIP0032 HD node from a base58-serialized value.
        '''

    def from_seed(seed: bytes, curve_name: str) -> HDNode:
        '''
        Construct a BIP0032 HD node from a BIP0039 seed value.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip39.h
def find_word(prefix: str) -> Optional[str]:
    '''
    Return the first word from the wordlist starting with prefix.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip39.h
def complete_word(prefix: str) -> int:
    '''
    Return possible 1-letter suffixes for given word prefix.
    Result is a bitmask, with 'a' on the lowest bit, 'b' on the second lowest, etc.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip39.h
def generate(strength: int) -> str:
    '''
    Generate a mnemonic of given strength (128, 160, 192, 224 and 256 bits).
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip39.h
def from_data(data: bytes) -> str:
    '''
    Generate a mnemonic from given data (of 16, 20, 24, 28 and 32 bytes).
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip39.h
def check(mnemonic: str) -> bool:
    '''
    Check whether given mnemonic is valid.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip39.h
def seed(mnemonic: str, passphrase: str) -> bytes:
    '''
    Generate seed from mnemonic and passphrase.
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

    def __init__(self, data: bytes = None, key: bytes = None) -> None:
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

    def __init__(self, data: bytes = None, key: bytes = None) -> None:
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

# extmod/modtrezorcrypto/modtrezorcrypto-curve25519.h
def generate_secret() -> bytes:
    '''
    Generate secret key.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-curve25519.h
def publickey(secret_key: bytes) -> bytes:
    '''
    Computes public key from secret key.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-curve25519.h
def multiply(secret_key: bytes, public_key: bytes) -> bytes:
    '''
    Multiplies point defined by public_key with scalar defined by secret_key.
    Useful for ECDH.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def generate_secret() -> bytes:
    '''
    Generate secret key.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def publickey(secret_key: bytes) -> bytes:
    '''
    Computes public key from secret key.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def sign(secret_key: bytes, message: bytes, hasher: str='') -> bytes:
    '''
    Uses secret key to produce the signature of message.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def verify(public_key: bytes, signature: bytes, message: bytes) -> bool:
    '''
    Uses public key to verify the signature of the message.
    Returns True on success.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def cosi_combine_publickeys(public_keys: List[bytes]) -> bytes:
    '''
    Combines a list of public keys used in COSI cosigning scheme.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def cosi_combine_signatures(R: bytes, signatures: List[bytes]) -> bytes:
    '''
    Combines a list of signatures used in COSI cosigning scheme.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-ed25519.h
def cosi_sign(secret_key: bytes, message: bytes, nonce: bytes, sigR: bytes, combined_pubkey: bytes) -> bytes:
    '''
    Produce signature of message using COSI cosigning scheme.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-nem.h
def validate_address(address: str, network: int) -> bool:
    '''
    Validate a NEM address
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-nem.h
def compute_address(public_key: bytes, network: int) -> str:
    '''
    Compute a NEM address from a public key
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def generate_secret() -> bytes:
    '''
    Generate secret key.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def publickey(secret_key: bytes, compressed: bool = True) -> bytes:
    '''
    Computes public key from secret key.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def sign(secret_key: bytes, digest: bytes, compressed: bool = True) -> bytes:
    '''
    Uses secret key to produce the signature of the digest.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def verify(public_key: bytes, signature: bytes, digest: bytes) -> bool:
    '''
    Uses public key to verify the signature of the digest.
    Returns True on success.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def verify_recover(signature: bytes, digest: bytes) -> bytes:
    '''
    Uses signature of the digest to verify the digest and recover the public key.
    Returns public key on success, None on failure.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def multiply(secret_key: bytes, public_key: bytes) -> bytes:
    '''
    Multiplies point defined by public_key with scalar defined by secret_key.
    Useful for ECDH.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-pbkdf2.h
class Pbkdf2:
    '''
    PBKDF2 context.
    '''

    def __init__(self, prf: str, password: bytes, salt: bytes, iterations: int = None) -> None:
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

# extmod/modtrezorcrypto/modtrezorcrypto-random.h
def uniform(n: int) -> int:
    '''
    Compute uniform random number from interval 0 ... n - 1.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-random.h
def bytes(len: int) -> bytes:
    '''
    Generate random bytes sequence of length len.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-random.h
def shuffle(data: list) -> None:
    '''
    Shuffles items of given list (in-place).
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

# extmod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def generate_secret() -> bytes:
    '''
    Generate secret key.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def publickey(secret_key: bytes, compressed: bool = True) -> bytes:
    '''
    Computes public key from secret key.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def sign(secret_key: bytes, digest: bytes, compressed: bool = True) -> bytes:
    '''
    Uses secret key to produce the signature of the digest.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def verify(public_key: bytes, signature: bytes, digest: bytes) -> bool:
    '''
    Uses public key to verify the signature of the digest.
    Returns True on success.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def verify_recover(signature: bytes, digest: bytes) -> bytes:
    '''
    Uses signature of the digest to verify the digest and recover the public key.
    Returns public key on success, None on failure.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-secp256k1.h
def multiply(secret_key: bytes, public_key: bytes) -> bytes:
    '''
    Multiplies point defined by public_key with scalar defined by secret_key.
    Useful for ECDH.
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

    def __init__(self, data: bytes = None) -> None:
        '''
        Creates a hash context object.
        '''

    def update(self, data: bytes) -> None:
        '''
        Update the hash context with hashed data.
        '''

    def digest(self, keccak: bool = False) -> bytes:
        '''
        Returns the digest of hashed data.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-sha3-512.h
class Sha3_512:
    '''
    SHA3_512 context.
    '''

    def __init__(self, data: bytes = None) -> None:
        '''
        Creates a hash context object.
        '''

    def update(self, data: bytes) -> None:
        '''
        Update the hash context with hashed data.
        '''

    def digest(self, keccak: bool = False) -> bytes:
        '''
        Returns the digest of hashed data.
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
