ARRAY = ...  # type: int
NATIVE = ...  # type: int
LITTLE_ENDIAN = ...  # type: int
BIG_ENDIAN = ...  # type: int
VOID = ...  # type: int
UINT8 = ...  # type: int
INT8 = ...  # type: int
UINT16 = ...  # type: int
INT16 = ...  # type: int
UINT32 = ...  # type: int
INT32 = ...  # type: int
UINT64 = ...  # type: int
INT64 = ...  # type: int
BFUINT8 = ...  # type: int
BFINT8 = ...  # type: int
BFUINT16 = ...  # type: int
BFINT16 = ...  # type: int
BFUINT32 = ...  # type: int
BFINT32 = ...  # type: int
BF_POS = ...  # type: int
BF_LEN = ...  # type: int
FLOAT32 = ...  # type: int

class struct:
    def __init__(self, addr: int, descriptor: dict, layout_type: int = ...) -> None: ...

def sizeof(struct: struct) -> int: ...
def addressof(obj: bytes) -> int: ...
def bytes_at(addr: int, size: int) -> bytes: ...
def bytearray_at(addr, size) -> bytearray: ...
