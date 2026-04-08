from dataclasses import dataclass

# Case 1:  CLA INS P1 P2
# Case 2S: CLA INS P1 P2 Le (1 <= Le <= 256, Le = 256 is represented as 0x00)
# Case 2E: CLA INS P1 P2 00 LeHi LeLow (1 <= Le <= 65536)
# Case 3S: CLA INS P1 P2 Lc Data (1 <= Lc <= 255)
# Case 3E: CLA INS P1 P2 00 LcHi LcLow Data (1 <= Lc <= 65535)
# Case 4S: CLA INS P1 P2 Lc Data Le (1 <= Lc <= 255, 1 <= Le <= 256, Le = 256 is represented as 0x00)
# Case 4E: CLA INS P1 P2 00 LcHi LcLow Data LeHi LeLow (1 <= Lc <= 65535, 1 <= Le <= 65536, Le = 65536 is represented as 0x00 0x00)


EXTENDED_LENGTH_MARKER = bytes([0x00])
SHORT_LC_MAX = 255
SHORT_LE_MAX = 256
EXTENDED_LE_MAX = 65536
EXTENDED_LC_MAX = 65536


class ApduError(ValueError):
    pass


class InvalidCla(ApduError):
    pass


class InvalidIns(ApduError):
    pass


class InvalidP1(ApduError):
    pass


class InvalidP2(ApduError):
    pass


class InvalidLc(ApduError):
    pass


class InvalidLe(ApduError):
    pass


class DataTooShort(ApduError):
    pass


class TrailingBytes(ApduError):
    pass


@dataclass(frozen=True)
class ApduHeader:
    cla: int
    ins: int
    p1: int
    p2: int


@dataclass(frozen=True)
class ApduStatus:
    sw1: int
    sw2: int


@dataclass
class ApduRequest:
    cla: int
    ins: int
    p1: int
    p2: int
    data: bytes  # Since APDU commands don't distinguish between no data and data of zero length, no data is always represented as data of zero length
    le: int | None  # None is interpreted as not expecting any response data

    @classmethod
    def from_header(
        cls, header: ApduHeader, data: bytes = b"", le: int | None = None
    ) -> "ApduRequest":
        return cls(header.cla, header.ins, header.p1, header.p2, data, le)

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ApduRequest":
        return decode_request(raw)

    def __repr__(self) -> str:
        return (
            f"ApduRequest(cla=0x{self.cla:02X}, ins=0x{self.ins:02X}, "
            f"p1=0x{self.p1:02X}, p2=0x{self.p2:02X}, "
            f"data=bytes.fromhex('{self.data.hex()}'), le={self.le})"
        )

    @property
    def header(self) -> ApduHeader:
        return ApduHeader(self.cla, self.ins, self.p1, self.p2)

    @property
    def command(self) -> ApduHeader:
        return self.header

    def get_header(self) -> bytes:
        return bytes([self.cla, self.ins, self.p1, self.p2])

    def to_bytes(self) -> bytes:
        return encode_request(self)


@dataclass
class ApduResponse:
    sw1: int
    sw2: int
    response: bytes  # Since APDU commands don't distinguish between no data and data of zero length, no data is always represented as data of zero length

    @classmethod
    def from_status(cls, status: ApduStatus, data: bytes = b"") -> "ApduResponse":
        return cls(status.sw1, status.sw2, data)

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ApduResponse":
        return decode_response(raw)

    def __repr__(self) -> str:
        return (
            f"ApduResponse(sw1=0x{self.sw1:02X}, sw2=0x{self.sw2:02X}, "
            f"response=bytes.fromhex('{self.response.hex()}'))"
        )

    @property
    def status(self) -> ApduStatus:
        return ApduStatus(self.sw1, self.sw2)

    def to_bytes(self) -> bytes:
        return encode_response(self)


def is_byte(value: int) -> bool:
    return 0 <= value <= 0xFF


def encode_header(raw: bytearray, request: ApduRequest):
    if not is_byte(request.cla):
        raise InvalidCla
    raw.append(request.cla)

    if not is_byte(request.ins):
        raise InvalidIns
    raw.append(request.ins)

    if not is_byte(request.p1):
        raise InvalidP1
    raw.append(request.p1)

    if not is_byte(request.p2):
        raise InvalidP2
    raw.append(request.p2)


def encode_short_lc(raw: bytearray, lc: int):
    if not 0 <= lc <= SHORT_LC_MAX:
        raise InvalidLc
    raw.append(lc)


def encode_short_le(raw: bytearray, le: int):
    if not 1 <= le <= SHORT_LE_MAX:
        raise InvalidLe
    if le == SHORT_LE_MAX:
        raw.append(0)
    else:
        raw.append(le)


