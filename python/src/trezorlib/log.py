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

import logging
from typing import Optional, Set, Type

from typing_extensions import Protocol, runtime_checkable

from . import protobuf


@runtime_checkable
class HasProtobuf(Protocol):
    protobuf: protobuf.MessageType


OMITTED_MESSAGES: Set[Type[protobuf.MessageType]] = set()

DUMP_BYTES = 5
DUMP_PACKETS = 4

logging.addLevelName(DUMP_BYTES, "BYTES")
logging.addLevelName(DUMP_PACKETS, "PACKETS")


class PrettyProtobufFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        time = self.formatTime(record)
        message = "[{time}] {source} {level}: {msg}".format(
            time=time,
            level=record.levelname.upper(),
            source=record.name,
            msg=super().format(record),
        )
        if isinstance(record, HasProtobuf):
            if type(record.protobuf) in OMITTED_MESSAGES:
                message += f" ({record.protobuf.ByteSize()} bytes)"
            else:
                message += "\n" + protobuf.format_message(record.protobuf)
        return message


def enable_debug_output(
    verbosity: int = 1, handler: Optional[logging.Handler] = None
) -> None:
    if handler is None:
        handler = logging.StreamHandler()

    formatter = PrettyProtobufFormatter()
    handler.setFormatter(formatter)

    level = logging.NOTSET
    if verbosity > 0:
        level = logging.DEBUG
    if verbosity > 1:
        level = DUMP_BYTES
    if verbosity > 2:
        level = DUMP_PACKETS

    logger = logging.getLogger(__name__.rsplit(".", 1)[0])
    logger.setLevel(level)
    logger.addHandler(handler)
