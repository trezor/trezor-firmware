# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

from __future__ import annotations

import hashlib
import typing as t
from dataclasses import asdict
from enum import IntEnum

import click
import construct as c
from construct_classes import subcon
from .. import _ed25519 as ed25519
from ..construct_helpers import EnumAdapter, TupleAdapter
from typing_extensions import Self

from .core import HeaderType

from . import models as fw_models
from .sanity_struct import STRICT_SANITY_CHECK_DEFAULT, SanityCheckedStruct
from .firmware_headers import (
    SYM_FAIL,
    SYM_OK,
    LiteralStr,
    check_signature_any,
    chunkify,
    format_container,
)
from .import util

Ed25519Signature = bytes
Ed25519PublicPoint = bytes

IMAGE_MAGIC = HeaderType.NRF_FIRMWARE.value
IMAGE_HEADER_SIZE = 32


class TlvType(IntEnum):
    SHA256 = 0x0010
    SIGNATURE1 = 0x00A0
    SIGNATURE2 = 0x00A1
    SIGMASK = 0x00A2
    TREZOR_MODEL = 0x00A3


class TlvTableType(IntEnum):
    PROTECTED = 0x6908
    UNPROTECTED = 0x6907


class TlvEntry(SanityCheckedStruct):
    id: int | TlvType
    data: bytes

    SUBCON = c.Struct(
        "id" / EnumAdapter(c.Int16ul, TlvType),
        "data" / c.Prefixed(c.Int16ul, c.GreedyBytes),
    )


class TlvTable(SanityCheckedStruct):
    magic: TlvTableType
    length: int
    entries: list[TlvEntry] = subcon(TlvEntry)

    SUBCON = c.Struct(
        "magic" / EnumAdapter(c.Int16ul, TlvTableType),
        "length" / c.Int16ul,
        "entries" / c.FixedSized(c.this.length - 4, c.GreedyRange(TlvEntry.SUBCON)),
    )

    def _update_length(self) -> None:
        self.length = sum(len(entry.build()) for entry in self.entries) + 4

    def build(self) -> bytes:
        entries_len = sum(len(entry.build()) for entry in self.entries)
        self.length = entries_len + 4
        return super().build()

    def __getitem__(self, key: TlvType) -> bytes:
        for entry in self.entries:
            if entry.id == key:
                return entry.data
        raise KeyError(f"TlvType {key} not found")

    def __setitem__(self, key: TlvType, value: bytes) -> None:
        for entry in self.entries:
            if entry.id == key:
                entry.data = value
                return

        self.entries.append(TlvEntry(id=key, data=value))

    def __delitem__(self, key: TlvType) -> None:
        for i, entry in enumerate(self.entries):
            if entry.id == key:
                del self.entries[i]
                return
        raise KeyError(f"TlvType {key} not found")

    def __contains__(self, key: TlvType) -> bool:
        return any(entry.id == key for entry in self.entries)


