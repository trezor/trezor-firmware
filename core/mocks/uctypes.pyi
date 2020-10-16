ARRAY: int
NATIVE: int
LITTLE_ENDIAN: int
BIG_ENDIAN: int
VOID: int
UINT8: int
INT8: int
UINT16: int
INT16: int
UINT32: int
INT32: int
UINT64: int
INT64: int
BFUINT8: int
BFINT8: int
BFUINT16: int
BFINT16: int
BFUINT32: int
BFINT32: int
BF_POS: int
BF_LEN: int
FLOAT32: int

class struct:
    def __init__(self, addr: int, descriptor: dict, layout_type: int = ...) -> None: ...

def sizeof(struct: struct) -> int: ...
def addressof(obj: bytes) -> int: ...
def bytes_at(addr: int, size: int) -> bytes: ...
def bytearray_at(addr: int, size: int) -> bytearray: ...
