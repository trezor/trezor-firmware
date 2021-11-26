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

import io
from typing import Dict, Tuple, Type

from . import messages, protobuf

map_type_to_class: Dict[int, Type[protobuf.MessageType]] = {}
map_class_to_type: Dict[Type[protobuf.MessageType], int] = {}


def build_map() -> None:
    for entry in messages.MessageType:
        msg_class = getattr(messages, entry.name, None)
        if msg_class is None:
            raise ValueError(
                f"Implementation of protobuf message '{entry.name}' is missing"
            )

        if msg_class.MESSAGE_WIRE_TYPE != entry.value:
            raise ValueError(
                f"Inconsistent wire type and MessageType record for '{entry.name}'"
            )

        register_message(msg_class)


def register_message(msg_class: Type[protobuf.MessageType]) -> None:
    if msg_class.MESSAGE_WIRE_TYPE is None:
        raise ValueError("Only messages with a wire type can be registered")

    if msg_class.MESSAGE_WIRE_TYPE in map_type_to_class:
        raise Exception(
            f"Message for wire type {msg_class.MESSAGE_WIRE_TYPE} is already "
            f"registered by {get_class(msg_class.MESSAGE_WIRE_TYPE)}"
        )

    map_class_to_type[msg_class] = msg_class.MESSAGE_WIRE_TYPE
    map_type_to_class[msg_class.MESSAGE_WIRE_TYPE] = msg_class


def get_type(msg: protobuf.MessageType) -> int:
    return map_class_to_type[msg.__class__]


def get_class(t: int) -> Type[protobuf.MessageType]:
    return map_type_to_class[t]


def encode(msg: protobuf.MessageType) -> Tuple[int, bytes]:
    if msg.MESSAGE_WIRE_TYPE is None:
        raise ValueError("Only messages with a wire type can be encoded")

    message_type = msg.MESSAGE_WIRE_TYPE
    buf = io.BytesIO()
    protobuf.dump_message(buf, msg)
    return message_type, buf.getvalue()


def decode(message_type: int, message_bytes: bytes) -> protobuf.MessageType:
    cls = get_class(message_type)
    buf = io.BytesIO(message_bytes)
    return protobuf.load_message(buf, cls)


build_map()
