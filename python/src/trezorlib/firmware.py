# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import hashlib
from enum import Enum
from hashlib import blake2s
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Tuple

import construct as c
import ecdsa

from . import cosi, messages
from .tools import session

if TYPE_CHECKING:
    from .client import TrezorClient

V1_SIGNATURE_SLOTS = 3
V1_BOOTLOADER_KEYS = [
    bytes.fromhex(key)
    for key in (
        "04d571b7f148c5e4232c3814f777d8faeaf1a84216c78d569b71041ffc768a5b2d810fc3bb134dd026b57e65005275aedef43e155f48fc11a32ec790a93312bd58",
        "0463279c0c0866e50c05c799d32bd6bab0188b6de06536d1109d2ed9ce76cb335c490e55aee10cc901215132e853097d5432eda06b792073bd7740c94ce4516cb1",
        "0443aedbb6f7e71c563f8ed2ef64ec9981482519e7ef4f4aa98b27854e8c49126d4956d300ab45fdc34cd26bc8710de0a31dbdf6de7435fd0b492be70ac75fde58",
        "04877c39fd7c62237e038235e9c075dab261630f78eeb8edb92487159fffedfdf6046c6f8b881fa407c4a4ce6c28de0b19c1f4e29f1fcbc5a58ffd1432a3e0938a",
        "047384c51ae81add0a523adbb186c91b906ffb64c2c765802bf26dbd13bdf12c319e80c2213a136c8ee03d7874fd22b70d68e7dee469decfbbb510ee9a460cda45",
    )
]

V2_BOARDLOADER_KEYS = [
    bytes.fromhex(key)
    for key in (
        "0eb9856be9ba7e972c7f34eac1ed9b6fd0efd172ec00faf0c589759da4ddfba0",
        "ac8ab40b32c98655798fd5da5e192be27a22306ea05c6d277cdff4a3f4125cd8",
        "ce0fcd12543ef5936cf2804982136707863d17295faced72af171d6e6513ff06",
    )
]

V2_BOARDLOADER_DEV_KEYS = [
    bytes.fromhex(key)
    for key in (
        "db995fe25169d141cab9bbba92baa01f9f2e1ece7df4cb2ac05190f37fcc1f9d",
        "2152f8d19b791d24453242e15f2eab6cb7cffa7b6a5ed30097960e069881db12",
        "22fc297792f0b6ffc0bfcfdb7edb0c0aa14e025a365ec0e342e86e3829cb74b6",
    )
]

V2_BOOTLOADER_KEYS = [
    bytes.fromhex(key)
    for key in (
        "c2c87a49c5a3460977fbb2ec9dfe60f06bd694db8244bd4981fe3b7a26307f3f",
        "80d036b08739b846f4cb77593078deb25dc9487aedcf52e30b4fb7cd7024178a",
        "b8307a71f552c60a4cbb317ff48b82cdbf6b6bb5f04c920fec7badf017883751",
    )
]

V2_SIGS_REQUIRED = 2

ONEV2_CHUNK_SIZE = 1024 * 64
V2_CHUNK_SIZE = 1024 * 128


def _transform_vendor_trust(data: bytes) -> bytes:
    """Byte-swap and bit-invert the VendorTrust field.

    Vendor trust is interpreted as a bitmask in a 16-bit little-endian integer,
    with the added twist that 0 means set and 1 means unset.
    We feed it to a `BitStruct` that expects a big-endian sequence where bits have
    the traditional meaning. We must therefore do a bitwise negation of each byte,
    and return them in reverse order. This is the same transformation both ways,
    fortunately, so we don't need two separate functions.
    """
    return bytes(~b & 0xFF for b in data)[::-1]


class FirmwareIntegrityError(Exception):
    pass


class InvalidSignatureError(FirmwareIntegrityError):
    pass


class Unsigned(FirmwareIntegrityError):
    pass


class ToifMode(Enum):
    full_color = b"f"
    grayscale = b"g"


class HeaderType(Enum):
    FIRMWARE = b"TRZF"
    BOOTLOADER = b"TRZB"


class EnumAdapter(c.Adapter):
    def __init__(self, subcon: Any, enum: Any) -> None:
        self.enum = enum
        super().__init__(subcon)

    def _encode(self, obj: Any, ctx: Any, path: Any):
        return obj.value

    def _decode(self, obj: Any, ctx: Any, path: Any):
        try:
            return self.enum(obj)
        except ValueError:
            return obj


