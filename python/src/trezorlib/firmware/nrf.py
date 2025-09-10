from __future__ import annotations

import hashlib
from enum import IntEnum

import construct as c
from construct_classes import Struct, subcon
from typing_extensions import Self

from .. import _ed25519 as ed25519
from ..tools import EnumAdapter, TupleAdapter
from . import util
from .models import Model

__all__ = ["NrfImage", "NrfHeader"]

IMAGE_MAGIC = 0x96F3B83D
IMAGE_HEADER_SIZE = 32

NRF_DEV_KEYS = [
    bytes.fromhex(k)
    for k in (
        "d759793bbc13a2819a827c76adb6fba8a49aee007f49f2d0992d99b825ad2c48",
        "6355691c178a8ff91007a7478afb955ef7352c63e7b25703984cf78b26e21a56",
    )
]
NRF_KEYS = [
    bytes.fromhex(k)
    for k in (
        "d1bad5e8c73dfe183ba1bd5464b2c96f1d1de66d53c95026d17169148d096f3e",
        "585f0635efc6518c490228a72ae1f5d0808ebe77f1c12516eb6d525821eb1e21",
        "065ee19b0de4eec3be70938935313ca2949cc3808b2bf3ad7ef0ac419a974191",
    )
]


class TlvType(IntEnum):
    SHA256 = 0x0010
    SIGNATURE1 = 0x00A0
    SIGNATURE2 = 0x00A1
    SIGMASK = 0x00A2
    MODEL = 0x00A3


class TlvTableType(IntEnum):
    PROTECTED = 0x6908
    UNPROTECTED = 0x6907


class TlvEntry(Struct):
    id: int | TlvType
    data: bytes

    SUBCON = c.Struct(
        "id" / EnumAdapter(c.Int16ul, TlvType),
        "data" / c.Prefixed(c.Int16ul, c.GreedyBytes),
    )


class TlvTable(Struct):
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
        self.entries = [entry for entry in self.entries if entry.id != key]

    def __contains__(self, key: TlvType) -> bool:
        return any(entry.id == key for entry in self.entries)


class NrfHeader(Struct):
    load_addr: int
    hdr_size: int
    protected_tlv_size: int
    img_size: int
    flags: int
    version: tuple[int, int, int, int]
    _trailing_data: bytes

    SUBCON = c.Struct(
        "_start_offset" / c.Tell,
        "magic" / c.Const(IMAGE_MAGIC, c.Int32ul),
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
        reparsed = cls.SUBCON.parse(header_empty)
        # re-parsing will pick out the default value
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
            # ...which we can use to figure out the correct length
            _trailing_data=padding_bytes,
        )


class NrfImage(Struct):
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
    def parse(cls, data: bytes) -> Self:
        parsed = super().parse(data)
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
        return hasher.digest()

    @property
    def sigmask(self) -> int:
        return int.from_bytes(self.protected_tlv[TlvType.SIGMASK], "little")

    @sigmask.setter
    def sigmask(self, sigmask: int) -> None:
        self.protected_tlv[TlvType.SIGMASK] = sigmask.to_bytes(1, "little")
        self._update_digest()

    def set_signatures(self, signatures: tuple[bytes, bytes]) -> None:
        self.unprotected_tlv[TlvType.SIGNATURE1] = signatures[0]
        self.unprotected_tlv[TlvType.SIGNATURE2] = signatures[1]

    @property
    def model(self) -> Model:
        model_bytes = self.protected_tlv[TlvType.MODEL]
        return Model.from_bytes(model_bytes)

    @model.setter
    def model(self, model: Model) -> None:
        self.protected_tlv[TlvType.MODEL] = model.value

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
        image.sigmask = sigmask
        image.model = model
        # force update of digest
        image.digest()
        return image

    def verify(self, dev_keys: bool = False) -> None:
        digest = self.digest()
        sigmask = self.sigmask
        model_keys = NRF_DEV_KEYS if dev_keys else NRF_KEYS
        indexes = []
        for i in range(8):
            if sigmask & (1 << i):
                indexes.append(i)

        if len(indexes) != 2:
            raise util.InvalidSignatureError("Invalid sigmask")

        sig1 = self.unprotected_tlv[TlvType.SIGNATURE1]
        sig2 = self.unprotected_tlv[TlvType.SIGNATURE2]
        try:
            ed25519.checkvalid(sig1, digest, model_keys[indexes[0]])
            ed25519.checkvalid(sig2, digest, model_keys[indexes[1]])
        except ed25519.SignatureMismatch as e:
            raise util.InvalidSignatureError("Invalid signature") from e
