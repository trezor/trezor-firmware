from typing import Generic, TypeVar, final

AnyBuffer = bytearray | memoryview
AnyBytes = bytes | bytearray | memoryview
StrOrBytes = str | AnyBytes

_S = TypeVar("_S", bound=StrOrBytes, covariant=True)

@final
class secure(Generic[_S]):
    """Opaque marker for secret material -- see `trezor.secbytes`.

    Not a subtype of what it wraps, so indexing, slicing, concatenation,
    `.encode()`/`.decode()` and passing to a public API are all rejected.
    `len()` and truthiness are deliberately allowed.
    """

    def __len__(self) -> int: ...

securebytes = secure[AnyBytes]
securestr = secure[str]