# fmt: off
Toif = c.Struct(
    "magic" / c.Const(b"TOI"),
    "format" / EnumAdapter(c.Bytes(1), ToifMode),
    "width" / c.Int16ul,
    "height" / c.Int16ul,
    "data" / c.Prefixed(c.Int32ul, c.GreedyBytes),
)


VendorTrust = c.Transformed(c.BitStruct(
    "_reserved" / c.Default(c.BitsInteger(9), 0),
    "show_vendor_string" / c.Flag,
    "require_user_click" / c.Flag,
    "red_background" / c.Flag,
    "delay" / c.BitsInteger(4),
), _transform_vendor_trust, 2, _transform_vendor_trust, 2)


VendorHeader = c.Struct(
    "_start_offset" / c.Tell,
    "magic" / c.Const(b"TRZV"),
    "header_len" / c.Int32ul,
    "expiry" / c.Int32ul,
    "version" / c.Struct(
        "major" / c.Int8ul,
        "minor" / c.Int8ul,
    ),
    "sig_m" / c.Int8ul,
    "sig_n" / c.Rebuild(c.Int8ul, c.len_(c.this.pubkeys)),
    "trust" / VendorTrust,
    "_reserved" / c.Padding(14),
    "pubkeys" / c.Bytes(32)[c.this.sig_n],
    "text" / c.Aligned(4, c.PascalString(c.Int8ul, "utf-8")),
    "image" / Toif,
    "_end_offset" / c.Tell,

    "_min_header_len" / c.Check(c.this.header_len > (c.this._end_offset - c.this._start_offset) + 65),
    "_header_len_aligned" / c.Check(c.this.header_len % 512 == 0),

    c.Padding(c.this.header_len - c.this._end_offset + c.this._start_offset - 65),
    "sigmask" / c.Byte,
    "signature" / c.Bytes(64),
)


VersionLong = c.Struct(
    "major" / c.Int8ul,
    "minor" / c.Int8ul,
    "patch" / c.Int8ul,
    "build" / c.Int8ul,
)


FirmwareHeader = c.Struct(
    "_start_offset" / c.Tell,
    "magic" / EnumAdapter(c.Bytes(4), HeaderType),
    "header_len" / c.Int32ul,
    "expiry" / c.Int32ul,
    "code_length" / c.Rebuild(
        c.Int32ul,
        lambda this:
            len(this._.code) if "code" in this._
            else (this.code_length or 0)
    ),
    "version" / VersionLong,
    "fix_version" / VersionLong,
    "_reserved" / c.Padding(8),
    "hashes" / c.Bytes(32)[16],

    "v1_signatures" / c.Bytes(64)[V1_SIGNATURE_SLOTS],
    "v1_key_indexes" / c.Int8ul[V1_SIGNATURE_SLOTS],  # pylint: disable=E1136

    "_reserved" / c.Padding(220),
    "sigmask" / c.Byte,
    "signature" / c.Bytes(64),

    "_end_offset" / c.Tell,

    "_rebuild_header_len" / c.If(
        c.this.version.major > 1,
        c.Pointer(
            c.this._start_offset + 4,
            c.Rebuild(c.Int32ul, c.this._end_offset - c.this._start_offset)
        ),
    ),
)


"""Raw firmware image.

Consists of firmware header and code block.
This is the expected format of firmware binaries for Trezor One, or bootloader images
for Trezor T."""
FirmwareImage = c.Struct(
    "header" / FirmwareHeader,
    "_code_offset" / c.Tell,
    "code" / c.Bytes(c.this.header.code_length),
    c.Terminated,
)


"""Firmware image prefixed by a vendor header.

This is the expected format of firmware binaries for Trezor T."""
VendorFirmware = c.Struct(
    "vendor_header" / VendorHeader,
    "image" / FirmwareImage,
    c.Terminated,
)


"""Legacy firmware image.
Consists of a custom header and code block.
This is the expected format of firmware binaries for Trezor One pre-1.8.0.

The code block can optionally be interpreted as a new-style firmware image. That is the
expected format of firmware binary for Trezor One version 1.8.0, which can be installed
by both the older and the newer bootloader."""
LegacyFirmware = c.Struct(
    "magic" / c.Const(b"TRZR"),
    "code_length" / c.Rebuild(c.Int32ul, c.len_(c.this.code)),
    "key_indexes" / c.Int8ul[V1_SIGNATURE_SLOTS],  # pylint: disable=E1136
    "flags" / c.BitStruct(
        c.Padding(7),
        "restore_storage" / c.Flag,
    ),
    "_reserved" / c.Padding(52),
    "signatures" / c.Bytes(64)[V1_SIGNATURE_SLOTS],
    "code" / c.Bytes(c.this.code_length),
    c.Terminated,

    "embedded_onev2" / c.RestreamData(c.this.code, c.Optional(FirmwareImage)),
)

