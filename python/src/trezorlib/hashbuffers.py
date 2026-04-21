"""Bridge between trezorlib protobuf MessageType classes and Hashbuffers."""

from __future__ import annotations

import typing as t
from enum import IntEnum

from hashbuffers.codec import Block, TableBlock
from hashbuffers.codec.table import NULL_ENTRY, BlockEntry, TableEntry
from hashbuffers.data_model.common import (
    BlockDecoderType,
    FieldType,
    resolve_entry_to_block,
)
from hashbuffers.fitting import Table
from hashbuffers.schema import (
    I32,
    I64,
    U16,
    U32,
    U64,
    Array,
    Bool,
    Bytes,
    EnumType,
    String,
)
from hashbuffers.store import BlockStore

from . import protobuf, messages

MT = t.TypeVar("MT", bound=protobuf.MessageType)
_TXACK_SINGLETON_TRANSACTION_FIELDS = {"inputs", "bin_outputs", "outputs"}


class _MessageRef(BlockDecoderType[MT]):
    def __init__(self, msg_type: type[MT]) -> None:
        self.msg_type = msg_type

    def encode(self, value: MT, store: BlockStore) -> TableEntry:
        return _serialize_entry(value, store)

    def decode(self, entry: TableEntry, store: BlockStore) -> MT:
        block = resolve_entry_to_block(entry, store)
        return self.block_decoder(store)(block)

    def block_decoder(self, store: BlockStore) -> t.Callable[[Block], MT]:
        def decode_block(block: Block) -> MT:
            if not isinstance(block, TableBlock):
                raise ValueError(f"Expected TABLE block, got {type(block)}")
            return _deserialize_from_table(self.msg_type, block, store)

        return decode_block


# Protobuf type name -> hashbuffers schema type
_PROTO_TYPE_MAP: dict[str, FieldType[t.Any]] = {
    "uint32": U32,
    "uint64": U64,
    "sint32": I32,
    "sint64": I64,
    "bool": Bool,
    "bytes": Bytes,
    "string": String,
}


def _is_txack_singleton_field(
    msg_type: type["protobuf.MessageType"], field: "protobuf.Field"
) -> bool:
    return (
        issubclass(msg_type, messages.TransactionType)
        and field.repeated
        and field.name in _TXACK_SINGLETON_TRANSACTION_FIELDS
    )


def _hb_type_for_field(
    field: "protobuf.Field", *, force_non_repeated: bool = False
) -> FieldType[t.Any]:
    hb_type = _PROTO_TYPE_MAP.get(field.proto_type)
    if hb_type is not None:
        if field.repeated and not force_non_repeated:
            return Array(hb_type)
        return hb_type

    py_type = field.py_type

    if issubclass(py_type, IntEnum):
        enum_type = EnumType(py_type, U16)
        if field.repeated and not force_non_repeated:
            return Array(enum_type)
        return enum_type

    msg_type = _MessageRef(py_type)
    if field.repeated and not force_non_repeated:
        return Array(msg_type)
    return msg_type


def _serialize_entry(msg: "protobuf.MessageType", store: BlockStore) -> BlockEntry:
    mtype = msg.__class__
    if not mtype.FIELDS:
        table = TableBlock.build([], b"")
        return BlockEntry(table)

    entries: dict[int, TableEntry] = {}

    for ftag, field in mtype.FIELDS.items():
        value = getattr(msg, field.name, None)
        if field.repeated and value is None:
            value = []
        if value is None:
            continue
        if field.repeated and not value:
            continue
        if _is_txack_singleton_field(mtype, field) and len(value) == 1:
            # TXACK compatibility:
            # firmware decodes these fields through TxAck* wrappers where the
            # field is a plain struct at the same tag, not an array.
            entries[ftag - 1] = _hb_type_for_field(
                field, force_non_repeated=True
            ).encode(value[0], store)
            continue

        entries[ftag - 1] = _hb_type_for_field(field).encode(value, store)

    max_index = max(entries.keys(), default=-1)
    entries_list: list[TableEntry] = [NULL_ENTRY] * (max_index + 1)
    for ftag, entry in entries.items():
        entries_list[ftag] = entry

    return Table(entries_list).build_entry(store)


def serialize(msg: "protobuf.MessageType", store: BlockStore) -> bytes:
    entry = _serialize_entry(msg, store)
    return entry.encode()


def _deserialize_from_table(
    msg_type: type[MT], table: TableBlock, store: BlockStore
) -> MT:
    kwargs: dict[str, t.Any] = {}

    for ftag, field in msg_type.FIELDS.items():
        value = None

        if _is_txack_singleton_field(msg_type, field):
            # Accept both legacy array form and singleton struct form.
            try:
                single = _hb_type_for_field(
                    field, force_non_repeated=True
                ).decode_or_none(table[ftag - 1], store)
                value = [single] if single is not None else None
            except Exception:
                value = _hb_type_for_field(field).decode_or_none(table[ftag - 1], store)
        else:
            value = _hb_type_for_field(field).decode_or_none(table[ftag - 1], store)

        if value is None:
            if field.repeated:
                kwargs[field.name] = []
            elif field.required:
                raise ValueError(
                    f"Required field '{field.name}' (tag {ftag}) is missing"
                )
            elif field.default is not None:
                kwargs[field.name] = field.default
            continue

        kwargs[field.name] = value

    return msg_type(**kwargs)


def deserialize(msg_type: type[MT], data: bytes, store: BlockStore) -> MT:
    table = TableBlock.decode(data)
    return _deserialize_from_table(msg_type, table, store)
