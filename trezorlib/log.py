# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

from . import protobuf

OMITTED_MESSAGES = set()  # type: Set[Type[protobuf.MessageType]]


class PrettyProtobufFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        time = self.formatTime(record)
        message = "[{time}] {source} {level}: {msg}".format(
            time=time,
            level=record.levelname.upper(),
            source=record.name,
            msg=super().format(record),
        )
        if hasattr(record, "protobuf"):
            if type(record.protobuf) in OMITTED_MESSAGES:
                message += " ({} bytes)".format(record.protobuf.ByteSize())
            else:
                message += "\n" + protobuf.format_message(record.protobuf)
        return message


def enable_debug_output(handler: Optional[logging.Handler] = None):
    if handler is None:
        handler = logging.StreamHandler()

    formatter = PrettyProtobufFormatter()
    handler.setFormatter(formatter)

    logger = logging.getLogger("trezorlib")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
