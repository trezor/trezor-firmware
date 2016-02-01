#TREZOR OS API

Auxiliary classes used to tighten the type checking.

``` python
class bytes16(bytes): pass # bytes variable of exactly 16 bytes
class bytes20(bytes): pass # bytes variable of exactly 20 bytes
class bytes21(bytes): pass # bytes variable of exactly 21 bytes
class bytes24(bytes): pass # bytes variable of exactly 24 bytes
class bytes32(bytes): pass # bytes variable of exactly 32 bytes
class bytes33(bytes): pass # bytes variable of exactly 33 bytes
class bytes64(bytes): pass # bytes variable of exactly 64 bytes
class bytes65(bytes): pass # bytes variable of exactly 65 bytes
```

Syntax used below is a valid Python function declaration with anotations defined in [PEP 3107](https://www.python.org/dev/peps/pep-3107/).

##trezor.crypto

###trezor.crypto.aes

``` python
class aes_ctx(object): pass # AES context

def aes_encrypt_key128(key: bytes16, iv: bytes16 = None) -> aes_ctx: # context

def aes_encrypt_key192(key: bytes24, iv: bytes16 = None) -> aes_ctx: # context

def aes_encrypt_key256(key: bytes32, iv: bytes16 = None) -> aes_ctx: # context

def aes_decrypt_key128(key: bytes16, iv: bytes16 = None) -> aes_ctx: # context

def aes_decrypt_key192(key: bytes24, iv: bytes16 = None) -> aes_ctx: # context

def aes_decrypt_key256(key: bytes32, iv: bytes16 = None) -> aes_ctx: # context

def aes_ecb_encrypt(ctx: aes_ctx, data: bytes) -> bytes: # encrypted

def aes_cbc_encrypt(ctx: aes_ctx, data: bytes) -> bytes: # encrypted

def aes_cfb_encrypt(ctx: aes_ctx, data: bytes) -> bytes: # encrypted

def aes_ofb_encrypt(ctx: aes_ctx, data: bytes) -> bytes: # encrypted

def aes_ctr_encrypt(ctx: aes_ctx, data: bytes) -> bytes: # encrypted

def aes_ecb_decrypt(ctx: aes_ctx, data: bytes) -> bytes: # decrypted

def aes_cbc_decrypt(ctx: aes_ctx, data: bytes) -> bytes: # decrypted

def aes_cfb_decrypt(ctx: aes_ctx, data: bytes) -> bytes: # decrypted

def aes_ofb_decrypt(ctx: aes_ctx, data: bytes) -> bytes: # decrypted

def aes_ctr_decrypt(ctx: aes_ctx, data: bytes) -> bytes: # decrypted
```

###trezor.crypto.base58

``` python
def encode(data: bytes) -> bytes: # encoded

def decode(data: bytes) -> bytes: # decoded

def encode_check(data: bytes) -> bytes: # encoded

def decode_check(data: bytes) -> bytes: # decoded
```

###trezor.crypto.ed25519

``` python
def to_public(secret_key: bytes32) -> bytes32: # public_key

def sign(message: bytes, secret_key: bytes32, public_key: bytes32 = None) -> bytes64: # signature

def verify(message: bytes, public_key: bytes32, signature: bytes64) -> bool: # valid
```

###trezor.crypto.hash

``` python
def sha256(data: bytes) -> bytes32: # hashed

def sha512(data: bytes) -> bytes64: # hashed

def ripemd160(data: bytes) -> bytes20: # hashed
```

###trezor.crypto.hd

TODO

###trezor.crypto.hmac

``` python
def hmac_sha256(key: bytes, message: bytes) -> bytes32: # hmac

def hmac_sha512(key: bytes, message: bytes) -> bytes64: # hmac
```

###trezor.crypto.kdf

``` python
def pbkdf2_hmac_sha256(password: bytes, salt: bytes, iterations: int, keylen: int) -> bytes32: # key

def pbkdf2_hmac_sha512(password: bytes, salt: bytes, iterations: int, keylen: int) -> bytes32: # key
```

###trezor.crypto.mnemonic

``` python
def bip39_generate(strength: int) -> bytes: # sentence

def bip39_fromdata(data: bytes) -> bytes: # sentence

def bip39_check(mnemonic: bytes) -> bool: # valid

def bip39_seed(mnemonic: bytes, passphrase: bytes) -> bytes64: # seed
```

###trezor.crypto.nistp256

``` python
def to_public(secret_key: bytes32) -> bytes33: # public_key

def sign(message: bytes, secret_key: bytes32, public_key: bytes33 = None) -> bytes65: # signature

def verify(message: bytes, public_key: bytes33, signature: bytes65) -> bool: # valid
```

###trezor.crypto.secp256k1

``` python
def to_public(secret_key: bytes32) -> bytes33: # public_key

def sign(message: bytes, secret_key: bytes32, public_key: bytes33 = None) -> bytes65: # signature

def verify(message: bytes, public_key: bytes33, signature: bytes65) -> bool: # valid
```

##trezor.hw

###trezor.hw.button

TODO

###trezor.hw.display

TODO

##trezor.utils

###trezor.utils.qrenc

``` python
class QrLevel(Enum):
    L = 0
    M = 1
    Q = 2
    H = 3

def encode(source: bytes, level: QrLevel = QrLevel.H) -> list: # data
```
