from typing import final

AnyBuffer = bytearray | memoryview
AnyBytes = bytes | bytearray | memoryview
StrOrBytes = str | AnyBytes

@final
class securebytes:
    def __len__(self) -> int: ...
