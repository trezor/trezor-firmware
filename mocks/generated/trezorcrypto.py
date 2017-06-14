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

    def derive(self, index: int) -> None:
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

# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
class Bip32:
    '''
    '''

    def __init__(self):
        '''
        '''

    def deserialize(self, value: str, version_public: int, version_private: int) -> HDNode:
        '''
        Construct a BIP0032 HD node from a base58-serialized value.
        '''

    def from_seed(self, seed: bytes, curve_name: str) -> HDNode:
        '''
        Construct a BIP0032 HD node from a BIP0039 seed value.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-bip39.h
class Bip39:
    '''
    '''

    def __init__(self):
        '''
        '''

    def find_word(self, prefix: str) -> Optional[str]:
        '''
        Return the first word from the wordlist starting with prefix.
        '''

    def complete_word(self, prefix: str) -> int:
        '''
        Return possible 1-letter suffixes for given word prefix.
        Result is a bitmask, with 'a' on the lowest bit, 'b' on the second lowest, etc.
        '''

    def generate(self, strength: int) -> str:
        '''
        Generate a mnemonic of given strength (128, 160, 192, 224 and 256 bits).
        '''

    def from_data(self, data: bytes) -> str:
        '''
        Generate a mnemonic from given data (of 16, 20, 24, 28 and 32 bytes).
        '''

    def check(self, mnemonic: str) -> bool:
        '''
        Check whether given mnemonic is valid.
        '''

    def seed(self, mnemonic: str, passphrase: str) -> bytes:
        '''
        Generate seed from mnemonic and passphrase.
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

# extmod/modtrezorcrypto/modtrezorcrypto-curve25519.h
class Curve25519:
    '''
    '''

    def __init__(self) -> None:
        '''
        '''

    def generate_secret(self) -> bytes:
        '''
        Generate secret key.
        '''

    def publickey(self, secret_key: bytes) -> bytes:
        '''
        Computes public key from secret key.
        '''

    def multiply(self, secret_key: bytes, public_key: bytes) -> bytes:
        '''
        Multiplies point defined by public_key with scalar defined by secret_key.
        Useful for ECDH.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-ed25519.h
class Ed25519:
    '''
    '''

    def __init__(self) -> None:
        '''
        '''

    def generate_secret(self) -> bytes:
        '''
        Generate secret key.
        '''

    def publickey(self, secret_key: bytes) -> bytes:
        '''
        Computes public key from secret key.
        '''

    def sign(self, secret_key: bytes, message: bytes) -> bytes:
        '''
        Uses secret key to produce the signature of message.
        '''

    def verify(self, public_key: bytes, signature: bytes, message: bytes) -> bool:
        '''
        Uses public key to verify the signature of the message.
        Returns True on success.
        '''

    def cosi_combine_publickeys(self, public_keys: List[bytes]) -> bytes:
        '''
        Combines a list of public keys used in COSI cosigning scheme.
        '''

    def cosi_combine_signatures(self, R: bytes, signatures: List[bytes]) -> bytes:
        '''
        Combines a list of signatures used in COSI cosigning scheme.
        '''

    def cosi_sign(self, secret_key: bytes, message: bytes, nonce: bytes, sigR: bytes, combined_pubkey: bytes) -> bytes:
        '''
        Produce signature of message using COSI cosigning scheme.
        '''

# extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
class Nist256p1:
    '''
    '''

    def __init__(self) -> None:
        '''
        '''

    def generate_secret(self) -> bytes:
        '''
        Generate secret key.
        '''

    def publickey(self, secret_key: bytes, compressed: bool = True) -> bytes:
        '''
        Computes public key from secret key.
        '''

    def sign(self, secret_key: bytes, digest: bytes, compressed: bool = True) -> bytes:
        '''
        Uses secret key to produce the signature of the digest.
        '''

    def verify(self, public_key: bytes, signature: bytes, digest: bytes) -> bool:
        '''
        Uses public key to verify the signature of the digest.
        Returns True on success.
        '''

    def verify_recover(self, signature: bytes, digest: bytes) -> bytes:
        '''
        Uses signature of the digest to verify the digest and recover the public key.
        Returns public key on success, None on failure.
        '''

    def multiply(self, secret_key: bytes, public_key: bytes) -> bytes:
        '''
        Multiplies point defined by public_key with scalar defined by secret_key
        Useful for ECDH
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
class Random:
    '''
    '''

    def __init__(self) -> None:
        '''
        '''

    def uniform(self, n: int) -> int:
        '''
        Compute uniform random number from interval 0 ... n - 1
        '''

    def bytes(self, len: int) -> bytes:
        '''
        Generate random bytes sequence of length len
        '''

    def shuffle(self, data: list) -> None:
        '''
        Shuffles items of given list (in-place)
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
class Secp256k1:
    '''
    '''

    def __init__(self) -> None:
        '''
        '''

    def generate_secret(self, ) -> bytes:
        '''
        Generate secret key.
        '''

    def publickey(self, secret_key: bytes, compressed: bool = True) -> bytes:
        '''
        Computes public key from secret key.
        '''

    def sign(self, secret_key: bytes, digest: bytes, compressed: bool = True) -> bytes:
        '''
        Uses secret key to produce the signature of the digest.
        '''

    def verify(self, public_key: bytes, signature: bytes, digest: bytes) -> bool:
        '''
        Uses public key to verify the signature of the digest.
        Returns True on success.
        '''

    def verify_recover(self, signature: bytes, digest: bytes) -> bytes:
        '''
        Uses signature of the digest to verify the digest and recover the public key.
        Returns public key on success, None on failure.
        '''

    def multiply(self, secret_key: bytes, public_key: bytes) -> bytes:
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

# extmod/modtrezorcrypto/modtrezorcrypto-ssss.h
class SSSS:
    '''
    '''

    def __init__(self) -> None:
        '''
        '''

    def split(self, m: int, n: int, secret: bytes) -> tuple:
        '''
        Split secret to (M of N) shares using Shamir's Secret Sharing Scheme.
        '''

    def combine(self, shares: tuple) -> bytes:
        '''
        Combine M shares of Shamir's Secret Sharing Scheme into secret.
        '''
