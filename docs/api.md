#TREZOR OS API

Syntax used below are valid Python function declarations with anotations defined in [PEP 3107](https://www.python.org/dev/peps/pep-3107/).

``` python
class bytes20(bytes): pass # bytes variable of exactly 20 bytes
class bytes21(bytes): pass # bytes variable of exactly 21 bytes
class bytes32(bytes): pass # bytes variable of exactly 32 bytes
class bytes33(bytes): pass # bytes variable of exactly 33 bytes
class bytes64(bytes): pass # bytes variable of exactly 64 bytes
class bytes65(bytes): pass # bytes variable of exactly 65 bytes

class uint32(int): pass # 32-bit unsigned int
```

##trezor.crypto

###trezor.crypto.ed25519

``` python
def to_public(secret_key: bytes32) -> bytes32: # public_key

def sign(message: bytes, secret_key: bytes32, public_key: bytes32 = None) -> bytes64: # signature

def verify(message: bytes, public_key: bytes32, signature: bytes64) -> bool: # valid
```

###trezor.crypto.func

``` python
def aes():

def base58_encode(data: bytes) -> bytes: # encoded

def base58_decode(data: bytes) -> bytes: # decoded

def base58_encode_check(data: bytes) -> bytes: # encoded

def base58_decode_check(data: bytes) -> bytes: # decoded

def hmac_sha256(key: bytes, message: bytes) -> bytes32: # hmac

def hmac_sha512(key: bytes, message: bytes) -> bytes64: # hmac

def sha256(data: bytes) -> bytes32: # hashed

def sha512(data: bytes) -> bytes64: # hashed

def ripemd160(data: bytes) -> bytes20: # hashed

def pbkdf2_hmac_sha256(password: bytes, salt: bytes, iterations: uint32, keylen: uint32) -> bytes32: # key

def pbkdf2_hmac_sha512(password: bytes, salt: bytes, iterations: uint32, keylen: uint32) -> bytes32: # key
```

###trezor.crypto.hd

TODO

###trezor.crypto.mnemonic

TODO

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

def encode(source: bytes, level: QrLevel = QrLevel.H) -> (int, list): # size, data
```
