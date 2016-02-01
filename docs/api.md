#TREZOR OS API

Syntax used below are valid Python function declarations with anotations defined in [PEP 3107](https://www.python.org/dev/peps/pep-3107/).

##trezor.crypto

###trezor.crypto.ed25519

``` python
def to_public(secret_key: bytes[32]) -> bytes[32]: # public_key

def sign(message: bytes, secret_key: bytes[32], public_key: bytes[32] = None) -> bytes[64]: # signature

def verify(message: bytes, public_key: bytes[32], signature: bytes[64]) -> bool: # valid
```

###trezor.crypto.func

``` python
def aes():

def base58():

def hmac():

def sha256():

def ripemd160():

def pbkdf2():
```

###trezor.crypto.hd

###trezor.crypto.mnemonic

###trezor.crypto.nistp256

``` python
def to_public(secret_key: bytes[32]) -> bytes[33]: # public_key

def sign(message: bytes, secret_key: bytes[32], public_key: bytes[33] = None) -> bytes[65]: # signature

def verify(message: bytes, public_key: bytes[33], signature: bytes[65]) -> bool: # valid
```

###trezor.crypto.secp256k1

``` python
def to_public(secret_key: bytes[32]) -> bytes[33]: # public_key

def sign(message: bytes, secret_key: bytes[32], public_key: bytes[33] = None) -> bytes[65]: # signature

def verify(message: bytes, public_key: bytes[33], signature: bytes[65]) -> bool: # valid
```

##trezor.hw

###trezor.hw.button

###trezor.hw.display

##trezor.utils

###trezor.utils.qrenc

``` python
enum QRLEVEL {
  L = 0,
  M = 1,
  Q = 2,
  H = 3,
}

def encode(source: bytes, level: QRLEVEL = QRLEVEL.H) -> bool[][]: # qrcode
```
