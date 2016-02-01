#TREZOR OS API

##trezor.crypto

###trezor.crypto.ed25519

```
def to_public(bytes[32] secret_key) => bytes[32] public_key

def sign(bytes message, bytes[32] secret_key, bytes[32] public_key = None) => bytes[64] signature

def verify(bytes message, bytes[32] public_key, bytes[64] signature) => bool valid
```

###trezor.crypto.func

```
aes()
base58()
hmac()
sha256()
ripemd160()
pbkdf2()
```

###trezor.crypto.hd

###trezor.crypto.mnemonic

###trezor.crypto.nistp256

```
def to_public()

def sign()

def verify()
```

###trezor.crypto.secp256k1

```
def to_public()

def sign()

def verify()
```

##trezor.hw

###trezor.hw.button

###trezor.hw.display

##trezor.qrenc

```
enum QRLEVEL {
  L = 0,
  M = 1,
  Q = 2,
  H = 3,
}

def encode(bytes source, qrlevel level = QRLEVEL.H) => bool[][] qrcode
```