class NrfHeader(SanityCheckedStruct):
    magic: bytes
    load_addr: int
    hdr_size: int
    protected_tlv_size: int
    img_size: int
    flags: int
    version: tuple[int, int, int, int]
    _trailing_data: bytes

    SUBCON = c.Struct(
        "_start_offset" / c.Tell,
        "magic" / c.Const(IMAGE_MAGIC, c.Bytes(4)),
        "load_addr" / c.Int32ul,
        "hdr_size" / c.Int16ul,
        "protected_tlv_size" / c.Int16ul,
        "img_size" / c.Int32ul,
        "flags" / c.Int32ul,
        "version" / TupleAdapter(c.Int8ul, c.Int8ul, c.Int16ul, c.Int32ul),
        "_hdr_known_end" / c.Tell,
        "_trailing_data"
        / c.Default(
            c.Bytes(c.this.hdr_size - c.this._hdr_known_end + c.this._start_offset),
            b"\x00" * (c.this.hdr_size - c.this._hdr_known_end + c.this._start_offset),
        ),
    )

    @property
    def trailing_data(self) -> bytes:
        return self._trailing_data

    @trailing_data.setter
    def trailing_data(self, value: bytes):
        self._trailing_data = value
        self.hdr_size = len(self.build())

    @classmethod
    def create(
        cls,
        *,
        version: tuple[int, int, int, int],
        header_size: int,
        flags: int = 0,
        padding_byte: bytes = b"\x00",
    ) -> Self:
        # explicitly build the subcon without providing trailing_data
        header_empty = cls.SUBCON.build(
            dict(
                load_addr=0,
                hdr_size=header_size,
                protected_tlv_size=0,
                img_size=0,
                flags=flags,
                version=version,
            )
        )
        # re-parsing will pick out the default value
        reparsed = cls.SUBCON.parse(header_empty)
        assert reparsed is not None

        # ...which we can use to figure out the correct length
        padding_bytes = bytearray(padding_byte * len(reparsed["_trailing_data"]))
        # XXX hack to get binary identical with imgtool:
        padding_bytes[0:4] = b"\x00\x00\x00\x00"
        return cls(
            magic = IMAGE_MAGIC,
            load_addr=0,
            hdr_size=header_size,
            protected_tlv_size=0,
            img_size=0,
            flags=flags,
            version=version,
            _trailing_data=bytes(padding_bytes),
        )


class NrfImage(SanityCheckedStruct):
    NAME: t.ClassVar[str] = "nrf"

    header: NrfHeader = subcon(NrfHeader)
    img_data: bytes
    protected_tlv: TlvTable = subcon(TlvTable)
    unprotected_tlv: TlvTable = subcon(TlvTable)
    trailer: bytes

    def signature_present(self) -> bool:
        return (
            TlvType.SIGNATURE1 in self.unprotected_tlv
            and TlvType.SIGNATURE2 in self.unprotected_tlv
        )

    SUBCON = c.Struct(
        "header" / NrfHeader.SUBCON,
        "img_data" / c.Bytes(c.this.header.img_size),
        "protected_tlv" / TlvTable.SUBCON,
        "unprotected_tlv" / TlvTable.SUBCON,
        "trailer" / c.GreedyBytes,
    )

    @classmethod
    def parse(cls, data: bytes, *, strict: bool = STRICT_SANITY_CHECK_DEFAULT) -> Self:
        parsed = super().parse(data, strict=strict)
        parsed._verify_integrity()
        return parsed

    def build(self) -> bytes:
        self.header.img_size = len(self.img_data)
        self.header.protected_tlv_size = len(self.protected_tlv.build())
        self._update_digest()
        self.protected_tlv._update_length()
        self.unprotected_tlv._update_length()
        return super().build()

    def _verify_integrity(self) -> None:
        assert self.protected_tlv.magic == TlvTableType.PROTECTED
        assert self.unprotected_tlv.magic == TlvTableType.UNPROTECTED
        assert len(self.protected_tlv.build()) == self.header.protected_tlv_size
        assert self.trailer == b""

    def _update_digest(self) -> None:
        self.unprotected_tlv[TlvType.SHA256] = self.digest()

    def digest(self) -> bytes:
        hasher = hashlib.sha256()
        hasher.update(self.header.build())
        hasher.update(self.img_data)
        hasher.update(self.protected_tlv.build())
        digest = hasher.digest()
        return digest

    @property
    def model(self) -> fw_models.Model:
        return fw_models.Model(self.protected_tlv[TlvType.TREZOR_MODEL]) # Will this work as expected?

    @property
    def sigmask(self) -> int:
        return int.from_bytes(self.protected_tlv[TlvType.SIGMASK], "little")

    @sigmask.setter
    def sigmask(self, sigmask: int) -> None:
        self.protected_tlv[TlvType.SIGMASK] = sigmask.to_bytes(1, "little")
        self.unprotected_tlv[TlvType.SHA256] = self.digest()

    def insert_sigmask(self, sigmask: int) -> None:
        self.sigmask = sigmask
        self._update_digest()

    def set_signatures(self, signatures: tuple[bytes, bytes]) -> None:
        self.unprotected_tlv[TlvType.SIGNATURE1] = signatures[0]
        self.unprotected_tlv[TlvType.SIGNATURE2] = signatures[1]

    def verify(self, dev_keys: bool = False) -> None:
        public_keys = self.public_keys(dev_keys)
        _verify(
            signature_1=self.unprotected_tlv[TlvType.SIGNATURE1],
            signature_2=self.unprotected_tlv[TlvType.SIGNATURE2],
            digest=self.digest(),
            keys=public_keys,
            sigmask=self.sigmask,
        )

    def format(self, verbose: bool = False) -> str:

        header_str = _format_header(self.header)
        image_str = f"Image data: {len(self.img_data)} bytes"
        tlvs_str = _format_tlvs(self.protected_tlv, self.unprotected_tlv)
        fingerprint_str = (
            f"Calculated fingerprint: {click.style(chunkify(self.digest()), bold=True)}"
        )
        sig_result = check_signature_any(self)
        sig_ok = SYM_OK if sig_result.is_ok() else SYM_FAIL
        sig_str = f"{sig_ok} Signature is {sig_result.value}"

        return "\n".join(
            [
                header_str,
                image_str,
                tlvs_str,
                fingerprint_str,
                sig_str,
            ]
        )

    def get_header(self) -> t.Any:
        return self.header

    def public_keys(self, dev_keys: bool = False) -> t.Sequence[bytes]:
        return fw_models.get_nrf_keys(self.model, dev_keys)