# fmt: on


class FirmwareFormat(Enum):
    TREZOR_ONE = 1
    TREZOR_T = 2
    TREZOR_ONE_V2 = 3


ParsedFirmware = Tuple[FirmwareFormat, c.Container]


def parse(data: bytes) -> ParsedFirmware:
    if data[:4] == b"TRZR":
        version = FirmwareFormat.TREZOR_ONE
        cls = LegacyFirmware
    elif data[:4] == b"TRZV":
        version = FirmwareFormat.TREZOR_T
        cls = VendorFirmware
    elif data[:4] == b"TRZF":
        version = FirmwareFormat.TREZOR_ONE_V2
        cls = FirmwareImage
    else:
        raise ValueError("Unrecognized firmware image type")

    try:
        fw = cls.parse(data)
    except Exception as e:
        raise FirmwareIntegrityError("Invalid firmware image") from e
    return version, fw


def digest_onev1(fw: c.Container) -> bytes:
    return hashlib.sha256(fw.code).digest()


def check_sig_v1(
    digest: bytes, key_indexes: List[int], signatures: List[bytes]
) -> None:
    distinct_key_indexes = set(i for i in key_indexes if i != 0)
    if not distinct_key_indexes:
        raise Unsigned

    if len(distinct_key_indexes) < len(key_indexes):
        raise InvalidSignatureError(
            f"Not enough distinct signatures (found {len(distinct_key_indexes)}, need {len(key_indexes)})"
        )

    for i in range(len(key_indexes)):
        key_idx = key_indexes[i] - 1
        signature = signatures[i]

        if key_idx >= len(V1_BOOTLOADER_KEYS):
            # unknown pubkey
            raise InvalidSignatureError(f"Unknown key in slot {i}")

        pubkey = V1_BOOTLOADER_KEYS[key_idx][1:]
        verify = ecdsa.VerifyingKey.from_string(pubkey, curve=ecdsa.curves.SECP256k1)
        try:
            verify.verify_digest(signature, digest)
        except ecdsa.BadSignatureError as e:
            raise InvalidSignatureError(f"Invalid signature in slot {i}") from e


def header_digest(header: c.Container, hash_function: Callable = blake2s) -> bytes:
    stripped_header = header.copy()
    stripped_header.sigmask = 0
    stripped_header.signature = b"\0" * 64
    stripped_header.v1_key_indexes = [0, 0, 0]
    stripped_header.v1_signatures = [b"\0" * 64] * 3
    if header.magic == b"TRZV":
        header_type = VendorHeader
    else:
        header_type = FirmwareHeader
    header_bytes = header_type.build(stripped_header)
    return hash_function(header_bytes).digest()


def digest_v2(fw: c.Container) -> bytes:
    return header_digest(fw.image.header, blake2s)


def digest_onev2(fw: c.Container) -> bytes:
    return header_digest(fw.header, hashlib.sha256)


def calculate_code_hashes(
    code: bytes,
    code_offset: int,
    hash_function: Callable = blake2s,
    chunk_size: int = V2_CHUNK_SIZE,
    padding_byte: Optional[bytes] = None,
) -> List[bytes]:
    hashes = []
    # End offset for each chunk. Normally this would be (i+1)*chunk_size for i-th chunk,
    # but the first chunk is shorter by code_offset, so all end offsets are shifted.
    ends = [(i + 1) * chunk_size - code_offset for i in range(16)]
    start = 0
    for end in ends:
        chunk = code[start:end]
        # padding for last non-empty chunk
        if padding_byte is not None and start < len(code) and end > len(code):
            chunk += padding_byte[0:1] * (end - start - len(chunk))

        if not chunk:
            hashes.append(b"\0" * 32)
        else:
            hashes.append(hash_function(chunk).digest())

        start = end

    return hashes


