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

import logging
import typing as t

if t.TYPE_CHECKING:
    from . import protobuf

OMITTED_MESSAGES: set[type[protobuf.MessageType]] = set()

DUMP_BYTES = 5
DUMP_PACKETS = 4

logging.addLevelName(DUMP_BYTES, "BYTES")
logging.addLevelName(DUMP_PACKETS, "PACKETS")


class PrettyProtobufFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        from . import client, protobuf

        session = getattr(record, "session", None)
        if isinstance(session, client.Session):
            session = f" [s:{session._log_short_id()}]"
        else:
            session = ""

        time = self.formatTime(record)
        message = "[{time}] {source} {level}{session}: {msg}".format(
            time=time,
            level=record.levelname.upper(),
            source=record.name,
            msg=super().format(record),
            session=session,
        )

        proto_msg = getattr(record, "protobuf", None)
        if isinstance(proto_msg, protobuf.MessageType):
            if type(proto_msg) in OMITTED_MESSAGES:
                message += f" ({proto_msg.ByteSize()} bytes)"
            else:
                message += "\n" + protobuf.format_message(proto_msg)

        return message


def enable_debug_output(
    verbosity: int = 1, handler: logging.Handler | None = None
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
