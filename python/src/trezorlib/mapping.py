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

import io
import typing as t
from types import ModuleType

from typing_extensions import Self
from hashbuffers.store import BlockStore

from . import messages, protobuf, hashbuffers

T = t.TypeVar("T")
MT = t.TypeVar("MT", bound=protobuf.MessageType)


class Mapping(t.Protocol):
    def encode(self, msg: protobuf.MessageType) -> tuple[int, bytes]: ...
    def decode(self, msg_wire_type: int, msg_bytes: bytes) -> protobuf.MessageType: ...


class ProtobufMapping(Mapping):
    """Mapping of protobuf classes to Python classes"""

    def __init__(self) -> None:
        self.type_to_class: t.Dict[int, t.Type[protobuf.MessageType]] = {}
        self.class_to_type_override: t.Dict[t.Type[protobuf.MessageType], int] = {}

    def register(
        self,
        msg_class: t.Type[protobuf.MessageType],
        msg_wire_type: int | None = None,
    ) -> None:
        """Register a Python class as a protobuf type.

        If `msg_wire_type` is specified, it is used instead of the internal value in
        `msg_class`.

        Any existing registrations are overwritten.
        """
        if msg_wire_type is not None:
            self.class_to_type_override[msg_class] = msg_wire_type
        elif msg_class.MESSAGE_WIRE_TYPE is None:
            raise ValueError("Cannot register class without wire type")
        else:
            msg_wire_type = msg_class.MESSAGE_WIRE_TYPE

        self.type_to_class[msg_wire_type] = msg_class

    def encode(self, msg: protobuf.MessageType) -> tuple[int, bytes]:
        """Serialize a Python protobuf class.

        Returns the message wire type and a byte representation of the protobuf message.
        """
        wire_type = self.class_to_type_override.get(type(msg), msg.MESSAGE_WIRE_TYPE)
        if wire_type is None:
            raise ValueError(
                f'Cannot encode class "{type(msg).__name__}" without wire type'
            )

        buf = io.BytesIO()
        protobuf.dump_message(buf, msg)
        return wire_type, buf.getvalue()

    def decode(self, msg_wire_type: int, msg_bytes: bytes) -> protobuf.MessageType:
        """Deserialize a protobuf message into a Python class."""
        cls = self.type_to_class[msg_wire_type]
        buf = io.BytesIO(msg_bytes)
        return protobuf.load_message(buf, cls)

    @classmethod
    def from_module(cls, module: ModuleType) -> Self:
        """Generate a mapping from a module.

        The module must have a `MessageType` enum that specifies individual wire types.
        """
        mapping = cls()

        message_types = getattr(module, "MessageType")
        thp_message_types = getattr(module, "ThpMessageType")

        for entry in (*message_types, *thp_message_types):
            msg_class = getattr(module, entry.name, None)
            if msg_class is None:
                raise ValueError(
                    f"Implementation of protobuf message '{entry.name}' is missing, {module}"
                )

            if msg_class.MESSAGE_WIRE_TYPE != entry.value:
                raise ValueError(
                    f"Inconsistent wire type and MessageType record for '{entry.name}': {entry.value} != {msg_class.MESSAGE_WIRE_TYPE}, {msg_class}"
                )

            mapping.register(msg_class)

        return mapping


class HashbufMapping(ProtobufMapping):
    def __init__(self, mapping: ProtobufMapping) -> None:
        self.mapping = mapping
        self.store = BlockStore(b"test")
        self.record: t.Callable[..., None] = self.null_record

    def null_record(
        self,
        direction: str,
        message_type: str,
        protobuf_size: int,
        store: BlockStore,
        message: protobuf.MessageType,
        hashbuf_bytes: bytes,
        protobuf_bytes: bytes,
    ) -> None:
        pass

    def encode(self, msg: protobuf.MessageType) -> tuple[int, bytes]:
        self.store.blocks.clear()
        wire_type, msg_bytes = self.mapping.encode(msg)
        block_bytes = hashbuffers.serialize(msg, self.store)
        _ = self.store.store_bytes(block_bytes)
        self.record(
            direction="encode",
            message_type=type(msg).__name__,
            protobuf_size=len(msg_bytes),
            store=self.store,
            message=msg,
            hashbuf_bytes=block_bytes,
            protobuf_bytes=msg_bytes,
        )
        return wire_type, block_bytes

    def decode(self, msg_wire_type: int, msg_bytes: bytes) -> protobuf.MessageType:
        msg = self.mapping.decode(msg_wire_type, msg_bytes)
        try:
            block_bytes = hashbuffers.serialize(msg, self.store)
        except Exception as e:
            print(f"Error serializing message {type(msg).__name__}: {msg} ({e})")
            raise
        self.store.blocks.clear()
        _ = self.store.store_bytes(block_bytes)
        self.record(
            direction="decode",
            message_type=type(msg).__name__,
            protobuf_size=len(msg_bytes),
            store=self.store,
            message=msg,
            hashbuf_bytes=block_bytes,
            protobuf_bytes=msg_bytes,
        )
        return msg


DEFAULT_PROTO_MAPPING = ProtobufMapping.from_module(messages)

import os

if int(os.environ.get("TREZOR_SEND_HASHBUFFERS", "0")):
    DEFAULT_MAPPING = HashbufMapping(DEFAULT_PROTO_MAPPING)
else:
    DEFAULT_MAPPING = DEFAULT_PROTO_MAPPING