def _verify(
    signature_1: Ed25519Signature,
    signature_2: Ed25519Signature,
    digest: bytes,
    keys: t.Sequence[Ed25519PublicPoint],
    sigmask: int,
) -> None:
    if sigmask.bit_length() > len(keys):
        raise ValueError("Sigmask specifies more public keys than provided.")
    selected_keys = [key for i, key in enumerate(keys) if sigmask & (1 << i)]
    if len(selected_keys) != 2:
        raise ValueError("Sigmask does not specify two keys.")
    try:
        ed25519.checkvalid(signature_1, digest, selected_keys[0])
        ed25519.checkvalid(signature_2, digest, selected_keys[1])
    except ed25519.SignatureMismatch as e:
        raise util.InvalidSignatureError("Invalid signature") from e

def _format_header(header: NrfHeader) -> str:
    header_dict = asdict(header)
    header_out = header_dict.copy()

    for key, val in header_out.items():
        if "version" in key:
            header_out[key] = LiteralStr(_format_version_nRF(val))
        if "magic" in key:
            header_out[key] = LiteralStr(HeaderType(val))

    return "NrfHeader " + format_container(header_out)


def _format_version_nRF(version: tuple[int, int, int, int]) -> str:
    return "{}.{}.{}+{}".format(*version)


def _format_tlvs(
    *tlv_tables: TlvTable,
    padding: str = " " * 4,
) -> str:
    total_size = 0
    for table in tlv_tables:
        total_size += table.length

    output = [
        f"TLVs (count: {len(tlv_tables)}, total_size: {_bytes_str(total_size)}) {{"
    ]

    def _add(s: str, depth=1) -> None:
        output.append(padding * depth + s)

    for tlv in tlv_tables:
        type_name = tlv.magic.name
        _add(f"{type_name} ({_bytes_str(tlv.length)}) {{")

        for entry in tlv.entries:
            if isinstance(entry.id, TlvType):
                name = entry.id.name
            else:
                name = f"unrecognized {entry.id}"
            if len(entry.data) > 64:
                data = entry.data[:64].hex() + "..."
            elif isinstance(entry.id, TlvType) and entry.id.name == "TREZOR_MODEL":
                data = f"{entry.data.decode()} ({entry.data.hex()})"
            else:
                data = entry.data.hex()
            _add(f"{name}: ({_bytes_str(len(entry.data))}) {data}", depth=2)
        _add("}")
    return "\n".join(output) + "\n}"


def _bytes_str(length: int) -> str:
    if length == 1:
        return f"{length} byte"
    return f"{length} bytes"
