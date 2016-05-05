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

Computes public key from secret key.

``` python
def trezor.crypto.curve.ed25519.sign(self, secret_key: bytes, message: bytes) -> bytes
```

Uses secret key to produce the signature of message.

``` python
def trezor.crypto.curve.ed25519.verify(self, public_key: bytes, signature: bytes, message: bytes) -> bool
```

Uses public key to verify the signature of the message
Returns True on success.


####trezor.crypto.curve.nist256p1

``` python
def trezor.crypto.curve.nist256p1.publickey(self, secret_key: bytes, compressed: bool=True) -> bytes
```

Computes public key from secret key.

``` python
def trezor.crypto.curve.nist256p1.sign(self, secret_key: bytes, message: bytes) -> bytes
```

Uses secret key to produce the signature of message.

``` python
def trezor.crypto.curve.nist256p1.verify(self, public_key: bytes, signature: bytes, message: bytes) -> bool
```

Uses public key to verify the signature of the message
Returns True on success.


####trezor.crypto.curve.secp256k1

``` python
def trezor.crypto.curve.secp256k1.publickey(self, secret_key: bytes, compressed: bool=True) -> bytes
```

Computes public key from secret key.

``` python
def trezor.crypto.curve.secp256k1.sign(self, secret_key: bytes, message: bytes) -> bytes
```

Uses secret key to produce the signature of message.

``` python
def trezor.crypto.curve.secp256k1.verify(self, public_key: bytes, signature: bytes, message: bytes) -> bool
```

Uses public key to verify the signature of the message
Returns True on success.


###trezor.crypto.hashlib

####trezor.crypto.hashlib.ripemd160

``` python
def trezor.crypto.hashlib.ripemd160(self, data: bytes=None) -> Ripemd160
```

Creates a hash context object.

``` python
def Ripemd160.update(self, data: bytes) -> None
```

Update the hash context with hashed data.

``` python
def Ripemd160.digest(self) -> bytes
```

Returns the digest of hashed data.


####trezor.crypto.hashlib.sha256

``` python
def trezor.crypto.hashlib.sha256(self, data: bytes=None) -> Sha256
```

Creates a hash context object.

``` python
def Sha256.update(self, data: bytes) -> None
```

Update the hash context with hashed data.

``` python
def Sha256.digest(self) -> bytes
```

Returns the digest of hashed data.


####trezor.crypto.hashlib.sha512

``` python
def trezor.crypto.hashlib.sha512(self, data: bytes=None) -> Sha512
```

Creates a hash context object.

``` python
def Sha512.hash(self, data: bytes) -> None
```

Update the hash context with hashed data.

``` python
def Sha512.digest(self) -> bytes
```

Returns the digest of hashed data.


####trezor.crypto.hashlib.sha3_256

``` python
def trezor.crypto.hashlib.sha3_256(self, data: bytes=None) -> Sha3_256
```

Creates a hash context object.

``` python
def Sha3_256.update(self, data: bytes) -> None
```

Update the hash context with hashed data.

``` python
def Sha3_256.digest(self) -> bytes
```

Returns the digest of hashed data.


####trezor.crypto.hashlib.sha3_512

``` python
def trezor.crypto.hashlib.sha3_512(self, data: bytes=None) -> Sha3_512
```

Creates a hash context object.

``` python
def Sha3_512.update(self, data: bytes) -> None
```

Update the hash context with hashed data.

``` python
def Sha3_512.digest(self) -> bytes
```

Returns the digest of hashed data.


###trezor.crypto.hmac

``` python
def trezor.crypto.hmac.new(key, msg, digestmod) -> Hmac
```

##trezor.msg

``` python
def trezor.msg.send(self, message) -> int
```

Sends message using USB HID (device) or UDP (emulator).

``` python
def trezor.msg.select(self, timeout_us: int) -> tuple
```

Polls the event queue and returns the event object.
Function returns None if timeout specified in microseconds is reached.


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

Renders a bar at position (x,y = upper left corner) with width w and height h of color fgcolor.
When a bgcolor is set, the bar is drawn with rounded corners and bgcolor is used for background.

``` python
def trezor.ui.display.blit(self, x: int, y: int, w: int, h: int, data: bytes) -> None
```

Renders rectangle at position (x,y = upper left corner) with width w and height h with data.
The data needs to have the correct format.

``` python
def trezor.ui.display.image(self, x: int, y: int, image: bytes) -> None
```

Renders an image at position (x,y).
The image needs to be in TREZOR Optimized Image Format (TOIF) - full-color mode.

``` python
def trezor.ui.display.icon(self, x: int, y: int, icon: bytes, fgcolor: int, bgcolor: int) -> None
```

Renders an icon at position (x,y), fgcolor is used as foreground color, bgcolor as background.
The image needs to be in TREZOR Optimized Image Format (TOIF) - gray-scale mode.

``` python
def trezor.ui.display.text(self, x: int, y: int, text: bytes, font: int, fgcolor: int, bgcolor: int) -> None
```

Renders left-aligned text at position (x,y) where x is left position and y is baseline.
Font font is used for rendering, fgcolor is used as foreground color, bgcolor as background.

``` python
def trezor.ui.display.text_center(self, x: int, y: int, text: bytes, font: int, fgcolor: int, bgcolor: int) -> None
```

Renders text centered at position (x,y) where x is text center and y is baseline.
Font font is used for rendering, fgcolor is used as foreground color, bgcolor as background.

``` python
def trezor.ui.display.text_right(self, x: int, y: int, text: bytes, font: int, fgcolor: int, bgcolor: int) -> None
```

Renders right-aligned text at position (x,y) where x is right position and y is baseline.
Font font is used for rendering, fgcolor is used as foreground color, bgcolor as background.

``` python
def trezor.ui.display.text_width(self, text: bytes, font: int) -> int
```

Returns a width of text in pixels. Font font is used for rendering.

``` python
def trezor.ui.display.qrcode(self, x: int, y: int, data: bytes, scale: int) -> None
```

Renders data encoded as a QR code at position (x,y).
Scale determines a zoom factor.

``` python
def trezor.ui.display.loader(self, progress: int, fgcolor: int, bgcolor: int, icon: bytes=None, iconfgcolor: int=None) -> None
```

Renders a rotating loader graphic.
Progress determines its position (0-1000), fgcolor is used as foreground color, bgcolor as background.
When icon and iconfgcolor are provided, an icon is drawn in the middle using the color specified in iconfgcolor.
Icon needs to be of exaclty 96x96 pixels size.

``` python
def trezor.ui.display.orientation(self, degrees: int) -> None
```

Sets display orientation to 0, 90, 180 or 270 degrees.
Everything needs to be redrawn again when this function is used.

``` python
def trezor.ui.display.backlight(self, val: int) -> None
```

Sets backlight intensity to the value specified in val.

``` python
def trezor.ui.display.raw(self, reg: int, data: bytes) -> None
```

Performs a raw command on the display. Read the datasheet to learn more.


###trezor.utils

``` python
def trezor.utils.memaccess(self, address: int, length: int) -> bytes
```

Creates a bytes object that can be used to access certain memory location.

