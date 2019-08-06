# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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
from typing import Callable, List, NewType, Tuple

import construct as c
import ecdsa
import pyblake2

from . import cosi, messages, tools

V1_SIGNATURE_SLOTS = 3
V1_BOOTLOADER_KEYS = {
    1: "04d571b7f148c5e4232c3814f777d8faeaf1a84216c78d569b71041ffc768a5b2d810fc3bb134dd026b57e65005275aedef43e155f48fc11a32ec790a93312bd58",
    2: "0463279c0c0866e50c05c799d32bd6bab0188b6de06536d1109d2ed9ce76cb335c490e55aee10cc901215132e853097d5432eda06b792073bd7740c94ce4516cb1",
    3: "0443aedbb6f7e71c563f8ed2ef64ec9981482519e7ef4f4aa98b27854e8c49126d4956d300ab45fdc34cd26bc8710de0a31dbdf6de7435fd0b492be70ac75fde58",
    4: "04877c39fd7c62237e038235e9c075dab261630f78eeb8edb92487159fffedfdf6046c6f8b881fa407c4a4ce6c28de0b19c1f4e29f1fcbc5a58ffd1432a3e0938a",
    5: "047384c51ae81add0a523adbb186c91b906ffb64c2c765802bf26dbd13bdf12c319e80c2213a136c8ee03d7874fd22b70d68e7dee469decfbbb510ee9a460cda45",
}

V2_BOOTLOADER_KEYS = [
    bytes.fromhex("c2c87a49c5a3460977fbb2ec9dfe60f06bd694db8244bd4981fe3b7a26307f3f"),
    bytes.fromhex("80d036b08739b846f4cb77593078deb25dc9487aedcf52e30b4fb7cd7024178a"),
    bytes.fromhex("b8307a71f552c60a4cbb317ff48b82cdbf6b6bb5f04c920fec7badf017883751"),
]
V2_BOOTLOADER_M = 2
V2_BOOTLOADER_N = 3

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


# fmt: off
Toif = c.Struct(
    "magic" / c.Const(b"TOI"),
    "format" / c.Enum(c.Byte, full_color=b"f", grayscale=b"g"),
    "width" / c.Int16ul,
    "height" / c.Int16ul,
    "data" / c.Prefixed(c.Int32ul, c.GreedyBytes),
)


VendorTrust = c.Transformed(c.BitStruct(
    "reserved" / c.Default(c.BitsInteger(9), 0),
    "show_vendor_string" / c.Flag,
    "require_user_click" / c.Flag,
    "red_background" / c.Flag,
    "delay" / c.BitsInteger(4),
), _transform_vendor_trust, 2, _transform_vendor_trust, 2)


VendorHeader = c.Struct(
    "_start_offset" / c.Tell,
    "magic" / c.Const(b"TRZV"),
    "_header_len" / c.Padding(4),
    "expiry" / c.Int32ul,
    "version" / c.Struct(
        "major" / c.Int8ul,
        "minor" / c.Int8ul,
    ),
    "vendor_sigs_required" / c.Int8ul,
    "vendor_sigs_n" / c.Rebuild(c.Int8ul, c.len_(c.this.pubkeys)),
    "vendor_trust" / VendorTrust,
    "reserved" / c.Padding(14),
    "pubkeys" / c.Bytes(32)[c.this.vendor_sigs_n],
    "vendor_string" / c.Aligned(4, c.PascalString(c.Int8ul, "utf-8")),
    "vendor_image" / Toif,
    "_data_end_offset" / c.Tell,

    c.Padding(-(c.this._data_end_offset + 65) % 512),
    "sigmask" / c.Byte,
    "signature" / c.Bytes(64),

    "_end_offset" / c.Tell,
    "header_len" / c.Pointer(
        c.this._start_offset + 4,
        c.Rebuild(c.Int32ul, c.this._end_offset - c.this._start_offset)
    ),
)


VersionLong = c.Struct(
    "major" / c.Int8ul,
    "minor" / c.Int8ul,
    "patch" / c.Int8ul,
    "build" / c.Int8ul,
)