def validate_code_hashes(fw: c.Container, version: FirmwareFormat) -> None:
    hash_function: Callable
    padding_byte: Optional[bytes]
    if version == FirmwareFormat.TREZOR_ONE_V2:
        image = fw
        hash_function = hashlib.sha256
        chunk_size = ONEV2_CHUNK_SIZE
        padding_byte = b"\xff"
    else:
        image = fw.image
        hash_function = blake2s
        chunk_size = V2_CHUNK_SIZE
        padding_byte = None

    expected_hashes = calculate_code_hashes(
        image.code, image._code_offset, hash_function, chunk_size, padding_byte
    )
    if expected_hashes != image.header.hashes:
        raise FirmwareIntegrityError("Invalid firmware data.")


def validate_onev2(fw: c.Container, allow_unsigned: bool = False) -> None:
    try:
        check_sig_v1(
            digest_onev2(fw),
            fw.header.v1_key_indexes,
            fw.header.v1_signatures,
        )
    except Unsigned:
        if not allow_unsigned:
            raise

    validate_code_hashes(fw, FirmwareFormat.TREZOR_ONE_V2)


def validate_onev1(fw: c.Container, allow_unsigned: bool = False) -> None:
    try:
        check_sig_v1(digest_onev1(fw), fw.key_indexes, fw.signatures)
    except Unsigned:
        if not allow_unsigned:
            raise
    if fw.embedded_onev2:
        validate_onev2(fw.embedded_onev2, allow_unsigned)


def validate_v2(fw: c.Container, skip_vendor_header: bool = False) -> None:
    vendor_fingerprint = header_digest(fw.vendor_header)
    fingerprint = digest_v2(fw)

    if not skip_vendor_header:
        try:
            # if you want to validate a custom vendor header, you can modify
            # the global variables to match your keys and m-of-n scheme
            cosi.verify(
                fw.vendor_header.signature,
                vendor_fingerprint,
                V2_SIGS_REQUIRED,
                V2_BOOTLOADER_KEYS,
                fw.vendor_header.sigmask,
            )
        except Exception:
            raise InvalidSignatureError("Invalid vendor header signature.")

        # XXX expiry is not used now
        # now = time.gmtime()
        # if time.gmtime(fw.vendor_header.expiry) < now:
        #     raise ValueError("Vendor header expired.")

    try:
        cosi.verify(
            fw.image.header.signature,
            fingerprint,
            fw.vendor_header.sig_m,
            fw.vendor_header.pubkeys,
            fw.image.header.sigmask,
        )
    except Exception:
        raise InvalidSignatureError("Invalid firmware signature.")

    # XXX expiry is not used now
    # if time.gmtime(fw.image.header.expiry) < now:
    #     raise ValueError("Firmware header expired.")
    validate_code_hashes(fw, FirmwareFormat.TREZOR_T)


def digest(version: FirmwareFormat, fw: c.Container) -> bytes:
    if version == FirmwareFormat.TREZOR_ONE:
        return digest_onev1(fw)
    elif version == FirmwareFormat.TREZOR_ONE_V2:
        return digest_onev2(fw)
    elif version == FirmwareFormat.TREZOR_T:
        return digest_v2(fw)
    else:
        raise ValueError("Unrecognized firmware version")


def validate(
    version: FirmwareFormat, fw: c.Container, allow_unsigned: bool = False
) -> None:
    if version == FirmwareFormat.TREZOR_ONE:
        return validate_onev1(fw, allow_unsigned)
    elif version == FirmwareFormat.TREZOR_ONE_V2:
        return validate_onev2(fw, allow_unsigned)
    elif version == FirmwareFormat.TREZOR_T:
        return validate_v2(fw)
    else:
        raise ValueError("Unrecognized firmware version")


# ====== Client functions ====== #


@session
def update(
    client: "TrezorClient",
    data: bytes,
    progress_update: Callable[[int], Any] = lambda _: None,
):
    if client.features.bootloader_mode is False:
        raise RuntimeError("Device must be in bootloader mode")

    resp = client.call(messages.FirmwareErase(length=len(data)))

    # TREZORv1 method
    if isinstance(resp, messages.Success):
        resp = client.call(messages.FirmwareUpload(payload=data))
        progress_update(len(data))
        if isinstance(resp, messages.Success):
            return
        else:
            raise RuntimeError(f"Unexpected result {resp}")

    # TREZORv2 method
    while isinstance(resp, messages.FirmwareRequest):
        assert resp.offset is not None
        assert resp.length is not None
        length = resp.length
        payload = data[resp.offset : resp.offset + length]
        digest = blake2s(payload).digest()
        resp = client.call(messages.FirmwareUpload(payload=payload, hash=digest))
        progress_update(length)

    if isinstance(resp, messages.Success):
        return
    else:
        raise RuntimeError(f"Unexpected message {resp}")
