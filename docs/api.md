#TREZOR OS API

Syntax used below is a valid Python function declaration with type hints defined in [PEP 0484](https://www.python.org/dev/peps/pep-0484/).

##trezor.crypto

###trezor.crypto.base58

``` python
def trezor.crypto.base58.encode(data: bytes) -> str
```
``` python
def trezor.crypto.base58.decode(string: str) -> bytes
```
``` python
def trezor.crypto.base58.encode_check(data: bytes) -> str
```
``` python
def trezor.crypto.base58.decode_check(string: str) -> bytes
```

###trezor.crypto.curve

####trezor.crypto.curve.ed25519

``` python
def trezor.crypto.curve.ed25519.publickey(self, secret_key: bytes) -> bytes
```
``` python
def trezor.crypto.curve.ed25519.sign(self, secret_key: bytes, message: bytes) -> bytes
```
``` python
def trezor.crypto.curve.ed25519.verify(self, public_key: bytes, signature: bytes, message: bytes) -> bool
```

####trezor.crypto.curve.nist256p1

``` python
def trezor.crypto.curve.nist256p1.publickey(self, secret_key: bytes, compressed: bool=True) -> bytes
```
``` python
def trezor.crypto.curve.nist256p1.sign(self, secret_key: bytes, message: bytes) -> bytes
```
``` python
def trezor.crypto.curve.nist256p1.verify(self, public_key: bytes, signature: bytes, message: bytes) -> bool
```

####trezor.crypto.curve.secp256k1

``` python
def trezor.crypto.curve.secp256k1.publickey(self, secret_key: bytes, compressed: bool=True) -> bytes
```
``` python
def trezor.crypto.curve.secp256k1.sign(self, secret_key: bytes, message: bytes) -> bytes
```
``` python
def trezor.crypto.curve.secp256k1.verify(self, public_key: bytes, signature: bytes, message: bytes) -> bool
```

###trezor.crypto.hashlib

####trezor.crypto.hashlib.ripemd160

``` python
def trezor.crypto.hashlib.ripemd160(self, data: bytes=None) -> Ripemd160
```
``` python
def Ripemd160.update(self, data: bytes) -> None
```
``` python
def Ripemd160.digest(self) -> bytes
```

####trezor.crypto.hashlib.sha256

``` python
def trezor.crypto.hashlib.sha256(self, data: bytes=None) -> Sha256
```
``` python
def Sha256.update(self, data: bytes) -> None
```
``` python
def Sha256.digest(self) -> bytes
```

####trezor.crypto.hashlib.sha512

``` python
def trezor.crypto.hashlib.sha512(self, data: bytes=None) -> Sha512
```
``` python
def Sha512.hash(self, data: bytes) -> None
```
``` python
def Sha512.digest(self) -> bytes
```

####trezor.crypto.hashlib.sha3_256

``` python
def trezor.crypto.hashlib.sha3_256(self, data: bytes=None) -> Sha3_256
```
``` python
def Sha3_256.update(self, data: bytes) -> None
```
``` python
def Sha3_256.digest(self) -> bytes
```

####trezor.crypto.hashlib.sha3_512

``` python
def trezor.crypto.hashlib.sha3_512(self, data: bytes=None) -> Sha3_512
```
``` python
def Sha3_512.update(self, data: bytes) -> None
```
``` python
def Sha3_512.digest(self) -> bytes
```

###trezor.crypto.hmac

``` python
def trezor.crypto.hmac.new(key, msg, digestmod) -> Hmac
```

##trezor.msg

``` python
def trezor.msg.send(self, message) -> int
```
``` python
def trezor.msg.select(self, timeout_us: int) -> tuple
```

##trezor.ui

``` python
def trezor.ui.rgbcolor(r: int, g: int, b: int) -> int
```
``` python
def trezor.ui.lerpi(a: int, b: int, t: float) -> int
```
``` python
def trezor.ui.blend(ca: int, cb: int, t: float) -> int
```
``` python
def trezor.ui.animate_pulse(func, ca, cb, speed=200000, delay=30000)
```

###trezor.ui.display

``` python
def trezor.ui.display.bar(self, x: int, y: int, w: int, h: int, fgcolor: int, bgcolor: int=None) -> None
```
``` python
def trezor.ui.display.blit(self, x: int, y: int, w: int, h: int, data: bytes) -> None
```
``` python
def trezor.ui.display.image(self, x: int, y: int, image: bytes) -> None
```
``` python
def trezor.ui.display.icon(self, x: int, y: int, icon: bytes, fgcolor: int, bgcolor: int) -> None
```
``` python
def trezor.ui.display.text(self, x: int, y: int, text: bytes, font: int, fgcolor: int, bgcolor: int) -> None
```
``` python
def trezor.ui.display.text_center(self, x: int, y: int, text: bytes, font: int, fgcolor: int, bgcolor: int) -> None
```
``` python
def trezor.ui.display.text_right(self, x: int, y: int, text: bytes, font: int, fgcolor: int, bgcolor: int) -> None
```
``` python
def trezor.ui.display.text_width(self, text: bytes, font: int) -> int
```
``` python
def trezor.ui.display.qrcode(self, x: int, y: int, data: bytes, scale: int) -> None
```
``` python
def trezor.ui.display.loader(self, progress: int, fgcolor: int, bgcolor: int, icon: bytes=None, iconfgcolor: int=None) -> None
```
``` python
def trezor.ui.display.orientation(self, degrees: int) -> None
```
``` python
def trezor.ui.display.raw(self, reg: int, data: bytes) -> None
```
``` python
def trezor.ui.display.backlight(self, val: int) -> None
```