FirmwareHeader = c.Struct(
    "_start_offset" / c.Tell,
    "magic" / c.Const(b"TRZF"),
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
    "reserved" / c.Padding(8),
    "hashes" / c.Bytes(32)[16],

    "v1_signatures" / c.Bytes(64)[V1_SIGNATURE_SLOTS],
    "v1_key_indexes" / c.Int8ul[V1_SIGNATURE_SLOTS],  # pylint: disable=E1136

    "reserved" / c.Padding(220),
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


Firmware = c.Struct(
    "vendor_header" / VendorHeader,
    "firmware_header" / FirmwareHeader,
    "_code_offset" / c.Tell,
    "code" / c.Bytes(c.this.firmware_header.code_length),
    c.Terminated,
)


FirmwareOneV2 = c.Struct(
    "firmware_header" / FirmwareHeader,
    "_code_offset" / c.Tell,
    "code" / c.Bytes(c.this.firmware_header.code_length),
    c.Terminated,
)


FirmwareOne = c.Struct(
    "magic" / c.Const(b"TRZR"),
    "code_length" / c.Rebuild(c.Int32ul, c.len_(c.this.code)),
    "key_indexes" / c.Int8ul[V1_SIGNATURE_SLOTS],  # pylint: disable=E1136
    "flags" / c.BitStruct(
        c.Padding(7),
        "restore_storage" / c.Flag,
    ),
    "reserved" / c.Padding(52),
    "signatures" / c.Bytes(64)[V1_SIGNATURE_SLOTS],
    "code" / c.Bytes(c.this.code_length),
    c.Terminated,

    "embedded_onev2" / c.RestreamData(c.this.code, c.Optional(FirmwareOneV2)),
)

# fmt: on


class FirmwareFormat(Enum):
    TREZOR_ONE = 1
    TREZOR_T = 2
    TREZOR_ONE_V2 = 3


FirmwareType = NewType("FirmwareType", c.Container)
ParsedFirmware = Tuple[FirmwareFormat, FirmwareType]


def parse(data: bytes) -> ParsedFirmware:
    if data[:4] == b"TRZR":
        version = FirmwareFormat.TREZOR_ONE
        cls = FirmwareOne
    elif data[:4] == b"TRZV":
        version = FirmwareFormat.TREZOR_T
        cls = Firmware
    elif data[:4] == b"TRZF":
        version = FirmwareFormat.TREZOR_ONE_V2
        cls = FirmwareOneV2
    else:
        raise ValueError("Unrecognized firmware image type")

    try:
        fw = cls.parse(data)
    except Exception as e:
        raise FirmwareIntegrityError("Invalid firmware image") from e
    return version, FirmwareType(fw)


def digest_onev1(fw: FirmwareType) -> bytes:
    return hashlib.sha256(fw.code).digest()


def check_sig_v1(
    digest: bytes, key_indexes: List[int], signatures: List[bytes]
) -> None:
    distinct_key_indexes = set(i for i in key_indexes if i != 0)
    if not distinct_key_indexes:
        raise Unsigned

    if len(distinct_key_indexes) < len(key_indexes):
        raise InvalidSignatureError(
            "Not enough distinct signatures (found {}, need {})".format(
                len(distinct_key_indexes), len(key_indexes)
            )
        )

    for i in range(len(key_indexes)):
        key_idx = key_indexes[i]
        signature = signatures[i]

        if key_idx not in V1_BOOTLOADER_KEYS:
            # unknown pubkey
            raise InvalidSignatureError("Unknown key in slot {}".format(i))

        pubkey = bytes.fromhex(V1_BOOTLOADER_KEYS[key_idx])[1:]
        verify = ecdsa.VerifyingKey.from_string(pubkey, curve=ecdsa.curves.SECP256k1)
        try:
            verify.verify_digest(signature, digest)
        except ecdsa.BadSignatureError as e:
            raise InvalidSignatureError("Invalid signature in slot {}".format(i)) from e


def _header_digest(
    header: c.Container,
    header_type: c.Construct,
    hash_function: Callable = pyblake2.blake2s,
) -> bytes:
    stripped_header = header.copy()
    stripped_header.sigmask = 0
    stripped_header.signature = b"\0" * 64
    stripped_header.v1_key_indexes = [0, 0, 0]
    stripped_header.v1_signatures = [b"\0" * 64] * 3
    header_bytes = header_type.build(stripped_header)
    return hash_function(header_bytes).digest()


def digest_v2(fw: FirmwareType) -> bytes:
    return _header_digest(fw.firmware_header, FirmwareHeader, pyblake2.blake2s)


def digest_onev2(fw: FirmwareType) -> bytes:
    return _header_digest(fw.firmware_header, FirmwareHeader, hashlib.sha256)


def validate_code_hashes(
    fw: FirmwareType,
    hash_function: Callable = pyblake2.blake2s,
    chunk_size: int = V2_CHUNK_SIZE,
    padding_byte: bytes = None,
) -> None:
    for i, expected_hash in enumerate(fw.firmware_header.hashes):
        if i == 0:
            # Because first chunk is sent along with headers, there is less code in it.
            chunk = fw.code[: chunk_size - fw._code_offset]
        else:
            # Subsequent chunks are shifted by the "missing header" size.
            ptr = i * chunk_size - fw._code_offset
            chunk = fw.code[ptr : ptr + chunk_size]

        # padding for last chunk
        if padding_byte is not None and i > 1 and chunk and len(chunk) < chunk_size:
            chunk += padding_byte[0:1] * (chunk_size - len(chunk))

        if not chunk and expected_hash == b"\0" * 32:
            continue
        chunk_hash = hash_function(chunk).digest()
        if chunk_hash != expected_hash:
            raise FirmwareIntegrityError("Invalid firmware data.")


def validate_onev2(fw: FirmwareType, allow_unsigned: bool = False) -> None:
    try:
        check_sig_v1(
            digest_onev2(fw),
            fw.firmware_header.v1_key_indexes,
            fw.firmware_header.v1_signatures,
        )
    except Unsigned:
        if not allow_unsigned:
            raise

    validate_code_hashes(
        fw,
        hash_function=hashlib.sha256,
        chunk_size=ONEV2_CHUNK_SIZE,
        padding_byte=b"\xFF",
    )


def validate_onev1(fw: FirmwareType, allow_unsigned: bool = False) -> None:
    try:
        check_sig_v1(digest_onev1(fw), fw.key_indexes, fw.signatures)
    except Unsigned:
        if not allow_unsigned:
            raise
    if fw.embedded_onev2:
        validate_onev2(fw.embedded_onev2, allow_unsigned)


def validate_v2(fw: FirmwareType, skip_vendor_header: bool = False) -> None:
    vendor_fingerprint = _header_digest(fw.vendor_header, VendorHeader)
    fingerprint = digest_v2(fw)

    if not skip_vendor_header:
        try:
            # if you want to validate a custom vendor header, you can modify
            # the global variables to match your keys and m-of-n scheme
            cosi.verify_m_of_n(
                fw.vendor_header.signature,
                vendor_fingerprint,
                V2_BOOTLOADER_M,
                V2_BOOTLOADER_N,
                fw.vendor_header.sigmask,
                V2_BOOTLOADER_KEYS,
            )
        except Exception:
            raise InvalidSignatureError("Invalid vendor header signature.")

        # XXX expiry is not used now
        # now = time.gmtime()
        # if time.gmtime(fw.vendor_header.expiry) < now:
        #     raise ValueError("Vendor header expired.")

    try:
        cosi.verify_m_of_n(
            fw.firmware_header.signature,
            fingerprint,
            fw.vendor_header.vendor_sigs_required,
            fw.vendor_header.vendor_sigs_n,
            fw.firmware_header.sigmask,
            fw.vendor_header.pubkeys,
        )
    except Exception:
        raise InvalidSignatureError("Invalid firmware signature.")

    # XXX expiry is not used now
    # if time.gmtime(fw.firmware_header.expiry) < now:
    #     raise ValueError("Firmware header expired.")
    validate_code_hashes(fw)


def digest(version: FirmwareFormat, fw: FirmwareType) -> bytes:
    if version == FirmwareFormat.TREZOR_ONE:
        return digest_onev1(fw)
    elif version == FirmwareFormat.TREZOR_ONE_V2:
        return digest_onev2(fw)
    elif version == FirmwareFormat.TREZOR_T:
        return digest_v2(fw)
    else:
        raise ValueError("Unrecognized firmware version")


def validate(
    version: FirmwareFormat, fw: FirmwareType, allow_unsigned: bool = False
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


@tools.session
def update(client, data):
    if client.features.bootloader_mode is False:
        raise RuntimeError("Device must be in bootloader mode")

    resp = client.call(messages.FirmwareErase(length=len(data)))

    # TREZORv1 method
    if isinstance(resp, messages.Success):
        resp = client.call(messages.FirmwareUpload(payload=data))
        if isinstance(resp, messages.Success):
            return
        else:
            raise RuntimeError("Unexpected result %s" % resp)

    # TREZORv2 method
    while isinstance(resp, messages.FirmwareRequest):
        payload = data[resp.offset : resp.offset + resp.length]
        digest = pyblake2.blake2s(payload).digest()
        resp = client.call(messages.FirmwareUpload(payload=payload, hash=digest))

    if isinstance(resp, messages.Success):
        return
    else:
        raise RuntimeError("Unexpected message %s" % resp)
