from __future__ import annotations

import hashlib
import typing as t
from enum import IntEnum

import construct as c
from construct_classes import subcon
from typing_extensions import Self

from .. import _ed25519 as ed25519
from ..construct_helpers import EnumAdapter, TupleAdapter
from . import util
from .models import Model, get_nrf_keys
from .sanity_struct import STRICT_SANITY_CHECK_DEFAULT, SanityCheckedStruct

__all__ = ["NrfHeader", "NrfImage"]


NRF_IMAGE_MAGIC = bytes.fromhex("3DB8F396")
NRF_IMAGE_HEADER_SIZE = 32


class TlvType(IntEnum):
    SHA256 = 0x0010
    SIGNATURE1 = 0x00A0
    SIGNATURE2 = 0x00A1
    SIGMASK = 0x00A2
    MODEL = 0x00A3


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
    entries: list[TlvEntry] = subcon(TlvEntry)
    length: int = 4

    SUBCON = c.Struct(
        "magic" / EnumAdapter(c.Int16ul, TlvTableType),
        "length" / c.Int16ul,
        "entries" / c.FixedSized(c.this.length - 4, c.GreedyRange(TlvEntry.SUBCON)),
    )

    def _update_length(self) -> None:
        self.length = sum(len(entry.build()) for entry in self.entries) + 4

    def __post_init__(self) -> None:
        self._update_length()

    def build(self) -> bytes:
        self._update_length()
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
    load_addr: int
    hdr_size: int
    protected_tlv_size: int
    img_size: int
    flags: int
    version: tuple[int, int, int, int]
    _trailing_data: bytes

    SUBCON = c.Struct(
        "_start_offset" / c.Tell,
        "_magic" / c.Const(NRF_IMAGE_MAGIC, c.Bytes(4)),
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
    def trailing_data(self, value: bytes) -> None:
        old_len = len(self._trailing_data)
        self._trailing_data = value
        self.hdr_size += len(value) - old_len

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
        # ...which we can use to figure out the correct length

        assert reparsed is not None

        padding_bytes = bytearray(padding_byte * len(reparsed["_trailing_data"]))
        # XXX hack to get binary identical with imgtool:
        padding_bytes[0:4] = b"\x00\x00\x00\x00"
        return cls(
            load_addr=0,
            hdr_size=header_size,
            protected_tlv_size=0,
            img_size=0,
            flags=flags,
            version=version,
            _trailing_data=bytes(padding_bytes),
        )


class NrfImage(SanityCheckedStruct):
    header: NrfHeader = subcon(NrfHeader)
    img_data: bytes
    protected_tlv: TlvTable = subcon(TlvTable)
    unprotected_tlv: TlvTable = subcon(TlvTable)
    trailer: bytes

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
        self._sync_header_fields()
        self._update_digest()
        self.protected_tlv._update_length()
        self.unprotected_tlv._update_length()
        return super().build()

    def _sync_header_fields(self) -> None:
        self.header.img_size = len(self.img_data)
        self.header.protected_tlv_size = len(self.protected_tlv.build())

    def _verify_integrity(self) -> None:
        if self.protected_tlv.magic != TlvTableType.PROTECTED:
            raise ValueError(
                f"Parsed NrfImage has unexpected magic in protected tlv table: {self.protected_tlv.magic}."
            )
        if self.unprotected_tlv.magic != TlvTableType.UNPROTECTED:
            raise ValueError(
                f"Parsed NrfImage has unexpected magic in unprotected tlv table: {self.unprotected_tlv.magic}."
            )
        if len(self.protected_tlv.build()) != self.header.protected_tlv_size:
            raise ValueError(
                f"Parsed NrfImage has invalid protected_tlv_size: {self.header.protected_tlv_size}."
            )
        if self.trailer != b"":
            raise ValueError(
                f"Parsed NrfImage has invalid trailer data: {self.trailer}."
            )

    def _update_digest(self) -> None:
        self.unprotected_tlv[TlvType.SHA256] = self.digest()

    def digest(self) -> bytes:
        self._sync_header_fields()
        hasher = hashlib.sha256()
        hasher.update(self.header.build())
        hasher.update(self.img_data)
        hasher.update(self.protected_tlv.build())
        return hasher.digest()

    @property
    def model(self) -> Model:
        return Model(self.protected_tlv[TlvType.MODEL])

    @model.setter
    def model(self, model: Model) -> None:
        self.protected_tlv[TlvType.MODEL] = model.value

    @property
    def sigmask(self) -> int:
        return int.from_bytes(self.protected_tlv[TlvType.SIGMASK], "little")

    def insert_sigmask(self, sigmask: int) -> None:
        self.protected_tlv[TlvType.SIGMASK] = sigmask.to_bytes(1, "little")
        self._update_digest()

    def set_signatures(self, signatures: tuple[bytes, bytes]) -> None:
        self.unprotected_tlv[TlvType.SIGNATURE1] = signatures[0]
        self.unprotected_tlv[TlvType.SIGNATURE2] = signatures[1]

    def public_keys(self, dev_keys: bool = False) -> t.Sequence[bytes]:
        return get_nrf_keys(self.model, dev_keys)

    @classmethod
    def create(
        cls,
        *,
        version: tuple[int, int, int, int],
        model: Model,
        img_data: bytes,
        header_size: int,
        flags: int = 0,
        padding_byte: bytes = b"\xff",
        sigmask: int = 0x03,
    ) -> Self:
        header = NrfHeader.create(
            version=version,
            header_size=header_size,
            flags=flags,
            padding_byte=padding_byte,
        )
        image = cls(
            header=header,
            img_data=img_data,
            protected_tlv=TlvTable(magic=TlvTableType.PROTECTED, entries=[]),
            unprotected_tlv=TlvTable(magic=TlvTableType.UNPROTECTED, entries=[]),
            trailer=b"",
        )
        image.insert_sigmask(sigmask)
        image.model = model

        # keep SHA256 TLV aligned with current content
        image._update_digest()
        return image

    def verify(self, dev_keys: bool = False) -> None:
        digest = self.digest()
        sigmask = self.sigmask
        keys = self.public_keys(dev_keys)
        signature_1 = self.unprotected_tlv[TlvType.SIGNATURE1]
        signature_2 = self.unprotected_tlv[TlvType.SIGNATURE2]

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
