#TREZOR OS API

Auxiliary classes used to tighten the type checking.

``` python
bytes16 = bytes # bytes variable of exactly 16 bytes
bytes20 = bytes # bytes variable of exactly 20 bytes
bytes21 = bytes # bytes variable of exactly 21 bytes
bytes24 = bytes # bytes variable of exactly 24 bytes
bytes32 = bytes # bytes variable of exactly 32 bytes
bytes33 = bytes # bytes variable of exactly 33 bytes
bytes64 = bytes # bytes variable of exactly 64 bytes
bytes65 = bytes # bytes variable of exactly 65 bytes
```

Syntax used below is a valid Python function declaration with type hints defined in [PEP 0484](https://www.python.org/dev/peps/pep-0484/).


##trezor.msg

``` python
def trezor.msg.receive(callback) -> None

def trezor.msg.send(message) -> None
```

##trezor.protobuf

``` python
def trezor.protobuf.encode(message) -> bytes

def trezor.protobuf.decode(data: bytes) -> object
```

##trezor.ui

###trezor.ui.display

``` python
trezor.ui.display.bar(self, x: int, y: int, w: int, h: int, color: int) -> None

trezor.ui.display.blit(self, x: int, y: int, w: int, h: int, data: bytes) -> None

trezor.ui.display.image(self, x: int, y: int, image: bytes) -> None

trezor.ui.display.icon(self, x: int, y: int, icon: bytes, fgcolor: int, bgcolor: int) -> None

trezor.ui.display.text(self, x: int, y: int, text: bytes, font: int, fgcolor: int, bgcolor: int) -> None

trezor.ui.display.qrcode(self, x: int, y: int, data: bytes, scale: int) -> None

trezor.ui.display.orientation(self, degrees: int) -> None

trezor.ui.display.raw(self, reg: int, data: bytes) -> None

trezor.ui.display.backlight(self, val: int) -> None
```

###trezor.ui.touch

``` python
trezor.ui.touch.start(self, callback) -> None

trezor.ui.touch.move(self, callback) -> None

trezor.ui.touch.end(self, callback) -> None
```