def encode_extended_lc(raw: bytearray, lc: int):
    if not 1 <= lc <= EXTENDED_LC_MAX:
        raise InvalidLc
    raw.extend(lc.to_bytes(2, "big"))


def encode_extended_le(raw: bytearray, le: int):
    if not 1 <= le <= EXTENDED_LE_MAX:
        raise InvalidLe
    if le == EXTENDED_LE_MAX:
        raw.extend(bytes(2))
    else:
        raw.extend(le.to_bytes(2, "big"))


def encode_request(request: ApduRequest) -> bytes:
    use_extended = len(request.data) > SHORT_LC_MAX or (
        request.le is not None and request.le > SHORT_LE_MAX
    )

    raw = bytearray()
    encode_header(raw, request)
    if use_extended:
        raw.extend(EXTENDED_LENGTH_MARKER)
        if len(request.data) > 0:
            encode_extended_lc(raw, len(request.data))
            raw.extend(request.data)
        if request.le is not None:
            encode_extended_le(raw, request.le)
    else:
        if len(request.data) > 0:
            encode_short_lc(raw, len(request.data))
            raw.extend(request.data)
        if request.le is not None:
            encode_short_le(raw, request.le)
    return bytes(raw)


def encode_response(response: ApduResponse) -> bytes:
    result = bytearray(response.response)
    result.append(response.sw1)
    result.append(response.sw2)
    return bytes(result)


def decode_short_lc(value: bytes) -> int:
    if not 1 <= value[0] <= SHORT_LC_MAX:
        raise InvalidLc
    return value[0]


def decode_extended_lc(data: bytes) -> int:
    if not 1 <= len(data) <= EXTENDED_LC_MAX:
        raise InvalidLc
    return int.from_bytes(data, "big")


def decode_short_le(value: bytes) -> int:
    if len(value) != 1:
        raise InvalidLe
    byte = value[0]
    return SHORT_LE_MAX if byte == 0 else byte


def decode_extended_le(data: bytes) -> int:
    if len(data) != 2:
        raise InvalidLe
    le = int.from_bytes(data, "big")
    return EXTENDED_LE_MAX if le == 0 else le


def decode_request(raw: bytes) -> ApduRequest:
    if len(raw) < 4:
        raise DataTooShort

    cla, ins, p1, p2 = raw[0], raw[1], raw[2], raw[3]
    body = raw[4:]

    # Case 1
    if len(body) == 0:
        return ApduRequest(cla, ins, p1, p2, data=b"", le=None)

    # Case 2S
    if len(body) == 1:
        le = decode_short_le(body[0:1])
        return ApduRequest(cla, ins, p1, p2, data=b"", le=le)

    # Cases 2E, 3E, 4E
    if body[0:1] == EXTENDED_LENGTH_MARKER:
        data, le = decode_extended_body(body)
        return ApduRequest(cla, ins, p1, p2, data=bytes(data), le=le)

    # Short length cases
    data, le = decode_short_body(body)
    return ApduRequest(cla, ins, p1, p2, data=bytes(data), le=le)


def decode_extended_body(body: bytes) -> tuple[memoryview, int | None]:
    if len(body) < 3:
        raise DataTooShort

    # Case 2E
    if len(body) == 3:
        le = decode_extended_le(body[1:3])
        return memoryview(b""), le

    # Case 3E or Case 4E
    lc = decode_extended_lc(body[1:3])
    data_end = 3 + lc

    if len(body) < data_end:
        raise DataTooShort

    data = memoryview(body)[3:data_end]
    remaining = body[data_end:]

    if len(remaining) == 0:
        # Case 3E
        return data, None

    if len(remaining) == 2:
        # Case 4E
        le = decode_extended_le(remaining)
        return data, le

    raise TrailingBytes


def decode_short_body(body: bytes) -> tuple[memoryview, int | None]:
    lc = decode_short_lc(body[0:1])
    data_end = 1 + lc

    if len(body) < data_end:
        raise DataTooShort

    data = memoryview(body)[1:data_end]
    remaining = body[data_end:]

    if len(remaining) == 0:
        # Case 3S
        return data, None

    if len(remaining) == 1:
        # Case 4S
        le = decode_short_le(remaining[0:1])
        return data, le

    raise TrailingBytes


def decode_response(raw: bytes) -> ApduResponse:
    if len(raw) < 2:
        raise DataTooShort

    sw1 = raw[-2]
    sw2 = raw[-1]
    data = raw[:-2]
    return ApduResponse(sw1, sw2, response=data)
